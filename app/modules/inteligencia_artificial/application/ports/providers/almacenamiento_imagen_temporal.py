from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


class ProveedorAlmacenamientoException(Exception):
    """Error base para operaciones de almacenamiento temporal."""


class ProveedorAlmacenamientoRecuperableException(ProveedorAlmacenamientoException):
    """Error temporal/recuperable al comunicarse con el servicio de almacenamiento."""


@dataclass(frozen=True)
class RecursoImagenTemporal:
    """Metadatos de una imagen subida temporalmente para análisis."""
    public_id: str
    secure_url: str
    formato: str
    bytes_tamano: int


class AlmacenamientoImagenTemporal(ABC):
    """Puerto para el almacenamiento y ciclo de vida temporal de imágenes para análisis IA."""

    @abstractmethod
    def subir(
        self,
        *,
        contenido_imagen: bytes,
        mime_type: str,
        carpeta: str | None = None,
    ) -> RecursoImagenTemporal:
        """
        Sube un archivo de imagen de forma temporal.
        
        Lanza ProveedorAlmacenamientoRecuperableException ante fallos de conexión o timeout.
        Lanza ProveedorAlmacenamientoException ante fallos no recuperables.
        """

    @abstractmethod
    def eliminar(self, *, public_id: str) -> None:
        """
        Elimina el recurso temporal mediante su public_id.
        
        No debe propagar excepciones destructivas si el recurso ya no existe.
        """
