from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from app.modules.generacion_backend.domain.entities.generacion_backend import (
    GeneracionBackend,
)


class GeneracionBackendRepository(ABC):
    """Puerto de repositorio para la persistencia de GeneracionBackend."""

    @abstractmethod
    def guardar(self, generacion: GeneracionBackend) -> GeneracionBackend:
        """Guarda o actualiza una entidad de generación backend."""
        pass

    @abstractmethod
    def obtener_por_id(self, generacion_id: UUID) -> GeneracionBackend | None:
        """Obtiene una generación por su identificador único."""
        pass

    @abstractmethod
    def listar_por_diagrama(
        self, id_diagrama: UUID, limite: int = 50
    ) -> list[GeneracionBackend]:
        """Lista las generaciones asociadas a un diagrama."""
        pass
