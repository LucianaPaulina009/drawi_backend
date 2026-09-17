from __future__ import annotations

from dataclasses import asdict
from uuid import UUID

from app.core.dependencies import CurrentUser, DBSession, UoWDep
from app.modules.diagramas.application.queries.diagrama.listar_diagramas import (
    ListarDiagramasQuery,
    ListarDiagramasQueryHandler,
)
from app.modules.diagramas.application.queries.diagrama.obtener_diagrama import (
    ObtenerDiagramaCompletoQueryHandler,
    ObtenerDiagramaQuery,
)
from app.modules.diagramas.application.use_cases.diagrama.actualizar_diagrama import (
    ActualizarDiagramaCommand,
    ActualizarDiagramaUseCase,
)
from app.modules.diagramas.application.use_cases.diagrama.crear_diagrama import (
    CrearDiagramaCommand,
    CrearDiagramaUseCase,
)
from app.modules.diagramas.application.use_cases.diagrama.eliminar_diagrama import (
    EliminarDiagramaCommand,
    EliminarDiagramaUseCase,
)
from app.modules.diagramas.infrastructure.api.schemas.diagrama_schemas import (
    ActualizarDiagramaRequest,
    ClaseEnDiagramaRead,
    CrearDiagramaRequest,
    DiagramaDetalleRead,
    DiagramaRead,
    ListaDiagramasRead,
)
from app.modules.diagramas.infrastructure.persistence.repositories.sqlmodel_diagrama_repository import (
    SQLModelDiagramaRepository,
)
from app.modules.diagramas.infrastructure.persistence.repositories.sqlmodel_clase_repository import (
    SQLModelClaseRepository,
)
from app.modules.diagramas.infrastructure.persistence.repositories.sqlmodel_atributo_repository import (
    SQLModelAtributoRepository,
)
from app.modules.gestion_colaboradores.infrastructure.persistence.repositories.sqlmodel_colaborador_proyecto_repository import (
    SQLModelColaboradorProyectoRepository,
)
from app.modules.gestion_proyectos.infrastructure.persistence.repositories.sqlmodel_proyecto_repository import (
    SQLModelProyectoRepository,
)
from fastapi import APIRouter, Response, status

router = APIRouter(prefix="/proyectos", tags=["Diagramas"])


def _a_read(diagrama) -> DiagramaRead:
    return DiagramaRead(
        id=diagrama.id,
        id_proyecto=diagrama.id_proyecto,
        nombre=diagrama.nombre,
        numero=diagrama.numero,
    )


@router.get(
    "/{id_proyecto}/diagramas",
    response_model=ListaDiagramasRead,
    status_code=status.HTTP_200_OK,
    summary="Listar diagramas de un proyecto autorizado",
)
def listar_diagramas(
    id_proyecto: UUID,
    usuario: CurrentUser,
    session: DBSession,
) -> ListaDiagramasRead:
    proyecto_repo = SQLModelProyectoRepository(session)
    diagrama_repo = SQLModelDiagramaRepository(session)
    colaborador_repo = SQLModelColaboradorProyectoRepository(session)
    resultado = ListarDiagramasQueryHandler(
        proyecto_repo, diagrama_repo, colaborador_repo
    ).execute(
        ListarDiagramasQuery(
            usuario_id=usuario.user_id,
            proyecto_id=id_proyecto,
        )
    )
    return ListaDiagramasRead(items=[_a_read(diagrama) for diagrama in resultado])


@router.get(
    "/{id_proyecto}/diagramas/{id_diagrama}",
    response_model=DiagramaDetalleRead,
    status_code=status.HTTP_200_OK,
    summary="Consultar un diagrama autorizado",
)
def obtener_diagrama(
    id_proyecto: UUID,
    id_diagrama: UUID,
    usuario: CurrentUser,
    session: DBSession,
) -> DiagramaDetalleRead:
    proyecto_repo = SQLModelProyectoRepository(session)
    diagrama_repo = SQLModelDiagramaRepository(session)
    clase_repo = SQLModelClaseRepository(session)
    atributo_repo = SQLModelAtributoRepository(session)
    colaborador_repo = SQLModelColaboradorProyectoRepository(session)
    resultado = ObtenerDiagramaCompletoQueryHandler(
        proyecto_repo, diagrama_repo, clase_repo, atributo_repo, colaborador_repo
    ).execute(
        ObtenerDiagramaQuery(
            usuario_id=usuario.user_id,
            proyecto_id=id_proyecto,
            diagrama_id=id_diagrama,
        )
    )
    return DiagramaDetalleRead(
        **_a_read(resultado).model_dump(),
        clases=[
            ClaseEnDiagramaRead(
                id=clase.id,
                id_diagrama=clase.id_diagrama,
                nombre=clase.nombre,
                posicion_x=clase.posicion_x,
                posicion_y=clase.posicion_y,
                ancho=clase.ancho,
                atributos=[asdict(atributo) for atributo in clase.atributos],
            )
            for clase in resultado.clases
        ],
    )


@router.post(
    "/{id_proyecto}/diagramas",
    response_model=DiagramaRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear una página de diagrama",
)
def crear_diagrama(
    id_proyecto: UUID,
    usuario: CurrentUser,
    session: DBSession,
    uow: UoWDep,
    datos: CrearDiagramaRequest | None = None,
) -> DiagramaRead:
    proyecto_repo = SQLModelProyectoRepository(session)
    diagrama_repo = SQLModelDiagramaRepository(session)
    diagrama = CrearDiagramaUseCase(proyecto_repo, diagrama_repo, uow).execute(
        CrearDiagramaCommand(
            propietario_id=usuario.user_id,
            proyecto_id=id_proyecto,
            nombre=datos.nombre if datos else None,
        )
    )
    return _a_read(diagrama)


@router.patch(
    "/{id_proyecto}/diagramas/{id_diagrama}",
    response_model=DiagramaRead,
    status_code=status.HTTP_200_OK,
    summary="Renombrar parcialmente un diagrama propio",
)
def actualizar_diagrama(
    id_proyecto: UUID,
    id_diagrama: UUID,
    datos: ActualizarDiagramaRequest,
    usuario: CurrentUser,
    session: DBSession,
    uow: UoWDep,
) -> DiagramaRead:
    proyecto_repo = SQLModelProyectoRepository(session)
    diagrama_repo = SQLModelDiagramaRepository(session)
    diagrama = ActualizarDiagramaUseCase(proyecto_repo, diagrama_repo, uow).execute(
        ActualizarDiagramaCommand(
            propietario_id=usuario.user_id,
            proyecto_id=id_proyecto,
            diagrama_id=id_diagrama,
            nombre=datos.nombre,
        )
    )
    return _a_read(diagrama)


@router.delete(
    "/{id_proyecto}/diagramas/{id_diagrama}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar lógicamente un diagrama propio",
)
def eliminar_diagrama(
    id_proyecto: UUID,
    id_diagrama: UUID,
    usuario: CurrentUser,
    session: DBSession,
    uow: UoWDep,
) -> Response:
    proyecto_repo = SQLModelProyectoRepository(session)
    diagrama_repo = SQLModelDiagramaRepository(session)
    clase_repo = SQLModelClaseRepository(session)
    atributo_repo = SQLModelAtributoRepository(session)
    EliminarDiagramaUseCase(
        proyecto_repo, diagrama_repo, clase_repo, atributo_repo, uow
    ).execute(
        EliminarDiagramaCommand(
            propietario_id=usuario.user_id,
            proyecto_id=id_proyecto,
            diagrama_id=id_diagrama,
        )
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
