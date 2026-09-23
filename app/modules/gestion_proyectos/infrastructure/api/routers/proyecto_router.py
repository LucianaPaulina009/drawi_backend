from __future__ import annotations

from uuid import UUID
from fastapi import APIRouter, Query, status

from app.core.dependencies import CurrentUser, DBSession, UoWDep
from app.modules.gestion_proyectos.application.queries.proyecto.listar_proyectos_usuario import (
    ListarProyectosUsuarioQuery,
    ListarProyectosUsuarioQueryHandler,
)
from app.modules.gestion_proyectos.application.use_cases.proyecto.actualizar_proyecto import (
    ActualizarProyectoCommand,
    ActualizarProyectoUseCase,
)
from app.modules.gestion_proyectos.application.use_cases.proyecto.agregar_proyecto_favorito import (
    AgregarProyectoFavoritoCommand,
    AgregarProyectoFavoritoUseCase,
)
from app.modules.gestion_proyectos.application.use_cases.proyecto.crear_proyecto import (
    CrearProyectoCommand,
    CrearProyectoUseCase,
)
from app.modules.gestion_proyectos.application.use_cases.proyecto.desmarcar_proyecto_favorito import (
    DesmarcarProyectoFavoritoCommand,
    DesmarcarProyectoFavoritoUseCase,
)
from app.modules.gestion_proyectos.application.use_cases.proyecto.eliminar_proyecto import (
    EliminarProyectoCommand,
    EliminarProyectoUseCase,
)
from app.modules.gestion_proyectos.infrastructure.api.schemas.proyecto_schemas import (
    ActualizarProyectoRequest,
    ListaProyectosRead,
    ProyectoCreadoRead,
    ProyectoRead,
)
from app.modules.gestion_proyectos.infrastructure.persistence.models.proyecto_model import (
    ProyectoModel,
)
from app.modules.diagramas.infrastructure.persistence.repositories.sqlmodel_diagrama_repository import (
    SQLModelDiagramaRepository,
)
from app.modules.gestion_proyectos.infrastructure.persistence.readers.sqlmodel_listado_proyectos_usuario_reader import (
    SQLModelListadoProyectosUsuarioReader,
)
from app.modules.gestion_proyectos.infrastructure.persistence.repositories.sqlmodel_proyecto_favorito_repository import (
    SQLModelProyectoFavoritoRepository,
)
from app.modules.gestion_proyectos.infrastructure.persistence.repositories.sqlmodel_proyecto_repository import (
    SQLModelProyectoRepository,
)

router = APIRouter(prefix="/proyectos", tags=["Proyectos"])


@router.post(
    "/crear",
    response_model=ProyectoCreadoRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un nuevo proyecto",
)
def crear_proyecto(
    usuario: CurrentUser,
    session: DBSession,
    uow: UoWDep,
) -> ProyectoCreadoRead:
    repositorio = SQLModelProyectoRepository(session)
    repositorio_diagramas = SQLModelDiagramaRepository(session)
    caso_uso = CrearProyectoUseCase(repositorio, repositorio_diagramas, uow)
    slug = caso_uso.execute(CrearProyectoCommand(propietario_id=usuario.user_id))
    return ProyectoCreadoRead(slug=slug)


@router.get(
    "/listado",
    response_model=ListaProyectosRead,
    status_code=status.HTTP_200_OK,
    summary="Listar proyectos del usuario autenticado",
)
def listar_proyectos(
    usuario: CurrentUser,
    session: DBSession,
    favoritos: bool = Query(
        default=False, description="Filtrar únicamente proyectos favoritos."
    ),
) -> ListaProyectosRead:
    reader = SQLModelListadoProyectosUsuarioReader(session)
    handler = ListarProyectosUsuarioQueryHandler(reader)
    resultado = handler.execute(
        ListarProyectosUsuarioQuery(
            usuario_id=usuario.user_id, solo_favoritos=favoritos
        )
    )

    items = [
        ProyectoRead(
            id=item.id,
            nombre=item.nombre,
            color=item.color,
            icono=item.icono,
            fecha_actualizacion=item.fecha_actualizacion,
            es_favorito=item.es_favorito,
            slug=item.slug,
            propietario_id=item.propietario_id,
            es_dueno=item.es_dueno,
        )
        for item in resultado.items
    ]

    return ListaProyectosRead(items=items)


@router.patch(
    "/{id_proyecto}/actualizar",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Actualizar parcialmente un proyecto propio",
)
def actualizar_proyecto(
    id_proyecto: UUID,
    datos: ActualizarProyectoRequest,
    usuario: CurrentUser,
    session: DBSession,
    uow: UoWDep,
) -> None:
    repo_proy = SQLModelProyectoRepository(session)
    caso_uso = ActualizarProyectoUseCase(repo_proy, uow)
    caso_uso.execute(
        ActualizarProyectoCommand(
            propietario_id=usuario.user_id,
            proyecto_id=id_proyecto,
            nombre=datos.nombre,
            color=datos.color,
            icono=datos.icono,
        )
    )


@router.delete(
    "/{id_proyecto}/eliminar",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar lógicamente un proyecto propio",
)
def eliminar_proyecto(
    id_proyecto: UUID,
    usuario: CurrentUser,
    session: DBSession,
    uow: UoWDep,
) -> None:
    repo_proy = SQLModelProyectoRepository(session)
    caso_uso = EliminarProyectoUseCase(repo_proy, uow)
    caso_uso.execute(
        EliminarProyectoCommand(
            propietario_id=usuario.user_id,
            proyecto_id=id_proyecto,
        )
    )


@router.post(
    "/{id_proyecto}/agregar_favorito",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Marcar un proyecto propio como favorito",
)
def agregar_favorito(
    id_proyecto: UUID,
    usuario: CurrentUser,
    session: DBSession,
    uow: UoWDep,
) -> None:
    repo_proy = SQLModelProyectoRepository(session)
    repo_fav = SQLModelProyectoFavoritoRepository(session)
    caso_uso = AgregarProyectoFavoritoUseCase(repo_proy, repo_fav, uow)
    caso_uso.execute(
        AgregarProyectoFavoritoCommand(
            propietario_id=usuario.user_id,
            proyecto_id=id_proyecto,
        )
    )


@router.post(
    "/{id_proyecto}/desmarcar_favorito",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Quitar la marca de favorito de un proyecto propio",
)
def desmarcar_favorito(
    id_proyecto: UUID,
    usuario: CurrentUser,
    session: DBSession,
    uow: UoWDep,
) -> None:
    repo_proy = SQLModelProyectoRepository(session)
    repo_fav = SQLModelProyectoFavoritoRepository(session)
    caso_uso = DesmarcarProyectoFavoritoUseCase(repo_proy, repo_fav, uow)
    caso_uso.execute(
        DesmarcarProyectoFavoritoCommand(
            propietario_id=usuario.user_id,
            proyecto_id=id_proyecto,
        )
    )
