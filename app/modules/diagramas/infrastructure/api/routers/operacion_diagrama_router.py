from __future__ import annotations

from uuid import UUID
from fastapi import APIRouter, Header, status

from app.core.dependencies import CurrentUser, DBSession, UoWDep
from app.modules.diagramas.application.services.idempotencia_diagrama import (
    IdempotenciaDiagramaService,
)
from app.modules.diagramas.application.use_cases.operacion_diagrama.procesar_operacion_diagrama import (
    ProcesarOperacionCommand,
    ProcesarOperacionDiagramaUseCase,
)
from app.modules.diagramas.infrastructure.api.schemas.operacion_diagrama_schemas import (
    OperacionDiagramaRequest,
    OperacionDiagramaResponse,
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

router = APIRouter(prefix="/api/diagramas", tags=["Operaciones Diagrama"])


@router.post(
    "/{id_diagrama}/operaciones",
    response_model=OperacionDiagramaResponse,
    status_code=status.HTTP_200_OK,
    summary="Fachada de operaciones durables e idempotentes del diagramador",
)
def procesar_operacion(
    id_diagrama: UUID,
    datos_req: OperacionDiagramaRequest,
    usuario: CurrentUser,
    session: DBSession,
    uow: UoWDep,
    idempotency_key: UUID = Header(..., alias="Idempotency-Key"),
) -> OperacionDiagramaResponse:
    proyecto_repo = SQLModelProyectoRepository(session)
    diagrama_repo = SQLModelDiagramaRepository(session)
    clase_repo = SQLModelClaseRepository(session)
    atributo_repo = SQLModelAtributoRepository(session)
    relacion_repo = SQLModelRelacionRepository(session)
    referencia_fk_repo = SQLModelReferenciaFKRepository(session)
    estructura_nm_repo = SQLModelEstructuraRelacionNmRepository(session)
    idempotencia_repo = SQLModelOperacionDiagramaRepository(session)
    colaborador_repo = SQLModelColaboradorProyectoRepository(session)

    idempotencia_service = IdempotenciaDiagramaService(idempotencia_repo)

    use_case = ProcesarOperacionDiagramaUseCase(
        proyecto_repository=proyecto_repo,
        diagrama_repository=diagrama_repo,
        clase_repository=clase_repo,
        atributo_repository=atributo_repo,
        relacion_repository=relacion_repo,
        referencia_fk_repository=referencia_fk_repo,
        estructura_nm_repository=estructura_nm_repo,
        idempotencia_service=idempotencia_service,
        uow=uow,
        colaborador_repository=colaborador_repo,
    )

    recibo = use_case.execute(
        ProcesarOperacionCommand(
            propietario_id=usuario.user_id,
            diagrama_id=id_diagrama,
            action_id=idempotency_key,
            tipo=datos_req.tipo,
            datos=datos_req.datos,
        )
    )
    return OperacionDiagramaResponse.model_validate(recibo)
