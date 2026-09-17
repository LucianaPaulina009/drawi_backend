from abc import ABC, abstractmethod
from uuid import UUID

from app.modules.gestion_colaboradores.domain.entities.colaborador_proyecto import (
    ColaboradorProyecto,
)


class ColaboradorProyectoRepository(ABC):
    """Contrato del repositorio de colaboradores de proyecto."""

    @abstractmethod
    def obtener_por_id(self, colaborador_id: UUID) -> ColaboradorProyecto | None:
        """Obtiene un colaborador activo o bloqueado por su ID."""

    @abstractmethod
    def obtener_por_proyecto_y_usuario(
        self, id_proyecto: UUID, id_usuario: str
    ) -> ColaboradorProyecto | None:
        """Obtiene el colaborador de un proyecto y usuario (incluyendo bloqueados, excluyendo eliminados)."""

    @abstractmethod
    def listar_por_proyecto(self, id_proyecto: UUID) -> list[ColaboradorProyecto]:
        """Lista todos los colaboradores no eliminados de un proyecto."""

    @abstractmethod
    def guardar(self, colaborador: ColaboradorProyecto) -> None:
        """Persiste un colaborador nuevo o actualiza uno existente."""

    @abstractmethod
    def eliminar(self, colaborador_id: UUID) -> None:
        """Elimina lógicamente un colaborador (baja de membresía activa)."""
