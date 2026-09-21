import pytest

from app.modules.inteligencia_artificial.application.ports.providers.proveedor_ia import (
    ProveedorIa,
    ResultadoProveedorIa,
)
from app.modules.inteligencia_artificial.application.services.estrategia_modelos_gemini import (
    MODELOS_GEMINI_ORDENADOS,
    EstrategiaModelosGemini,
)
from app.modules.inteligencia_artificial.domain.exceptions import (
    EntradaUsuarioInvalidaException,
    ProveedorIaNoRecuperableException,
    ProveedorIaRecuperableException,
    RespuestaIaInvalidaException,
)


class FakeProveedorIa(ProveedorIa):
    def __init__(self, respuestas_por_modelo: dict[str, ResultadoProveedorIa | Exception]) -> None:
        self.respuestas = respuestas_por_modelo
        self.modelos_llamados: list[str] = []

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
        if isinstance(resp, Exception):
            raise resp
        if isinstance(resp, ResultadoProveedorIa):
            return resp
        return ResultadoProveedorIa(texto_respuesta="ok", modelo=modelo)


def test_estrategia_primer_modelo_exitoso_se_detiene():
    proveedor = FakeProveedorIa({
        "gemini-3.7-flash": ResultadoProveedorIa(texto_respuesta="hola", modelo="gemini-3.7-flash"),
    })
    coordinador = EstrategiaModelosGemini(proveedor)

    resultado = coordinador.ejecutar_con_fallback(
        prompt_sistema="system",
        mensaje_usuario="hola",
    )

    assert resultado.modelo == "gemini-3.7-flash"
    assert resultado.texto_respuesta == "hola"
    assert proveedor.modelos_llamados == ["gemini-3.7-flash"]


def test_estrategia_fallback_secuencial_exacto_ante_error_recuperable():
    proveedor = FakeProveedorIa({
        "gemini-3.7-flash": ProveedorIaRecuperableException("Rate limit 429"),
        "gemini-3.6-flash": ProveedorIaRecuperableException("Timeout"),
        "gemini-3.5-flash": ResultadoProveedorIa(texto_respuesta="éxito en 3.5", modelo="gemini-3.5-flash"),
    })
    coordinador = EstrategiaModelosGemini(proveedor)

    resultado = coordinador.ejecutar_con_fallback(
        prompt_sistema="system",
        mensaje_usuario="hola",
    )

    assert resultado.modelo == "gemini-3.5-flash"
    assert resultado.texto_respuesta == "éxito en 3.5"
    assert proveedor.modelos_llamados == [
        "gemini-3.7-flash",
        "gemini-3.6-flash",
        "gemini-3.5-flash",
    ]


def test_estrategia_agota_ocho_modelos_si_todos_fallan_recuperable():
    proveedor = FakeProveedorIa({
        m: ProveedorIaRecuperableException(f"Error en {m}")
        for m in MODELOS_GEMINI_ORDENADOS
    })
    coordinador = EstrategiaModelosGemini(proveedor)

    with pytest.raises(ProveedorIaRecuperableException):
        coordinador.ejecutar_con_fallback(
            prompt_sistema="system",
            mensaje_usuario="hola",
        )

    assert tuple(proveedor.modelos_llamados) == MODELOS_GEMINI_ORDENADOS


def test_estrategia_no_hace_fallback_ante_error_no_recuperable():
    proveedor = FakeProveedorIa({
        "gemini-3.7-flash": ProveedorIaNoRecuperableException("API key inválida 401"),
        "gemini-3.6-flash": ResultadoProveedorIa(texto_respuesta="no debería llamarse", modelo="gemini-3.6-flash"),
    })
    coordinador = EstrategiaModelosGemini(proveedor)

    with pytest.raises(ProveedorIaNoRecuperableException):
        coordinador.ejecutar_con_fallback(
            prompt_sistema="system",
            mensaje_usuario="hola",
        )

    assert proveedor.modelos_llamados == ["gemini-3.7-flash"]


def test_estrategia_no_hace_fallback_ante_excepcion_de_dominio_o_validacion():
    proveedor = FakeProveedorIa({
        "gemini-3.7-flash": EntradaUsuarioInvalidaException("Texto vacío"),
        "gemini-3.6-flash": ResultadoProveedorIa(texto_respuesta="no", modelo="gemini-3.6-flash"),
    })
    coordinador = EstrategiaModelosGemini(proveedor)

    with pytest.raises(EntradaUsuarioInvalidaException):
        coordinador.ejecutar_con_fallback(
            prompt_sistema="system",
            mensaje_usuario="hola",
        )

    assert proveedor.modelos_llamados == ["gemini-3.7-flash"]
