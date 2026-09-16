from __future__ import annotations

from uuid import UUID
from fastapi import APIRouter, status

from app.core.dependencies import CurrentUser, DBSession, OptionalUser, UoWDep
from app.modules.diagramas.infrastructure.persistence.repositories.sqlmodel_diagrama_repository import (
    SQLModelDiagramaRepository,
)
from app.modules.gestion_proyectos.application.queries.validar_invitacion import (
    ValidarInvitacionQuery,
    ValidarInvitacionQueryHandler,
)
from app.modules.gestion_proyectos.application.use_cases.obtener_o_crear_invitacion import (
    ObtenerOCrearInvitacionCommand,
    ObtenerOCrearInvitacionUseCase,
)
from app.modules.gestion_proyectos.application.use_cases.unirse_con_invitacion import (
    UnirseConInvitacionCommand,
    UnirseConInvitacionUseCase,
)
from app.modules.gestion_proyectos.infrastructure.api.schemas.invitacion_schemas import (
    InvitacionRead,
    UnirseInvitacionResponse,
    ValidarInvitacionResponse,
)
from app.modules.gestion_proyectos.infrastructure.persistence.repositories.sqlmodel_colaborador_proyecto_repository import (
    SQLModelColaboradorProyectoRepository,
)
from app.modules.gestion_proyectos.infrastructure.persistence.repositories.sqlmodel_invitacion_repository import (
    SQLModelInvitacionRepository,
)
from app.modules.gestion_proyectos.infrastructure.persistence.repositories.sqlmodel_proyecto_repository import (
    SQLModelProyectoRepository,
)

router = APIRouter(tags=["Invitaciones"])


@router.post(
    "/proyectos/{proyecto_id}/invitacion",
    response_model=InvitacionRead,
    status_code=status.HTTP_200_OK,
    summary="Obtener o renovar el enlace de invitación único del proyecto",
)
def obtener_o_crear_invitacion(
    proyecto_id: UUID,
    usuario: CurrentUser,
    session: DBSession,
    uow: UoWDep,
) -> InvitacionRead:
    repo_proy = SQLModelProyectoRepository(session)
    repo_inv = SQLModelInvitacionRepository(session)
    caso_uso = ObtenerOCrearInvitacionUseCase(repo_proy, repo_inv, uow)

    invitacion = caso_uso.execute(
        ObtenerOCrearInvitacionCommand(
            propietario_id=usuario.user_id,
            proyecto_id=proyecto_id,
        )
    )

    return InvitacionRead(
        id=invitacion.id,
        id_proyecto=invitacion.id_proyecto,
        codigo_acceso=invitacion.codigo_acceso,
        fecha_expiracion=invitacion.fecha_expiracion,
    )


@router.get(
    "/invitaciones/{codigo}",
    response_model=ValidarInvitacionResponse,
    status_code=status.HTTP_200_OK,
    summary="Validar código de invitación e información del proyecto",
)
def validar_invitacion(
    codigo: str,
    session: DBSession,
    usuario: OptionalUser = None,
) -> ValidarInvitacionResponse:
    repo_inv = SQLModelInvitacionRepository(session)
    repo_proy = SQLModelProyectoRepository(session)
    repo_colab = SQLModelColaboradorProyectoRepository(session)
    handler = ValidarInvitacionQueryHandler(repo_inv, repo_proy, repo_colab, session)

    usuario_id = usuario.user_id if usuario else None
    dto = handler.execute(ValidarInvitacionQuery(codigo=codigo, usuario_id=usuario_id))

    return ValidarInvitacionResponse(
        codigo=dto.codigo,
        proyecto_id=dto.proyecto_id,
        proyecto_nombre=dto.proyecto_nombre,
        proyecto_slug=dto.proyecto_slug,
        propietario_nombre=dto.propietario_nombre,
        ha_expirado=dto.ha_expirado,
    )


@router.post(
    "/invitaciones/{codigo}/unirse",
    response_model=UnirseInvitacionResponse,
    status_code=status.HTTP_200_OK,
    summary="Unirse a un proyecto mediante código de invitación",
)
def unirse_a_proyecto(
    codigo: str,
    usuario: CurrentUser,
    session: DBSession,
    uow: UoWDep,
) -> UnirseInvitacionResponse:
    repo_inv = SQLModelInvitacionRepository(session)
    repo_proy = SQLModelProyectoRepository(session)
    repo_colab = SQLModelColaboradorProyectoRepository(session)
    repo_diag = SQLModelDiagramaRepository(session)

    caso_uso = UnirseConInvitacionUseCase(
        invitacion_repository=repo_inv,
        proyecto_repository=repo_proy,
        colaborador_repository=repo_colab,
        diagrama_repository=repo_diag,
        uow=uow,
    )

    resultado = caso_uso.execute(
        UnirseConInvitacionCommand(
            codigo=codigo,
            usuario_id=usuario.user_id,
        )
    )

    return UnirseInvitacionResponse(
        proyecto_id=resultado.proyecto_id,
        proyecto_slug=resultado.proyecto_slug,
        diagrama_id=resultado.diagrama_id,
        rol=resultado.rol,
        mensaje=resultado.mensaje,
    )
