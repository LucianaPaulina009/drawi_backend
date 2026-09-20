from uuid import UUID

from fastapi import APIRouter, Header, Response, status

from app.core.dependencies import CurrentUser, DBSession, UoWDep
from app.modules.diagramas.application.services.idempotencia_diagrama import IdempotenciaDiagramaService
from app.modules.diagramas.application.services.notificador_colaboracion import (
    construir_efectos,
    emitir_evento_mutacion_confirmada,
    proyectar_clase,
    proyectar_estructura_nm,
    proyectar_relacion,
)
from app.modules.diagramas.application.use_cases.estructura_relacion_nm.crear_estructura_relacion_nm import (
    CrearEstructuraRelacionNmCommand,
    CrearEstructuraRelacionNmUseCase,
)
from app.modules.diagramas.application.use_cases.estructura_relacion_nm.eliminar_estructura_relacion_nm import (
    EliminarEstructuraRelacionNmCommand,
    EliminarEstructuraRelacionNmUseCase,
)
from app.modules.diagramas.infrastructure.api.schemas.estructura_relacion_nm_schemas import (
    CrearEstructuraRelacionNmRequest,
    EstructuraRelacionNmRead,
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
from app.modules.diagramas.infrastructure.persistence.repositories.sqlmodel_estructura_relacion_nm_repository import (
    SQLModelEstructuraRelacionNmRepository,
)
from app.modules.diagramas.infrastructure.persistence.repositories.sqlmodel_operacion_diagrama_repository import (
    SQLModelOperacionDiagramaRepository,
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

router = APIRouter(prefix="/diagramas", tags=["Estructuras N:M"])


@router.post(
    "/{id_diagrama}/estructuras-nm",
    response_model=EstructuraRelacionNmRead,
    status_code=status.HTTP_201_CREATED,
)
def crear_estructura_nm(
    id_diagrama: UUID,
    datos: CrearEstructuraRelacionNmRequest,
    usuario: CurrentUser,
    session: DBSession,
    uow: UoWDep,
    idempotency_key: UUID = Header(alias="Idempotency-Key"),
) -> EstructuraRelacionNmRead:
    proyecto_repo = SQLModelProyectoRepository(session)
    diagrama_repo = SQLModelDiagramaRepository(session)
    clase_repo = SQLModelClaseRepository(session)
    atributo_repo = SQLModelAtributoRepository(session)
    relacion_repo = SQLModelRelacionRepository(session)
    referencia_fk_repo = SQLModelReferenciaFKRepository(session)
    estructura_nm_repo = SQLModelEstructuraRelacionNmRepository(session)
    idempotencia = IdempotenciaDiagramaService(SQLModelOperacionDiagramaRepository(session))
    colaborador_repo = SQLModelColaboradorProyectoRepository(session)

    resultado = CrearEstructuraRelacionNmUseCase(
        proyecto_repo,
        diagrama_repo,
        clase_repo,
        atributo_repo,
        relacion_repo,
        referencia_fk_repo,
        estructura_nm_repo,
        idempotencia,
        uow,
        colaborador_repo,
    ).execute(
        CrearEstructuraRelacionNmCommand(
            propietario_id=usuario.user_id,
            diagrama_id=id_diagrama,
            action_id=idempotency_key,
            **datos.model_dump(),
        )
    )

    intermedia_id = UUID(resultado["id_clase_intermedia"])
    rel_orig_id = UUID(resultado["id_relacion_origen"])
    rel_dest_id = UUID(resultado["id_relacion_destino"])
    struct_id = UUID(resultado["id"])

    efectos = construir_efectos(
        clases_actualizadas=[proyectar_clase(clase_repo, atributo_repo, intermedia_id)],
        relaciones_actualizadas=[
            proyectar_relacion(relacion_repo, referencia_fk_repo, rel_orig_id),
            proyectar_relacion(relacion_repo, referencia_fk_repo, rel_dest_id),
        ],
        estructuras_nm_actualizadas=[proyectar_estructura_nm(estructura_nm_repo, struct_id)],
    )
    emitir_evento_mutacion_confirmada(
        diagrama_id=id_diagrama,
        action_id=str(idempotency_key),
        tipo_operacion="CREAR_ESTRUCTURA_NM",
        emisor_id=usuario.user_id,
        efectos=efectos,
    )

    return EstructuraRelacionNmRead(**resultado)


@router.delete(
    "/{id_diagrama}/estructuras-nm/{id_estructura}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def eliminar_estructura_nm(
    id_diagrama: UUID,
    id_estructura: UUID,
    usuario: CurrentUser,
    session: DBSession,
    uow: UoWDep,
) -> Response:
    proyecto_repo = SQLModelProyectoRepository(session)
    diagrama_repo = SQLModelDiagramaRepository(session)
    estructura_nm_repo = SQLModelEstructuraRelacionNmRepository(session)
    clase_repo = SQLModelClaseRepository(session)
    atributo_repo = SQLModelAtributoRepository(session)
    relacion_repo = SQLModelRelacionRepository(session)
    referencia_fk_repo = SQLModelReferenciaFKRepository(session)
    colaborador_repo = SQLModelColaboradorProyectoRepository(session)

    resultado = EliminarEstructuraRelacionNmUseCase(
        proyecto_repo,
        diagrama_repo,
        estructura_nm_repo,
        clase_repo,
        atributo_repo,
        relacion_repo,
        referencia_fk_repo,
        uow,
        colaborador_repo,
    ).execute(
        EliminarEstructuraRelacionNmCommand(
            propietario_id=usuario.user_id,
            diagrama_id=id_diagrama,
            estructura_id=id_estructura,
        )
    )

    efectos = construir_efectos(
        clases_eliminadas=list(resultado.clases_eliminadas),
        relaciones_eliminadas=list(resultado.relaciones_eliminadas),
        estructuras_nm_eliminadas=list(resultado.estructuras_nm_eliminadas),
    )
    emitir_evento_mutacion_confirmada(
        diagrama_id=id_diagrama,
        action_id=None,
        tipo_operacion="ELIMINAR_ESTRUCTURA_NM",
        emisor_id=usuario.user_id,
        efectos=efectos,
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)
