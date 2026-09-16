from abc import ABC, abstractmethod
from uuid import UUID

from app.modules.gestion_proyectos.domain.entities.invitacion import Invitacion


class InvitacionRepository(ABC):
    """Contrato del repositorio de invitaciones a proyectos."""

    @abstractmethod
    def obtener_por_id(self, invitacion_id: UUID) -> Invitacion | None:
        """Obtiene una invitación por su ID."""

    @abstractmethod
    def obtener_por_proyecto(self, id_proyecto: UUID) -> Invitacion | None:
        """Obtiene la invitación activa del proyecto si existe."""

    @abstractmethod
    def obtener_por_codigo(self, codigo_acceso: str) -> Invitacion | None:
        """Obtiene una invitación por su código de acceso."""

    @abstractmethod
    def guardar(self, invitacion: Invitacion) -> None:
        """Persiste una invitación nueva o actualiza una existente."""

    @abstractmethod
    def eliminar(self, invitacion_id: UUID) -> None:
        """Elimina lógicamente una invitación."""
