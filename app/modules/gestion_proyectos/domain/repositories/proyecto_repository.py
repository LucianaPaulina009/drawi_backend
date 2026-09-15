from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from app.modules.gestion_proyectos.domain.entities.proyecto import Proyecto


class ProyectoRepository(ABC):
    """Contrato de persistencia para la entidad Proyecto."""

    @abstractmethod
    def contar_historicos_por_propietario(self, propietario_id: str) -> int:
        """Cuenta todos los proyectos del propietario, incluidos los eliminados lógicamente."""

    @abstractmethod
    def obtener_por_id(self, proyecto_id: UUID) -> Proyecto | None:
        """Obtiene un proyecto activo por su ID (excluye eliminados lógicamente)."""

    @abstractmethod
    def obtener_por_propietario_y_slug(
        self, propietario_id: str, slug: str
    ) -> Proyecto | None:
        """Obtiene un proyecto por propietario y slug, considerando también el historial."""

    @abstractmethod
    def existe_slug_en_historico(
        self, propietario_id: str, slug: str, excluir_id: UUID | None = None
    ) -> bool:
        """Verifica si un slug ya existe en el historial del propietario para garantizar unicidad."""

    @abstractmethod
    def guardar(self, proyecto: Proyecto) -> None:
        """Guarda o actualiza la entidad Proyecto."""

    @abstractmethod
    def eliminar(self, proyecto_id: UUID) -> None:
        """Marca la eliminación lógica del proyecto."""
