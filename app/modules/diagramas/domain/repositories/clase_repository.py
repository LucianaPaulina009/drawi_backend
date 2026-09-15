from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from app.modules.diagramas.domain.entities.clase import Clase


class ClaseRepository(ABC):
    """Contrato de persistencia para clases de Diagramas."""

    @abstractmethod
    def obtener_por_id(self, clase_id: UUID) -> Clase | None:
        """Obtiene una clase activa por identificador."""

    @abstractmethod
    def listar_por_diagrama(self, diagrama_id: UUID) -> list[Clase]:
        """Lista las clases activas de un diagrama."""

    @abstractmethod
    def guardar(self, clase: Clase) -> None:
        """Guarda o actualiza una clase."""

    @abstractmethod
    def eliminar(self, clase_id: UUID) -> None:
        """Marca una clase como eliminada lógicamente."""

    @abstractmethod
    def eliminar_por_diagrama(self, diagrama_id: UUID) -> None:
        """Marca lógicamente las clases activas de un diagrama."""
