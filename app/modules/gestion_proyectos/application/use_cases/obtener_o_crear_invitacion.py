from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.core.config import settings
from app.modules.gestion_proyectos.domain.entities.invitacion import Invitacion
from app.modules.gestion_proyectos.domain.exceptions import (
    NoAutorizadoProyectoException,
    ProyectoNoEncontradoException,
)
from app.modules.gestion_proyectos.domain.repositories.invitacion_repository import (
    InvitacionRepository,
)
from app.modules.gestion_proyectos.domain.repositories.proyecto_repository import (
    ProyectoRepository,
)
from app.shared.application.ports import UnitOfWork


@dataclass(slots=True)
class ObtenerOCrearInvitacionCommand:
    propietario_id: str
    proyecto_id: UUID


class ObtenerOCrearInvitacionUseCase:
    """Caso de uso para obtener o renovar de forma idempotente la invitación activa del proyecto."""

    def __init__(
        self,
        proyecto_repository: ProyectoRepository,
        invitacion_repository: InvitacionRepository,
        uow: UnitOfWork,
        duracion_dias: int | None = None,
    ) -> None:
        self.proyecto_repository = proyecto_repository
        self.invitacion_repository = invitacion_repository
        self.uow = uow
        self.duracion_dias = duracion_dias

    def execute(self, command: ObtenerOCrearInvitacionCommand) -> Invitacion:
        proyecto = self.proyecto_repository.obtener_por_id(command.proyecto_id)
        if proyecto is None:
            raise ProyectoNoEncontradoException()

        if proyecto.propietario_id != command.propietario_id:
            raise NoAutorizadoProyectoException()

        dias = (
            self.duracion_dias
            if self.duracion_dias is not None
            else settings.INVITACION_DURACION_DIAS
        )

        invitacion = self.invitacion_repository.obtener_por_proyecto(command.proyecto_id)

        if invitacion is None:
            invitacion = Invitacion.crear(
                id_proyecto=command.proyecto_id,
                duracion_dias=dias,
            )
            self.invitacion_repository.guardar(invitacion)
            self.uow.commit()
        elif invitacion.ha_expirado():
            invitacion.renovar(duracion_dias=dias)
            self.invitacion_repository.guardar(invitacion)
            self.uow.commit()

        return invitacion
