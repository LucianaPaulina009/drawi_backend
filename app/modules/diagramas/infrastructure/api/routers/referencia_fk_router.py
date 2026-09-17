from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Response, status

from app.core.dependencies import CurrentUser, DBSession, UoWDep
from app.modules.diagramas.application.queries.referencia_fk.listar_referencias_fk import (
    ListarReferenciasFKQuery,
    ListarReferenciasFKQueryHandler,
)
from app.modules.diagramas.application.queries.referencia_fk.obtener_referencia_fk import (
    ObtenerReferenciaFKQuery,
    ObtenerReferenciaFKQueryHandler,
)
from app.modules.diagramas.application.use_cases.referencia_fk.actualizar_referencia_fk import (
    ActualizarReferenciaFKCommand,
    ActualizarReferenciaFKUseCase,
)
from app.modules.diagramas.application.use_cases.referencia_fk.crear_referencia_fk import (
    CrearReferenciaFKCommand,
    CrearReferenciaFKUseCase,
)
from app.modules.diagramas.application.use_cases.referencia_fk.eliminar_referencia_fk import (
    EliminarReferenciaFKCommand,
    EliminarReferenciaFKUseCase,
)
from app.modules.diagramas.infrastructure.api.schemas.referencia_fk_schemas import (
    ActualizarReferenciaFKRequest,
    CrearReferenciaFKRequest,
    ListaReferenciasFKRead,
    ReferenciaFKRead,
)
from app.modules.diagramas.infrastructure.persistence.repositories.sqlmodel_atributo_repository import (
    SQLModelAtributoRepository,
)
from app.modules.diagramas.infrastructure.persistence.repositories.sqlmodel_clase_repository import (
    SQLModelClaseRepository,
)
from app.modules.diagramas.infrastructure.persistence.repositories.sqlmodel_diagrama_repository import (
    SQLModelDiagramaRepository,
)
from app.modules.diagramas.infrastructure.persistence.repositories.sqlmodel_referencia_fk_repository import (
    SQLModelReferenciaFKRepository,
)
from app.modules.diagramas.infrastructure.persistence.repositories.sqlmodel_relacion_repository import (
    SQLModelRelacionRepository,
)
from app.modules.gestion_colaboradores.infrastructure.persistence.repositories.sqlmodel_colaborador_proyecto_repository import (
    SQLModelColaboradorProyectoRepository,
)
from app.modules.gestion_proyectos.infrastructure.persistence.repositories.sqlmodel_proyecto_repository import (
    SQLModelProyectoRepository,
)

router = APIRouter(prefix="/relaciones", tags=["Referencias FK"])


def _a_referencia_fk_read(referencia) -> ReferenciaFKRead:
    return ReferenciaFKRead(
        id=referencia.id,
        id_relacion=referencia.id_relacion,
        id_atributo_fk=referencia.id_atributo_fk,
        id_atributo_referenciado=referencia.id_atributo_referenciado,
        on_delete=referencia.on_delete,
        on_update=referencia.on_update,
    )


@router.get(
    "/{id_relacion}/referencias-fk",
    response_model=ListaReferenciasFKRead,
    status_code=status.HTTP_200_OK,
    summary="Listar referencias FK de una relación autorizada",
)
def listar_referencias_fk(
    id_relacion: UUID,
    usuario: CurrentUser,
    session: DBSession,
) -> ListaReferenciasFKRead:
    proyecto_repo = SQLModelProyectoRepository(session)
    diagrama_repo = SQLModelDiagramaRepository(session)
    relacion_repo = SQLModelRelacionRepository(session)
    referencia_fk_repo = SQLModelReferenciaFKRepository(session)
    colaborador_repo = SQLModelColaboradorProyectoRepository(session)

    referencias = ListarReferenciasFKQueryHandler(
        proyecto_repo,
        diagrama_repo,
        relacion_repo,
        referencia_fk_repo,
        colaborador_repo,
    ).execute(
        ListarReferenciasFKQuery(
            propietario_id=usuario.user_id,
            relacion_id=id_relacion,
        )
    )
    return ListaReferenciasFKRead(
        items=[_a_referencia_fk_read(ref) for ref in referencias]
    )


@router.get(
    "/{id_relacion}/referencias-fk/{id_referencia}",
    response_model=ReferenciaFKRead,
    status_code=status.HTTP_200_OK,
    summary="Consultar una referencia FK de una relación autorizada",
)
def obtener_referencia_fk(
    id_relacion: UUID,
    id_referencia: UUID,
    usuario: CurrentUser,
    session: DBSession,
) -> ReferenciaFKRead:
    proyecto_repo = SQLModelProyectoRepository(session)
    diagrama_repo = SQLModelDiagramaRepository(session)
    relacion_repo = SQLModelRelacionRepository(session)
    referencia_fk_repo = SQLModelReferenciaFKRepository(session)
    colaborador_repo = SQLModelColaboradorProyectoRepository(session)

    referencia = ObtenerReferenciaFKQueryHandler(
        proyecto_repo,
        diagrama_repo,
        relacion_repo,
        referencia_fk_repo,
        colaborador_repo,
    ).execute(
        ObtenerReferenciaFKQuery(
            propietario_id=usuario.user_id,
            relacion_id=id_relacion,
            referencia_id=id_referencia,
        )
    )
    return _a_referencia_fk_read(referencia)


@router.post(
    "/{id_relacion}/referencias-fk",
    response_model=ReferenciaFKRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear una referencia FK en una relación autorizada",
)
def crear_referencia_fk(
    id_relacion: UUID,
    datos: CrearReferenciaFKRequest,
    usuario: CurrentUser,
    session: DBSession,
    uow: UoWDep,
) -> ReferenciaFKRead:
    proyecto_repo = SQLModelProyectoRepository(session)
    diagrama_repo = SQLModelDiagramaRepository(session)
    relacion_repo = SQLModelRelacionRepository(session)
    clase_repo = SQLModelClaseRepository(session)
    atributo_repo = SQLModelAtributoRepository(session)
    referencia_fk_repo = SQLModelReferenciaFKRepository(session)
    colaborador_repo = SQLModelColaboradorProyectoRepository(session)

    referencia = CrearReferenciaFKUseCase(
        proyecto_repo,
        diagrama_repo,
        relacion_repo,
        clase_repo,
        atributo_repo,
        referencia_fk_repo,
        uow,
        colaborador_repo,
    ).execute(
        CrearReferenciaFKCommand(
            propietario_id=usuario.user_id,
            relacion_id=id_relacion,
            id_referencia_fk=datos.id_referencia_fk,
            id_atributo_fk=datos.id_atributo_fk,
            id_atributo_referenciado=datos.id_atributo_referenciado,
            on_delete=datos.on_delete,
            on_update=datos.on_update,
        )
    )
    return _a_referencia_fk_read(referencia)


@router.patch(
    "/{id_relacion}/referencias-fk/{id_referencia}",
    response_model=ReferenciaFKRead,
    status_code=status.HTTP_200_OK,
    summary="Actualizar parcialmente una referencia FK autorizada",
)
def actualizar_referencia_fk(
    id_relacion: UUID,
    id_referencia: UUID,
    datos: ActualizarReferenciaFKRequest,
    usuario: CurrentUser,
    session: DBSession,
    uow: UoWDep,
) -> ReferenciaFKRead:
    proyecto_repo = SQLModelProyectoRepository(session)
    diagrama_repo = SQLModelDiagramaRepository(session)
    relacion_repo = SQLModelRelacionRepository(session)
    clase_repo = SQLModelClaseRepository(session)
    atributo_repo = SQLModelAtributoRepository(session)
    referencia_fk_repo = SQLModelReferenciaFKRepository(session)
    colaborador_repo = SQLModelColaboradorProyectoRepository(session)

    referencia = ActualizarReferenciaFKUseCase(
        proyecto_repo,
        diagrama_repo,
        relacion_repo,
        clase_repo,
        atributo_repo,
        referencia_fk_repo,
        uow,
        colaborador_repo,
    ).execute(
        ActualizarReferenciaFKCommand(
            propietario_id=usuario.user_id,
            relacion_id=id_relacion,
            referencia_id=id_referencia,
            id_atributo_fk=datos.id_atributo_fk,
            id_atributo_referenciado=datos.id_atributo_referenciado,
            on_delete=datos.on_delete,
            on_update=datos.on_update,
        )
    )
    return _a_referencia_fk_read(referencia)


@router.delete(
    "/{id_relacion}/referencias-fk/{id_referencia}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar lógicamente una referencia FK autorizada",
)
def eliminar_referencia_fk(
    id_relacion: UUID,
    id_referencia: UUID,
    usuario: CurrentUser,
    session: DBSession,
    uow: UoWDep,
) -> Response:
    proyecto_repo = SQLModelProyectoRepository(session)
    diagrama_repo = SQLModelDiagramaRepository(session)
    relacion_repo = SQLModelRelacionRepository(session)
    referencia_fk_repo = SQLModelReferenciaFKRepository(session)
    atributo_repo = SQLModelAtributoRepository(session)
    colaborador_repo = SQLModelColaboradorProyectoRepository(session)

    EliminarReferenciaFKUseCase(
        proyecto_repo,
        diagrama_repo,
        relacion_repo,
        referencia_fk_repo,
        uow,
        colaborador_repo,
        atributo_repo,
    ).execute(
        EliminarReferenciaFKCommand(
            propietario_id=usuario.user_id,
            relacion_id=id_relacion,
            referencia_id=id_referencia,
        )
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
