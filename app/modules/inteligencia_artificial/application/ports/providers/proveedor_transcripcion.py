from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class ResultadoTranscripcion:
    texto: str
    idioma: str | None = None


class ProveedorTranscripcion(ABC):
    """Puerto para interactuar con proveedores externos de Speech-to-Text."""

    @abstractmethod
    def transcribir_audio(
        self,
        *,
        contenido_audio: bytes,
        mime_type: str,
        idioma: str | None = None,
    ) -> ResultadoTranscripcion:
        """
        Transcribe el contenido de audio a texto normalizado.

        Lanza:
            - ProveedorTranscripcionRecuperableException: si hay timeout, rate limit o falla temporal de red/servicio.
            - ProveedorTranscripcionException: si ocurre un fallo permanente en el proveedor externo.
        """
