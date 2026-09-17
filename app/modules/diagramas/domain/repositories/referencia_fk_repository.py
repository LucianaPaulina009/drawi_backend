from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from app.modules.diagramas.domain.entities.referencia_fk import ReferenciaFK


class ReferenciaFKRepository(ABC):
    """Contrato de persistencia para referencias FK de Diagramas."""

    @abstractmethod
    def obtener_por_id(self, referencia_id: UUID) -> ReferenciaFK | None:
        """Obtiene una referencia FK activa por identificador."""

    @abstractmethod
    def listar_por_relacion(self, relacion_id: UUID) -> list[ReferenciaFK]:
        """Lista las referencias FK activas de una relación."""

    @abstractmethod
    def listar_por_atributo(self, atributo_id: UUID) -> list[ReferenciaFK]:
        """Lista referencias activas donde el atributo participa."""

    @abstractmethod
    def listar_por_diagrama(self, diagrama_id: UUID) -> list[ReferenciaFK]:
        """Lista todas las referencias FK activas asociadas a las relaciones de un diagrama."""

    @abstractmethod
    def obtener_por_par(
        self,
        relacion_id: UUID,
        id_atributo_fk: UUID,
        id_atributo_referenciado: UUID,
    ) -> ReferenciaFK | None:
        """Obtiene una referencia FK activa con el par de atributos indicado en la relación."""

    @abstractmethod
    def guardar(self, referencia_fk: ReferenciaFK) -> None:
        """Guarda o actualiza una referencia FK."""

    @abstractmethod
    def eliminar(self, referencia_id: UUID) -> None:
        """Marca una referencia FK como eliminada lógicamente."""

    @abstractmethod
    def eliminar_por_relacion(self, relacion_id: UUID) -> None:
        """Marca como eliminadas las referencias FK activas de una relación."""

    @abstractmethod
    def eliminar_por_atributo(self, atributo_id: UUID) -> None:
        """Marca como eliminadas las referencias FK activas que involucren al atributo como FK o referenciado."""

    @abstractmethod
    def eliminar_por_clase(self, clase_id: UUID) -> None:
        """Marca como eliminadas las referencias FK activas de las relaciones asociadas a una clase."""

    @abstractmethod
    def eliminar_por_diagrama(self, diagrama_id: UUID) -> None:
        """Marca como eliminadas las referencias FK activas de las relaciones de un diagrama."""
