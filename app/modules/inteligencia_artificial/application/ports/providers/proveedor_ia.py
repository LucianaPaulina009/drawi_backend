from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class ResultadoProveedorIa:
    texto_respuesta: str
    modelo: str
    intentos: int = 1
    fallback_utilizado: bool = False
    breaker_abierto: bool = False
    duracion_ms: float = 0.0


class ProveedorIa(ABC):
    """Puerto para interactuar con proveedores externos de inteligencia artificial."""

    @abstractmethod
    def generar_respuesta(
        self,
        *,
        modelo: str,
        prompt_sistema: str,
        mensaje_usuario: str,
        temperatura: float = 0.2,
    ) -> ResultadoProveedorIa:
        """
        Invoca el modelo indicado con el prompt dado.
        
        Lanza ProveedorIaRecuperableException en fallos temporales (timeout, rate limit, servicio no disponible).
        Lanza ProveedorIaNoRecuperableException en fallos permanentes (autenticación, parámetros no válidos, etc.).
        """

    def transcribir_audio(
        self,
        *,
        modelo: str,
        contenido_audio: bytes,
        mime_type: str,
        idioma: str = "es",
    ) -> str:
        """
        Transcribe el contenido de audio a texto literal usando el modelo multimodal indicado.

        Lanza ProveedorIaRecuperableException en fallos temporales (timeout, rate limit, servicio no disponible).
        Lanza ProveedorIaNoRecuperableException en fallos permanentes.
        """
        raise NotImplementedError("transcribir_audio no está implementado en este proveedor.")

