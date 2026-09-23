import pytest
import time

from app.modules.inteligencia_artificial.application.ports.providers.proveedor_ia import (
    ProveedorIa,
    ResultadoProveedorIa,
)
from app.modules.inteligencia_artificial.application.services.estrategia_modelos_gemini import (
    CircuitState,
    EstrategiaModelosGemini,
    MODELOS_GEMINI_ORDENADOS,
    _obtener_breaker,
    reset_circuit_breakers,
)
from app.modules.inteligencia_artificial.domain.exceptions import (
    EntradaUsuarioInvalidaException,
    ProveedorIaNoRecuperableException,
    ProveedorIaRecuperableException,
)


class FakeProveedorIa(ProveedorIa):
    def __init__(
        self,
        respuestas_por_modelo: dict[str, list[ResultadoProveedorIa | Exception] | ResultadoProveedorIa | Exception] | None = None,
        respuestas_audio_por_modelo: dict[str, list[str | Exception] | str | Exception] | None = None,
        respuestas_imagen_por_modelo: dict[str, list[str | Exception] | str | Exception] | None = None,
    ) -> None:
        self.respuestas = respuestas_por_modelo or {}
        self.respuestas_audio = respuestas_audio_por_modelo or {}
        self.respuestas_imagen = respuestas_imagen_por_modelo or {}
        self.modelos_llamados: list[str] = []
        self.llamadas_audio: list[str] = []
        self.llamadas_imagen: list[str] = []

    def generar_respuesta(
        self,
        *,
        modelo: str,
        prompt_sistema: str,
        mensaje_usuario: str,
        temperatura: float = 0.2,
    ) -> ResultadoProveedorIa:
        self.modelos_llamados.append(modelo)
        resp = self.respuestas.get(modelo)
        if isinstance(resp, list):
            item = resp.pop(0) if resp else ResultadoProveedorIa(texto_respuesta="ok", modelo=modelo)
            if isinstance(item, Exception):
                raise item
            return item
        if isinstance(resp, Exception):
            raise resp
        if isinstance(resp, ResultadoProveedorIa):
            return resp
        return ResultadoProveedorIa(texto_respuesta="ok", modelo=modelo)

    def transcribir_audio(
        self,
        *,
        modelo: str,
        contenido_audio: bytes,
        mime_type: str,
        idioma: str = "es",
    ) -> str:
        self.llamadas_audio.append(modelo)
        resp = self.respuestas_audio.get(modelo)
        if isinstance(resp, list):
            item = resp.pop(0) if resp else "transcripcion ok"
            if isinstance(item, Exception):
                raise item
            return item
        if isinstance(resp, Exception):
            raise resp
        if isinstance(resp, str):
            return resp
        return "transcripcion ok"

    def analizar_diagrama_imagen(
        self,
        *,
        modelo: str,
        contenido_imagen: bytes,
        mime_type: str,
        prompt_estructural: str,
    ) -> str:
        self.llamadas_imagen.append(modelo)
        resp = self.respuestas_imagen.get(modelo)
        if isinstance(resp, list):
            item = resp.pop(0) if resp else '{"clases": []}'
            if isinstance(item, Exception):
                raise item
            return item
        if isinstance(resp, Exception):
            raise resp
        if isinstance(resp, str):
            return resp
        return '{"clases": []}'


@pytest.fixture(autouse=True)
def limpiar_breakers():
    reset_circuit_breakers()
    yield
    reset_circuit_breakers()


# Caso 1: Modelo principal gemini-3.1-flash-lite responde con éxito en primer intento
def test_caso_1_modelo_principal_exitoso_primer_intento():
    proveedor = FakeProveedorIa({
        "gemini-3.1-flash-lite": ResultadoProveedorIa(texto_respuesta="respuesta principal", modelo="gemini-3.1-flash-lite"),
    })
    coordinador = EstrategiaModelosGemini(proveedor, retry_backoff_ms=0)

    resultado = coordinador.ejecutar_con_fallback(
        prompt_sistema="system",
        mensaje_usuario="crea clase Cliente",
    )

    assert resultado.modelo == "gemini-3.1-flash-lite"
    assert resultado.texto_respuesta == "respuesta principal"
    assert resultado.intentos == 1
    assert resultado.fallback_utilizado is False
    assert resultado.breaker_abierto is False
    assert proveedor.modelos_llamados == ["gemini-3.1-flash-lite"]


# Caso 2: Fallo 429 (Resource Exhausted / Quota Exceeded) en modelo principal pasa inmediatamente a fallback sin reintentos
def test_caso_2_fallo_429_pasa_inmediatamente_a_fallback():
    proveedor = FakeProveedorIa({
        "gemini-3.1-flash-lite": ProveedorIaRecuperableException("Rate limit 429: Quota exceeded"),
        "gemini-3.5-flash-lite": ResultadoProveedorIa(texto_respuesta="éxito en fallback inmediato", modelo="gemini-3.5-flash-lite"),
    })
    coordinador = EstrategiaModelosGemini(
        proveedor,
        modelos=("gemini-3.1-flash-lite", "gemini-3.5-flash-lite"),
        retry_backoff_ms=0,
    )

    resultado = coordinador.ejecutar_con_fallback(
        prompt_sistema="system",
        mensaje_usuario="crea clase Cliente",
    )

    assert resultado.modelo == "gemini-3.5-flash-lite"
    assert resultado.texto_respuesta == "éxito en fallback inmediato"
    assert resultado.intentos == 2
    assert resultado.fallback_utilizado is True
    # Exactamente 1 intento por modelo, sin repetir gemini-3.1-flash-lite
    assert proveedor.modelos_llamados == ["gemini-3.1-flash-lite", "gemini-3.5-flash-lite"]


# Caso 3: Fallo 504 / Timeout en modelo principal pasa inmediatamente a fallback sin reintentos
def test_caso_3_fallo_504_timeout_pasa_inmediatamente_a_fallback():
    proveedor = FakeProveedorIa({
        "gemini-3.1-flash-lite": ProveedorIaRecuperableException("Timeout 504 Gateway Timeout"),
        "gemini-3.5-flash-lite": ResultadoProveedorIa(texto_respuesta="éxito en fallback tras timeout", modelo="gemini-3.5-flash-lite"),
    })
    coordinador = EstrategiaModelosGemini(
        proveedor,
        modelos=("gemini-3.1-flash-lite", "gemini-3.5-flash-lite"),
        retry_backoff_ms=0,
    )

    resultado = coordinador.ejecutar_con_fallback(
        prompt_sistema="system",
        mensaje_usuario="crea clase Cliente",
    )

    assert resultado.modelo == "gemini-3.5-flash-lite"
    assert resultado.texto_respuesta == "éxito en fallback tras timeout"
    assert resultado.fallback_utilizado is True
    # Exactamente 1 intento por modelo
    assert proveedor.modelos_llamados == ["gemini-3.1-flash-lite", "gemini-3.5-flash-lite"]


# Caso 4: Circuit breaker abre tras 2 fallos acumulados y salta directamente al fallback sin timeout
def test_caso_4_circuit_breaker_abre_y_salta_directamente_al_fallback():
    breaker = _obtener_breaker("gemini-3.1-flash-lite")
    breaker.state = CircuitState.OPEN
    breaker.last_failure_time = time.monotonic()  # recientemente abierto

    proveedor = FakeProveedorIa({
        "gemini-3.5-flash-lite": ResultadoProveedorIa(texto_respuesta="éxito directo en fallback", modelo="gemini-3.5-flash-lite"),
    })
    coordinador = EstrategiaModelosGemini(
        proveedor,
        modelos=("gemini-3.1-flash-lite", "gemini-3.5-flash-lite"),
        retry_backoff_ms=0,
        breaker_cooldown_seconds=60.0,
    )

    resultado = coordinador.ejecutar_con_fallback(
        prompt_sistema="system",
        mensaje_usuario="crea clase Cliente",
    )

    assert resultado.modelo == "gemini-3.5-flash-lite"
    assert resultado.breaker_abierto is True
    assert resultado.fallback_utilizado is True
    # gemini-3.1-flash-lite NO fue llamado porque breaker está OPEN
    assert proveedor.modelos_llamados == ["gemini-3.5-flash-lite"]


# Caso 5: Auto-recuperación en HALF_OPEN tras periodo de enfriamiento
def test_caso_5_auto_recuperacion_half_open_tras_enfriamiento():
    breaker = _obtener_breaker("gemini-3.1-flash-lite")
    breaker.state = CircuitState.OPEN
    breaker.consecutive_failures = 2
    breaker.last_failure_time = time.monotonic() - 65.0  # Cooldown de 60s expirado

    proveedor = FakeProveedorIa({
        "gemini-3.1-flash-lite": ResultadoProveedorIa(texto_respuesta="recuperado", modelo="gemini-3.1-flash-lite"),
    })
    coordinador = EstrategiaModelosGemini(proveedor, retry_backoff_ms=0, breaker_cooldown_seconds=60.0)

    resultado = coordinador.ejecutar_con_fallback(
        prompt_sistema="system",
        mensaje_usuario="crea clase Cliente",
    )

    assert resultado.modelo == "gemini-3.1-flash-lite"
    assert breaker.state == CircuitState.CLOSED
    assert breaker.consecutive_failures == 0
    assert proveedor.modelos_llamados == ["gemini-3.1-flash-lite"]


# Caso 6: Ambos modelos fallan -> lanza error técnico controlado 503 sin mutaciones
def test_caso_6_ambos_modelos_fallan_lanza_error_recuperable():
    proveedor = FakeProveedorIa({
        "gemini-3.1-flash-lite": ProveedorIaRecuperableException("429 Quota Exceeded"),
        "gemini-3.5-flash-lite": ProveedorIaRecuperableException("503 Service Unavailable"),
    })
    coordinador = EstrategiaModelosGemini(
        proveedor,
        modelos=("gemini-3.1-flash-lite", "gemini-3.5-flash-lite"),
        retry_backoff_ms=0,
    )

    with pytest.raises(ProveedorIaRecuperableException) as exc_info:
        coordinador.ejecutar_con_fallback(
            prompt_sistema="system",
            mensaje_usuario="crea clase Cliente",
        )

    assert "DRAWI no pudo procesar la solicitud en este momento" in str(exc_info.value) or "503" in str(exc_info.value) or "429" in str(exc_info.value)
    # Máximo 1 intento por modelo
    assert proveedor.modelos_llamados == ["gemini-3.1-flash-lite", "gemini-3.5-flash-lite"]


# Caso 7: Error no recuperable (401/403) no reintenta ni realiza fallback
def test_caso_7_error_no_recuperable_sin_reintento_ni_fallback():
    proveedor = FakeProveedorIa({
        "gemini-3.1-flash-lite": ProveedorIaNoRecuperableException("401 Unauthorized API Key"),
        "gemini-3.5-flash-lite": ResultadoProveedorIa(texto_respuesta="no debe llegar", modelo="gemini-3.5-flash-lite"),
    })
    coordinador = EstrategiaModelosGemini(proveedor, retry_backoff_ms=0)

    with pytest.raises(ProveedorIaNoRecuperableException):
        coordinador.ejecutar_con_fallback(
            prompt_sistema="system",
            mensaje_usuario="crea clase Cliente",
        )

    assert proveedor.modelos_llamados == ["gemini-3.1-flash-lite"]


# Caso 8: Excepción de validación o dominio no activa fallback ni incrementa contador de breaker
def test_caso_8_excepcion_dominio_sin_fallback_ni_breaker_increment():
    breaker = _obtener_breaker("gemini-3.1-flash-lite")
    proveedor = FakeProveedorIa({
        "gemini-3.1-flash-lite": EntradaUsuarioInvalidaException("Texto vacío"),
        "gemini-3.5-flash-lite": ResultadoProveedorIa(texto_respuesta="no", modelo="gemini-3.5-flash-lite"),
    })
    coordinador = EstrategiaModelosGemini(proveedor, retry_backoff_ms=0)

    with pytest.raises(EntradaUsuarioInvalidaException):
        coordinador.ejecutar_con_fallback(
            prompt_sistema="system",
            mensaje_usuario="",
        )

    assert proveedor.modelos_llamados == ["gemini-3.1-flash-lite"]
    assert breaker.consecutive_failures == 0
    assert breaker.state == CircuitState.CLOSED


# Caso Adicional: Transcripción de audio con fallback inmediato ante 429
def test_transcripcion_audio_fallback_secuencial():
    proveedor = FakeProveedorIa(
        respuestas_audio_por_modelo={
            "gemini-3.1-flash-lite": ProveedorIaRecuperableException("429 rate limit"),
            "gemini-3.5-flash-lite": "texto transcrito con exito",
        }
    )
    coordinador = EstrategiaModelosGemini(
        proveedor,
        modelos=("gemini-3.1-flash-lite", "gemini-3.5-flash-lite"),
        retry_backoff_ms=0,
    )

    resultado = coordinador.transcribir_con_fallback(
        contenido_audio=b"dummy_bytes",
        mime_type="audio/webm",
        idioma="es",
    )

    assert resultado == "texto transcrito con exito"
    assert proveedor.llamadas_audio == [
        "gemini-3.1-flash-lite",
        "gemini-3.5-flash-lite",
    ]


# Caso Adicional: Análisis de imagen con fallback inmediato ante 503 / 429
def test_analisis_imagen_fallback_secuencial():
    proveedor = FakeProveedorIa(
        respuestas_imagen_por_modelo={
            "gemini-3.1-flash-lite": ProveedorIaRecuperableException("503 High Demand"),
            "gemini-3.5-flash-lite": '{"clases": [{"nombre": "Factura", "referencia_semantica": "c1", "atributos": []}], "relaciones": []}',
        }
    )
    coordinador = EstrategiaModelosGemini(
        proveedor,
        modelos=("gemini-3.1-flash-lite", "gemini-3.5-flash-lite"),
        retry_backoff_ms=0,
    )

    resultado = coordinador.analizar_imagen_con_fallback(
        contenido_imagen=b"dummy_image_bytes",
        mime_type="image/png",
        prompt_estructural="prompt",
    )

    assert "Factura" in resultado
    assert proveedor.llamadas_imagen == [
        "gemini-3.1-flash-lite",
        "gemini-3.5-flash-lite",
    ]


# Caso Adicional: Ambos modelos fallan en análisis de imagen (503) lanza ProveedorIaRecuperableException (máximo 1 intento por modelo)
def test_analisis_imagen_ambos_modelos_503_lanza_recuperable():
    proveedor = FakeProveedorIa(
        respuestas_imagen_por_modelo={
            "gemini-3.1-flash-lite": ProveedorIaRecuperableException("429 Quota Exceeded"),
            "gemini-3.5-flash-lite": ProveedorIaRecuperableException("503 High Demand fallback"),
        }
    )
    coordinador = EstrategiaModelosGemini(
        proveedor,
        modelos=("gemini-3.1-flash-lite", "gemini-3.5-flash-lite"),
        retry_backoff_ms=0,
    )

    with pytest.raises(ProveedorIaRecuperableException) as exc_info:
        coordinador.analizar_imagen_con_fallback(
            contenido_imagen=b"dummy_image_bytes",
            mime_type="image/png",
            prompt_estructural="prompt",
        )

    assert "DRAWI no pudo procesar" in str(exc_info.value) or "503" in str(exc_info.value) or "429" in str(exc_info.value)
    # Exactamente 2 llamadas en total (1 por modelo)
    assert proveedor.llamadas_imagen == ["gemini-3.1-flash-lite", "gemini-3.5-flash-lite"]


# Caso Adicional: Error 400 no recuperable en análisis de imagen se propaga inmediatamente sin reintentos ni fallback
def test_analisis_imagen_error_400_no_recuperable_inmediato():
    breaker = _obtener_breaker("gemini-3.1-flash-lite")
    proveedor = FakeProveedorIa(
        respuestas_imagen_por_modelo={
            "gemini-3.1-flash-lite": ProveedorIaNoRecuperableException("400 Bad Request: deadline too short"),
            "gemini-3.5-flash-lite": '{"clases": []}',
        }
    )
    coordinador = EstrategiaModelosGemini(proveedor, retry_backoff_ms=0)

    with pytest.raises(ProveedorIaNoRecuperableException) as exc_info:
        coordinador.analizar_imagen_con_fallback(
            contenido_imagen=b"dummy_image_bytes",
            mime_type="image/png",
            prompt_estructural="prompt",
        )

    assert "400" in str(exc_info.value)
    assert proveedor.llamadas_imagen == ["gemini-3.1-flash-lite"]
    assert breaker.consecutive_failures == 0
    assert breaker.state == CircuitState.CLOSED


# Caso 6 Modelos: Cascada completa por orden de prioridad ante fallos recuperables
def test_cascada_completa_6_modelos_fallback():
    assert len(MODELOS_GEMINI_ORDENADOS) == 6
    assert MODELOS_GEMINI_ORDENADOS[0] == "gemini-3.1-flash-lite"
    assert MODELOS_GEMINI_ORDENADOS[-1] == "gemini-3.8-flash"

    # Los primeros 5 modelos fallan por 429/503/timeout
    respuestas = {
        m: ProveedorIaRecuperableException(f"Error temporal en {m}")
        for m in MODELOS_GEMINI_ORDENADOS[:5]
    }
    # El 6to modelo (gemini-3.8-flash) responde con éxito
    respuestas[MODELOS_GEMINI_ORDENADOS[5]] = ResultadoProveedorIa(
        texto_respuesta="respuesta final del 6to modelo",
        modelo=MODELOS_GEMINI_ORDENADOS[5],
    )

    proveedor = FakeProveedorIa(respuestas)
    coordinador = EstrategiaModelosGemini(proveedor, retry_backoff_ms=0)
    assert len(coordinador.modelos) == 6

    resultado = coordinador.ejecutar_con_fallback(
        prompt_sistema="system",
        mensaje_usuario="crea clase Producto",
    )

    assert resultado.modelo == "gemini-3.8-flash"
    assert resultado.texto_respuesta == "respuesta final del 6to modelo"
    assert resultado.fallback_utilizado is True
    assert resultado.intentos == 6
    assert proveedor.modelos_llamados == list(MODELOS_GEMINI_ORDENADOS)



