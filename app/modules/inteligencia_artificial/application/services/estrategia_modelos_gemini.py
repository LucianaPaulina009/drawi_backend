from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Final, Sequence, TypeVar

from app.core.config import settings
from app.modules.inteligencia_artificial.application.ports.providers.proveedor_ia import (
    ProveedorIa,
    ResultadoProveedorIa,
)
from app.modules.inteligencia_artificial.domain.exceptions import (
    ProveedorIaNoRecuperableException,
    ProveedorIaRecuperableException,
)

logger = logging.getLogger(__name__)

# Cascada de modelos Gemini ordenados por balance de inteligencia, velocidad y resiliencia
MODELOS_GEMINI_ORDENADOS: Final[tuple[str, ...]] = (
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.6-flash",
    "gemini-3.7-flash",
    "gemini-3.8-flash",
    "gemini-2.5-flash",
)


class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


@dataclass
class ModelCircuitBreaker:
    state: CircuitState = CircuitState.CLOSED
    consecutive_failures: int = 0
    last_failure_time: float = 0.0


# Registro en memoria por modelo (compartido en el proceso)
_CIRCUIT_BREAKERS: dict[str, ModelCircuitBreaker] = {}

T = TypeVar("T")


def _obtener_breaker(modelo: str) -> ModelCircuitBreaker:
    if modelo not in _CIRCUIT_BREAKERS:
        _CIRCUIT_BREAKERS[modelo] = ModelCircuitBreaker()
    return _CIRCUIT_BREAKERS[modelo]


def reset_circuit_breakers() -> None:
    """Limpia el estado de todos los circuit breakers (útil en tests)."""
    _CIRCUIT_BREAKERS.clear()


class EstrategiaModelosGemini:
    """Coordinador de resiliencia con Circuit Breaker, reintento técnico y fallback entre modelos Gemini."""

    def __init__(
        self,
        proveedor: ProveedorIa,
        modelos: Sequence[str] | None = None,
        failures_threshold: int | None = None,
        breaker_cooldown_seconds: float | None = None,
        retry_backoff_ms: int | None = None,
    ) -> None:
        self.proveedor = proveedor
        self.modelos = tuple(
            modelos
            if modelos is not None
            else getattr(settings, "modelos_gemini_cascada", MODELOS_GEMINI_ORDENADOS)
        )
        self.failures_threshold = (
            failures_threshold
            if failures_threshold is not None
            else settings.IA_GEMINI_BREAKER_FAILURES
        )
        self.breaker_cooldown_seconds = (
            breaker_cooldown_seconds
            if breaker_cooldown_seconds is not None
            else float(settings.IA_GEMINI_BREAKER_SECONDS)
        )
        self.retry_backoff_ms = (
            retry_backoff_ms
            if retry_backoff_ms is not None
            else settings.IA_GEMINI_RETRY_BACKOFF_MS
        )
        self._ultimo_modelo_usado: str = ""

    @property
    def modelo_primario(self) -> str:
        return self.modelos[0] if self.modelos else settings.IA_GEMINI_PRIMARY_MODEL

    @property
    def ultimo_modelo_usado(self) -> str:
        return self._ultimo_modelo_usado or self.modelo_primario

    def _evaluar_estado_breaker(self, modelo: str) -> tuple[CircuitState, bool]:
        """Devuelve el estado actual del breaker y si está abierto bloqueando peticiones."""
        breaker = _obtener_breaker(modelo)
        ahora = time.monotonic()

        if breaker.state == CircuitState.OPEN:
            if ahora - breaker.last_failure_time >= self.breaker_cooldown_seconds:
                breaker.state = CircuitState.HALF_OPEN
                logger.info(
                    "Circuit Breaker para modelo %s pasó a HALF_OPEN tras periodo de enfriamiento.",
                    modelo,
                )
                return CircuitState.HALF_OPEN, False
            return CircuitState.OPEN, True

        return breaker.state, False

    def _registrar_exito(self, modelo: str) -> None:
        breaker = _obtener_breaker(modelo)
        breaker.state = CircuitState.CLOSED
        breaker.consecutive_failures = 0

    def _registrar_fallo_recuperable(self, modelo: str, en_half_open: bool = False) -> None:
        breaker = _obtener_breaker(modelo)
        breaker.last_failure_time = time.monotonic()
        if en_half_open:
            breaker.state = CircuitState.OPEN
            logger.warning(
                "Prueba en HALF_OPEN para modelo %s falló. Circuito devuelto a OPEN.",
                modelo,
            )
            return

        breaker.consecutive_failures += 1
        if breaker.consecutive_failures >= self.failures_threshold:
            breaker.state = CircuitState.OPEN
            logger.warning(
                "Circuit Breaker ABIERTO para modelo %s tras %d fallos consecutivos.",
                modelo,
                breaker.consecutive_failures,
            )

    def ejecutar_con_fallback(
        self,
        *,
        prompt_sistema: str,
        mensaje_usuario: str,
        temperatura: float = 0.2,
    ) -> ResultadoProveedorIa:
        ultimo_error: ProveedorIaRecuperableException | None = None
        alguna_vez_breaker_abierto = False
        inicio_total = time.monotonic()
        total_intentos = 0

        for indice_modelo, modelo in enumerate(self.modelos):
            estado_breaker, esta_abierto = self._evaluar_estado_breaker(modelo)
            if esta_abierto:
                alguna_vez_breaker_abierto = True
                logger.warning(
                    "Circuit breaker OPEN para modelo %s. Omitiendo directamente hacia fallback.",
                    modelo,
                )
                continue

            es_half_open = estado_breaker == CircuitState.HALF_OPEN
            total_intentos += 1

            try:
                resultado = self.proveedor.generar_respuesta(
                    modelo=modelo,
                    prompt_sistema=prompt_sistema,
                    mensaje_usuario=mensaje_usuario,
                    temperatura=temperatura,
                )
                duracion_ms = (time.monotonic() - inicio_total) * 1000.0
                self._ultimo_modelo_usado = modelo
                self._registrar_exito(modelo)
                return ResultadoProveedorIa(
                    texto_respuesta=resultado.texto_respuesta,
                    modelo=modelo,
                    intentos=total_intentos,
                    fallback_utilizado=(indice_modelo > 0),
                    breaker_abierto=alguna_vez_breaker_abierto,
                    duracion_ms=duracion_ms,
                )
            except ProveedorIaRecuperableException as err:
                ultimo_error = err
                logger.warning(
                    "Fallo recuperable en modelo %s: %s. Saltando inmediatamente al fallback sin reintento sobre el mismo modelo.",
                    modelo,
                    str(err),
                )
                self._registrar_fallo_recuperable(modelo, en_half_open=es_half_open)
                continue
            except (ProveedorIaNoRecuperableException, Exception):
                # Errores no recuperables, de autorización o de dominio detienen el flujo sin fallback ni reintento
                raise

        raise ultimo_error or ProveedorIaRecuperableException(
            "DRAWI no pudo procesar la solicitud en este momento. Intenta nuevamente."
        )

    def transcribir_con_fallback(
        self,
        *,
        contenido_audio: bytes,
        mime_type: str,
        idioma: str = "es",
    ) -> str:
        ultimo_error: ProveedorIaRecuperableException | None = None

        for modelo in self.modelos:
            estado_breaker, esta_abierto = self._evaluar_estado_breaker(modelo)
            if esta_abierto:
                logger.warning(
                    "Circuit breaker OPEN para modelo %s en transcripción. Omitiendo directamente hacia fallback.",
                    modelo,
                )
                continue

            es_half_open = estado_breaker == CircuitState.HALF_OPEN

            try:
                texto = self.proveedor.transcribir_audio(
                    modelo=modelo,
                    contenido_audio=contenido_audio,
                    mime_type=mime_type,
                    idioma=idioma,
                )
                self._ultimo_modelo_usado = modelo
                self._registrar_exito(modelo)
                return texto
            except ProveedorIaRecuperableException as err:
                ultimo_error = err
                logger.warning(
                    "Fallo recuperable en transcripción con modelo %s: %s. Saltando inmediatamente al fallback sin reintento.",
                    modelo,
                    str(err),
                )
                self._registrar_fallo_recuperable(modelo, en_half_open=es_half_open)
                continue
            except (ProveedorIaNoRecuperableException, Exception):
                raise

        raise ultimo_error or ProveedorIaRecuperableException(
            "DRAWI no pudo procesar la solicitud en este momento. Intenta nuevamente."
        )

    def analizar_imagen_con_fallback(
        self,
        *,
        contenido_imagen: bytes,
        mime_type: str,
        prompt_estructural: str,
    ) -> str:
        ultimo_error: ProveedorIaRecuperableException | None = None

        for modelo in self.modelos:
            estado_breaker, esta_abierto = self._evaluar_estado_breaker(modelo)
            if esta_abierto:
                logger.warning(
                    "Circuit breaker OPEN para modelo %s en análisis de imagen. Omitiendo directamente hacia fallback.",
                    modelo,
                )
                continue

            es_half_open = estado_breaker == CircuitState.HALF_OPEN

            try:
                json_str = self.proveedor.analizar_diagrama_imagen(
                    modelo=modelo,
                    contenido_imagen=contenido_imagen,
                    mime_type=mime_type,
                    prompt_estructural=prompt_estructural,
                )
                self._ultimo_modelo_usado = modelo
                self._registrar_exito(modelo)
                return json_str
            except ProveedorIaRecuperableException as err:
                ultimo_error = err
                logger.warning(
                    "Fallo recuperable en análisis de imagen con modelo %s: %s. Saltando inmediatamente al fallback sin reintento.",
                    modelo,
                    str(err),
                )
                self._registrar_fallo_recuperable(modelo, en_half_open=es_half_open)
                continue
            except (ProveedorIaNoRecuperableException, Exception):
                raise

        raise ultimo_error or ProveedorIaRecuperableException(
            "DRAWI no pudo procesar el análisis de imagen en este momento. Intenta nuevamente."
        )

    def ejecutar_audio_con_fallback(
        self,
        *,
        prompt_sistema: str,
        contenido_audio: bytes,
        mime_type: str,
        temperatura: float = 0.2,
    ) -> ResultadoProveedorIa:
        ultimo_error: ProveedorIaRecuperableException | None = None
        alguna_vez_breaker_abierto = False
        inicio_total = time.monotonic()
        total_intentos = 0

        for indice_modelo, modelo in enumerate(self.modelos):
            estado_breaker, esta_abierto = self._evaluar_estado_breaker(modelo)
            if esta_abierto:
                alguna_vez_breaker_abierto = True
                logger.warning(
                    "Circuit breaker OPEN para modelo %s en audio. Omitiendo directamente hacia fallback.",
                    modelo,
                )
                continue

            es_half_open = estado_breaker == CircuitState.HALF_OPEN
            total_intentos += 1

            try:
                resultado = self.proveedor.generar_respuesta_audio(
                    modelo=modelo,
                    prompt_sistema=prompt_sistema,
                    contenido_audio=contenido_audio,
                    mime_type=mime_type,
                    temperatura=temperatura,
                )
                duracion_ms = (time.monotonic() - inicio_total) * 1000.0
                self._registrar_exito(modelo)
                return ResultadoProveedorIa(
                    texto_respuesta=resultado.texto_respuesta,
                    modelo=modelo,
                    intentos=total_intentos,
                    fallback_utilizado=(indice_modelo > 0),
                    breaker_abierto=alguna_vez_breaker_abierto,
                    duracion_ms=duracion_ms,
                )
            except ProveedorIaRecuperableException as err:
                ultimo_error = err
                logger.warning(
                    "Fallo recuperable en audio con modelo %s: %s. Saltando inmediatamente al fallback sin reintento sobre el mismo modelo.",
                    modelo,
                    str(err),
                )
                self._registrar_fallo_recuperable(modelo, en_half_open=es_half_open)
                continue
            except (ProveedorIaNoRecuperableException, Exception):
                raise

        raise ultimo_error or ProveedorIaRecuperableException(
            "DRAWI no pudo procesar la solicitud de audio en este momento. Intenta nuevamente."
        )
