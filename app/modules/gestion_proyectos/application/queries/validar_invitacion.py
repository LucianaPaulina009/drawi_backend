from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID
from sqlmodel import Session, select

from app.modules.gestion_proyectos.domain.exceptions import (
    InvitacionExpiradaException,
    InvitacionNoEncontradaException,
    ProyectoNoEncontradoException,
    UsuarioBloqueadoException,
)
from app.modules.gestion_proyectos.domain.repositories.colaborador_proyecto_repository import (
    ColaboradorProyectoRepository,
)
from app.modules.gestion_proyectos.domain.repositories.invitacion_repository import (
    InvitacionRepository,
)
from app.modules.gestion_proyectos.domain.repositories.proyecto_repository import (
    ProyectoRepository,
)
from app.shared.infrastructure.db.better_auth import BetterAuthUser


@dataclass(slots=True)
class ValidarInvitacionQuery:
    codigo: str
    usuario_id: str | None = None


@dataclass(slots=True)
class DetalleValidacionInvitacionDTO:
    codigo: str
    proyecto_id: UUID
    proyecto_nombre: str
    proyecto_slug: str
    propietario_nombre: str
    ha_expirado: bool = False


class ValidarInvitacionQueryHandler:
    """Consulta para validar la vigencia de una invitación y los datos básicos del proyecto."""

    def __init__(
        self,
        invitacion_repository: InvitacionRepository,
        proyecto_repository: ProyectoRepository,
        colaborador_repository: ColaboradorProyectoRepository,
        bd: Session,
    ) -> None:
        self.invitacion_repository = invitacion_repository
        self.proyecto_repository = proyecto_repository
        self.colaborador_repository = colaborador_repository
        self.bd = bd

    def execute(self, query: ValidarInvitacionQuery) -> DetalleValidacionInvitacionDTO:
        invitacion = self.invitacion_repository.obtener_por_codigo(query.codigo)
        if invitacion is None:
            raise InvitacionNoEncontradaException()

        if invitacion.ha_expirado():
            raise InvitacionExpiradaException()

        proyecto = self.proyecto_repository.obtener_por_id(invitacion.id_proyecto)
        if proyecto is None:
            raise ProyectoNoEncontradoException()

        if query.usuario_id:
            if query.usuario_id != proyecto.propietario_id:
                colaborador = self.colaborador_repository.obtener_por_proyecto_y_usuario(
                    proyecto.id, query.usuario_id
                )
                if colaborador and colaborador.esta_bloqueado():
                    raise UsuarioBloqueadoException()

        propietario_user = self.bd.exec(
            select(BetterAuthUser).where(BetterAuthUser.id == proyecto.propietario_id)
        ).first()
        propietario_nombre = (
            propietario_user.name if propietario_user and propietario_user.name else "Propietario"
        )

        return DetalleValidacionInvitacionDTO(
            codigo=invitacion.codigo_acceso,
            proyecto_id=proyecto.id,
            proyecto_nombre=proyecto.nombre,
            proyecto_slug=proyecto.slug,
            propietario_nombre=propietario_nombre,
            ha_expirado=False,
        )
