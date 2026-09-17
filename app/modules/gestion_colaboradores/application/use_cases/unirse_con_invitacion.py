from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.modules.diagramas.domain.repositories.diagrama_repository import (
    DiagramaRepository,
)
from app.modules.gestion_colaboradores.domain.entities.colaborador_proyecto import (
    ColaboradorProyecto,
)
from app.modules.gestion_colaboradores.domain.exceptions import (
    InvitacionExpiradaException,
    InvitacionNoEncontradaException,
    UsuarioBloqueadoException,
)
from app.modules.gestion_colaboradores.domain.repositories.colaborador_proyecto_repository import (
    ColaboradorProyectoRepository,
)
from app.modules.gestion_colaboradores.domain.repositories.invitacion_repository import (
    InvitacionRepository,
)
from app.modules.gestion_colaboradores.domain.value_objects.estado_colaborador import (
    EstadoColaborador,
)
from app.modules.gestion_colaboradores.domain.value_objects.rol_colaborador import (
    RolColaborador,
)
from app.modules.gestion_proyectos.domain.exceptions import (
    ProyectoNoEncontradoException,
)
from app.modules.gestion_proyectos.domain.repositories.proyecto_repository import (
    ProyectoRepository,
)
from app.shared.application.ports import UnitOfWork


@dataclass(slots=True)
class UnirseConInvitacionCommand:
    codigo: str
    usuario_id: str


@dataclass(slots=True)
class UnirseConInvitacionResult:
    proyecto_id: UUID
    proyecto_slug: str
    diagrama_id: UUID | None
    rol: str
    mensaje: str


class UnirseConInvitacionUseCase:
    """Caso de uso para que un usuario se una a un proyecto usando un código de invitación válido."""

    def __init__(
        self,
        invitacion_repository: InvitacionRepository,
        proyecto_repository: ProyectoRepository,
        colaborador_repository: ColaboradorProyectoRepository,
        diagrama_repository: DiagramaRepository,
        uow: UnitOfWork,
    ) -> None:
        self.invitacion_repository = invitacion_repository
        self.proyecto_repository = proyecto_repository
        self.colaborador_repository = colaborador_repository
        self.diagrama_repository = diagrama_repository
        self.uow = uow

    def execute(self, command: UnirseConInvitacionCommand) -> UnirseConInvitacionResult:
        invitacion = self.invitacion_repository.obtener_por_codigo(command.codigo)
        if invitacion is None:
            raise InvitacionNoEncontradaException()

        if invitacion.ha_expirado():
            raise InvitacionExpiradaException()

        proyecto = self.proyecto_repository.obtener_por_id(invitacion.id_proyecto)
        if proyecto is None:
            raise ProyectoNoEncontradoException()

        diagramas = self.diagrama_repository.listar_por_proyecto(proyecto.id)
        primer_diagrama_id = diagramas[0].id if diagramas else None

        # Si el usuario es el propietario
        if proyecto.propietario_id == command.usuario_id:
            return UnirseConInvitacionResult(
                proyecto_id=proyecto.id,
                proyecto_slug=proyecto.slug,
                diagrama_id=primer_diagrama_id,
                rol="propietario",
                mensaje="Ya eres el propietario del proyecto.",
            )

        colaborador = self.colaborador_repository.obtener_por_proyecto_y_usuario(
            proyecto.id, command.usuario_id
        )

        if colaborador is not None:
            if colaborador.esta_bloqueado():
                raise UsuarioBloqueadoException()

            # Ya es miembro activo (idempotente)
            return UnirseConInvitacionResult(
                proyecto_id=proyecto.id,
                proyecto_slug=proyecto.slug,
                diagrama_id=primer_diagrama_id,
                rol=colaborador.rol.value,
                mensaje="Ya eres miembro de este proyecto.",
            )

        # Incorporar nuevo miembro
        nuevo_colaborador = ColaboradorProyecto.crear(
            id_proyecto=proyecto.id,
            id_usuario=command.usuario_id,
            rol=RolColaborador.VER,
            estado=EstadoColaborador.ACTIVO,
        )
        self.colaborador_repository.guardar(nuevo_colaborador)
        self.uow.commit()

        return UnirseConInvitacionResult(
            proyecto_id=proyecto.id,
            proyecto_slug=proyecto.slug,
            diagrama_id=primer_diagrama_id,
            rol=RolColaborador.VER.value,
            mensaje="Te has unido al proyecto exitosamente.",
        )
