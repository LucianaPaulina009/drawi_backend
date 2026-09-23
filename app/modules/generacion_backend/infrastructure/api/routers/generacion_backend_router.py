from __future__ import annotations

from uuid import UUID
from urllib.parse import quote
from fastapi import APIRouter, Response, status
from fastapi.responses import JSONResponse

from app.core.dependencies import CurrentUser, DBSession, UoWDep
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
from app.modules.inteligencia_artificial.infrastructure.persistence.repositories.sqlmodel_interaccion_ia_repository import (
    SQLModelInteraccionIaRepository,
)
from app.modules.generacion_backend.application.use_cases.generar_backend import (
    GenerarBackendCommand,
    GenerarBackendUseCase,
    ResultadoGeneracionError,
    ResultadoGeneracionExito,
)
from app.modules.generacion_backend.infrastructure.api.schemas.generacion_backend_schemas import (
    DiagnosticoGeneracionErrorSchema,
    ErrorBloqueanteSchema,
)
from app.modules.generacion_backend.infrastructure.persistence.repositories.sqlmodel_generacion_backend_repository import (
    SQLModelGeneracionBackendRepository,
)

router = APIRouter(
    prefix="/diagramas",
    tags=["Generación Backend"],
)


@router.post(
    "/{id_diagrama}/generaciones-backend",
    summary="Generar y descargar backend Spring Boot + PostgreSQL desde el diagrama confirmado",
    response_class=Response,
    responses={
        200: {
            "content": {"application/zip": {}},
            "description": "Archivo ZIP con el proyecto Spring Boot generado.",
        },
        422: {
            "model": DiagnosticoGeneracionErrorSchema,
            "description": "Errores estructurales que impiden la generación.",
        },
    },
)
def generar_backend_desde_diagrama(
    id_diagrama: UUID,
    user: CurrentUser,
    session: DBSession,
    uow: UoWDep,
) -> Response:
    """Valida el diagrama confirmado, genera el proyecto Spring Boot y devuelve el ZIP para su descarga."""
    proyecto_repo = SQLModelProyectoRepository(session)
    diagrama_repo = SQLModelDiagramaRepository(session)
    generacion_repo = SQLModelGeneracionBackendRepository(session)
    clase_repo = SQLModelClaseRepository(session)
    atributo_repo = SQLModelAtributoRepository(session)
    relacion_repo = SQLModelRelacionRepository(session)
    referencia_fk_repo = SQLModelReferenciaFKRepository(session)
    estructura_nm_repo = SQLModelEstructuraRelacionNmRepository(session)
    colaborador_repo = SQLModelColaboradorProyectoRepository(session)
    interaccion_repo = SQLModelInteraccionIaRepository(session)

    caso_de_uso = GenerarBackendUseCase(
        uow=uow,
        proyecto_repository=proyecto_repo,
        diagrama_repository=diagrama_repo,
        generacion_repository=generacion_repo,
        clase_repository=clase_repo,
        atributo_repository=atributo_repo,
        relacion_repository=relacion_repo,
        referencia_fk_repository=referencia_fk_repo,
        estructura_nm_repository=estructura_nm_repo,
        colaborador_repository=colaborador_repo,
        interaccion_repository=interaccion_repo,
    )

    comando = GenerarBackendCommand(
        usuario_id=user.user_id,
        diagrama_id=id_diagrama,
        version_plantilla="1.0.0",
    )

    resultado = caso_de_uso.execute(comando)

    if isinstance(resultado, ResultadoGeneracionError):
        errores_schema = [
            ErrorBloqueanteSchema(**e.a_dict())
            for e in resultado.diagnostico.errores_bloqueantes
        ]
        diagnostico_schema = DiagnosticoGeneracionErrorSchema(
            code="DIAGRAMA_NO_GENERABLE",
            message="El diagrama contiene errores que deben corregirse",
            mensaje_chat=resultado.mensaje_chat,
            interaccion_id=str(resultado.interaccion_id) if resultado.interaccion_id else None,
            errores=errores_schema,
            errores_bloqueantes=errores_schema,
        )
        headers: dict[str, str] = {
            "X-Generacion-Backend-Id": str(resultado.generacion_id),
        }
        if resultado.mensaje_chat:
            headers["X-Mensaje-Chat"] = quote(resultado.mensaje_chat)
        if resultado.interaccion_id:
            headers["X-Interaccion-Id"] = str(resultado.interaccion_id)

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=diagnostico_schema.model_dump(mode="json"),
            headers=headers,
        )

    headers_200: dict[str, str] = {
        "Content-Disposition": f'attachment; filename="{resultado.nombre_archivo}"',
        "X-Generacion-Backend-Id": str(resultado.generacion_id),
    }
    if resultado.mensaje_chat:
        headers_200["X-Mensaje-Chat"] = quote(resultado.mensaje_chat)
    if resultado.interaccion_id:
        headers_200["X-Interaccion-Id"] = str(resultado.interaccion_id)

    return Response(
        content=resultado.contenido_zip,
        media_type="application/zip",
        headers=headers_200,
    )
