from __future__ import annotations

import logging
from typing import Final, Sequence

from app.modules.inteligencia_artificial.application.ports.providers.proveedor_ia import (
    ProveedorIa,
    ResultadoProveedorIa,
)
from app.modules.inteligencia_artificial.domain.exceptions import (
    ProveedorIaNoRecuperableException,
    ProveedorIaRecuperableException,
)

logger = logging.getLogger(__name__)

MODELOS_GEMINI_ORDENADOS: Final[tuple[str, ...]] = (
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-3-flash-preview",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
)


class EstrategiaModelosGemini:
    """Coordinador de fallback secuencial entre modelos de Google Gemini."""

    def __init__(
        self,
        proveedor: ProveedorIa,
        modelos: Sequence[str] = MODELOS_GEMINI_ORDENADOS,
    ) -> None:
        self.proveedor = proveedor
        self.modelos = tuple(modelos)

    def ejecutar_con_fallback(
        self,
        *,
        prompt_sistema: str,
        mensaje_usuario: str,
        temperatura: float = 0.2,
    ) -> ResultadoProveedorIa:
        ultimo_error: ProveedorIaRecuperableException | None = None

        for modelo in self.modelos:
            try:
                resultado = self.proveedor.generar_respuesta(
                    modelo=modelo,
                    prompt_sistema=prompt_sistema,
                    mensaje_usuario=mensaje_usuario,
                    temperatura=temperatura,
                )
                return resultado
            except ProveedorIaRecuperableException as err:
                logger.warning(
                    "Error recuperable en modelo %s: %s. Intentando siguiente modelo en la estrategia.",
                    modelo,
                    str(err),
                )
                ultimo_error = err
                continue
            except (ProveedorIaNoRecuperableException, Exception):
                # Errores no recuperables, de autorización o de dominio detienen el flujo sin fallback
                raise

        raise ultimo_error or ProveedorIaRecuperableException(
            "Se agotaron todos los modelos de la estrategia sin obtener respuesta."
        )
