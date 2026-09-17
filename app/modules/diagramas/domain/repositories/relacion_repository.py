from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from app.modules.diagramas.domain.entities.relacion import Relacion


class RelacionRepository(ABC):
    """Contrato de persistencia para relaciones UML de Diagramas."""

    @abstractmethod
    def obtener_por_id(self, relacion_id: UUID) -> Relacion | None:
        """Obtiene una relación activa por identificador."""

    @abstractmethod
    def listar_por_diagrama(self, diagrama_id: UUID) -> list[Relacion]:
        """Lista las relaciones activas de un diagrama."""

    @abstractmethod
    def listar_por_clase(self, clase_id: UUID) -> list[Relacion]:
        """Lista las relaciones activas donde participa una clase (origen o destino)."""

    @abstractmethod
    def guardar(self, relacion: Relacion) -> None:
        """Guarda o actualiza una relación."""

    @abstractmethod
    def eliminar(self, relacion_id: UUID) -> None:
        """Marca una relación como eliminada lógicamente."""

    @abstractmethod
    def eliminar_por_clase(self, clase_id: UUID) -> None:
        """Marca como eliminadas las relaciones activas vinculadas a una clase."""

    @abstractmethod
    def eliminar_por_diagrama(self, diagrama_id: UUID) -> None:
        """Marca como eliminadas las relaciones activas de un diagrama."""
