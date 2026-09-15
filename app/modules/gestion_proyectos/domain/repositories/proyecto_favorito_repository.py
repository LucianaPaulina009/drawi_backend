from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from app.modules.gestion_proyectos.domain.entities.proyecto_favorito import (
    ProyectoFavorito,
)


class ProyectoFavoritoRepository(ABC):
    """Contrato de persistencia para la relación ProyectoFavorito."""

    @abstractmethod
    def obtener_activo(
        self, usuario_id: str, proyecto_id: UUID
    ) -> ProyectoFavorito | None:
        """Obtiene la relación de favorito activa para un usuario y proyecto."""

    @abstractmethod
    def obtener_eliminado(
        self, usuario_id: str, proyecto_id: UUID
    ) -> ProyectoFavorito | None:
        """Obtiene la relación de favorito previamente eliminada lógicamente (para restauración)."""

    @abstractmethod
    def guardar(self, favorito: ProyectoFavorito) -> None:
        """Inserta una nueva relación de favorito."""

    @abstractmethod
    def restaurar(self, favorito_id: UUID) -> None:
        """Restaura una relación de favorito previamente eliminada lógicamente."""

    @abstractmethod
    def eliminar(self, usuario_id: str, proyecto_id: UUID) -> None:
        """Marca como eliminada lógicamente la relación de favorito activa."""
