from __future__ import annotations

import logging

from app.core.config import settings
from app.modules.inteligencia_artificial.application.ports.providers.proveedor_ia import (
    ProveedorIa,
)
from app.modules.inteligencia_artificial.application.ports.providers.proveedor_transcripcion import (
    ProveedorTranscripcion,
    ResultadoTranscripcion,
)
from app.modules.inteligencia_artificial.application.services.estrategia_modelos_gemini import (
    EstrategiaModelosGemini,
)
from app.modules.inteligencia_artificial.domain.exceptions import (
    ProveedorIaNoRecuperableException,
    ProveedorIaRecuperableException,
    ProveedorTranscripcionException,
    ProveedorTranscripcionRecuperableException,
)
from app.modules.inteligencia_artificial.infrastructure.external.proveedor_google_gemini import (
    ProveedorGoogleGemini,
)

logger = logging.getLogger(__name__)


class ProveedorTranscripcionGemini(ProveedorTranscripcion):
    """Adaptador de transcripción que reutiliza la integración existente de Google Gemini."""

    def __init__(
        self,
        proveedor_ia: ProveedorIa | None = None,
        estrategia: EstrategiaModelosGemini | None = None,
    ) -> None:
        if estrategia is not None:
            self._estrategia = estrategia
        elif proveedor_ia is not None:
            self._estrategia = EstrategiaModelosGemini(proveedor=proveedor_ia)
        else:
            self._estrategia = EstrategiaModelosGemini(proveedor=ProveedorGoogleGemini())

    def transcribir_audio(
        self,
        *,
        contenido_audio: bytes,
        mime_type: str,
        idioma: str | None = None,
    ) -> ResultadoTranscripcion:
        idioma_final = idioma or settings.IA_TRANSCRIPCION_IDIOMA
        try:
            texto = self._estrategia.transcribir_con_fallback(
                contenido_audio=contenido_audio,
                mime_type=mime_type,
                idioma=idioma_final,
            )
            return ResultadoTranscripcion(
                texto=texto,
                idioma=idioma_final,
            )
        except ProveedorIaRecuperableException as err:
            logger.warning("Error recuperable en transcripción Gemini: %s", str(err))
            raise ProveedorTranscripcionRecuperableException(str(err)) from err
        except ProveedorIaNoRecuperableException as err:
            logger.error("Error no recuperable en transcripción Gemini: %s", str(err))
            raise ProveedorTranscripcionException(str(err)) from err
        except Exception as err:
            logger.error("Error inesperado en transcripción Gemini: %s", str(err))
            raise ProveedorTranscripcionException(str(err)) from err
