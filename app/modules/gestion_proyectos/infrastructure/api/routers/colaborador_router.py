from __future__ import annotations

from uuid import UUID
from fastapi import APIRouter, status

from app.core.dependencies import CurrentUser, DBSession, UoWDep
from app.modules.gestion_proyectos.application.queries.listar_miembros_proyecto import (
    ListarMiembrosProyectoQuery,
    ListarMiembrosProyectoQueryHandler,
)
from app.modules.gestion_proyectos.application.use_cases.bloquear_colaborador import (
    BloquearColaboradorCommand,
    BloquearColaboradorUseCase,
)
from app.modules.gestion_proyectos.application.use_cases.cambiar_rol_colaborador import (
    CambiarRolColaboradorCommand,
    CambiarRolColaboradorUseCase,
)
from app.modules.gestion_proyectos.application.use_cases.desbloquear_colaborador import (
    DesbloquearColaboradorCommand,
    DesbloquearColaboradorUseCase,
)
from app.modules.gestion_proyectos.application.use_cases.remover_colaborador import (
    RemoverColaboradorCommand,
    RemoverColaboradorUseCase,
)
from app.modules.gestion_proyectos.infrastructure.api.schemas.colaborador_schemas import (
    CambiarRolRequest,
    ListaMiembrosRead,
    MiembroRead,
)
from app.modules.gestion_proyectos.infrastructure.persistence.readers.sqlmodel_miembros_proyecto_reader import (
    SQLModelMiembrosProyectoReader,
)
from app.modules.gestion_proyectos.infrastructure.persistence.repositories.sqlmodel_colaborador_proyecto_repository import (
    SQLModelColaboradorProyectoRepository,
)
from app.modules.gestion_proyectos.infrastructure.persistence.repositories.sqlmodel_proyecto_repository import (
    SQLModelProyectoRepository,
)

router = APIRouter(prefix="/proyectos", tags=["Colaboradores"])


@router.get(
    "/{proyecto_id}/miembros",
    response_model=ListaMiembrosRead,
    status_code=status.HTTP_200_OK,
    summary="Listar los miembros y colaboradores de un proyecto",
)
def listar_miembros_proyecto(
    proyecto_id: UUID,
    usuario: CurrentUser,
    session: DBSession,
) -> ListaMiembrosRead:
    repo_proy = SQLModelProyectoRepository(session)
    repo_colab = SQLModelColaboradorProyectoRepository(session)
    reader = SQLModelMiembrosProyectoReader(session)
    handler = ListarMiembrosProyectoQueryHandler(repo_proy, repo_colab, reader)

    miembros = handler.execute(
        ListarMiembrosProyectoQuery(
            usuario_id=usuario.user_id,
            proyecto_id=proyecto_id,
        )
    )

    items = [
        MiembroRead(
            id=m.id,
            usuario_id=m.usuario_id,
            nombre=m.nombre,
            email=m.email,
            avatar_url=m.avatar_url,
            rol=m.rol,
            estado=m.estado,
            es_propietario=m.es_propietario,
        )
        for m in miembros
    ]
    return ListaMiembrosRead(items=items)


@router.patch(
    "/{proyecto_id}/miembros/{colaborador_id}/rol",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Modificar el rol de un colaborador en el proyecto",
)
def cambiar_rol_colaborador(
    proyecto_id: UUID,
    colaborador_id: UUID,
    body: CambiarRolRequest,
    usuario: CurrentUser,
    session: DBSession,
    uow: UoWDep,
) -> None:
    repo_proy = SQLModelProyectoRepository(session)
    repo_colab = SQLModelColaboradorProyectoRepository(session)
    caso_uso = CambiarRolColaboradorUseCase(repo_proy, repo_colab, uow)

    caso_uso.execute(
        CambiarRolColaboradorCommand(
            propietario_id=usuario.user_id,
            proyecto_id=proyecto_id,
            colaborador_id=colaborador_id,
            nuevo_rol=body.rol,
        )
    )


@router.delete(
    "/{proyecto_id}/miembros/{colaborador_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remover a un colaborador del proyecto (baja de membresía)",
)
def remover_colaborador(
    proyecto_id: UUID,
    colaborador_id: UUID,
    usuario: CurrentUser,
    session: DBSession,
    uow: UoWDep,
) -> None:
    repo_proy = SQLModelProyectoRepository(session)
    repo_colab = SQLModelColaboradorProyectoRepository(session)
    caso_uso = RemoverColaboradorUseCase(repo_proy, repo_colab, uow)

    caso_uso.execute(
        RemoverColaboradorCommand(
            propietario_id=usuario.user_id,
            proyecto_id=proyecto_id,
            colaborador_id=colaborador_id,
        )
    )


@router.post(
    "/{proyecto_id}/miembros/{colaborador_id}/bloquear",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Bloquear a un colaborador en el proyecto",
)
def bloquear_colaborador(
    proyecto_id: UUID,
    colaborador_id: UUID,
    usuario: CurrentUser,
    session: DBSession,
    uow: UoWDep,
) -> None:
    repo_proy = SQLModelProyectoRepository(session)
    repo_colab = SQLModelColaboradorProyectoRepository(session)
    caso_uso = BloquearColaboradorUseCase(repo_proy, repo_colab, uow)

    caso_uso.execute(
        BloquearColaboradorCommand(
            propietario_id=usuario.user_id,
            proyecto_id=proyecto_id,
            colaborador_id=colaborador_id,
        )
    )


@router.post(
    "/{proyecto_id}/miembros/{colaborador_id}/desbloquear",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Desbloquear a un colaborador previamente bloqueado en el proyecto",
)
def desbloquear_colaborador(
    proyecto_id: UUID,
    colaborador_id: UUID,
    usuario: CurrentUser,
    session: DBSession,
    uow: UoWDep,
) -> None:
    repo_proy = SQLModelProyectoRepository(session)
    repo_colab = SQLModelColaboradorProyectoRepository(session)
    caso_uso = DesbloquearColaboradorUseCase(repo_proy, repo_colab, uow)

    caso_uso.execute(
        DesbloquearColaboradorCommand(
            propietario_id=usuario.user_id,
            proyecto_id=proyecto_id,
            colaborador_id=colaborador_id,
        )
    )
