from __future__ import annotations

import logging
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, File, Form, Query, Response, UploadFile, status

from app.core.dependencies import CurrentUser, DBSession, UoWDep
from app.modules.diagramas.application.queries.diagrama.obtener_diagrama import (
    ObtenerDiagramaCompletoQueryHandler,
)
from app.modules.diagramas.application.services.idempotencia_diagrama import (
    IdempotenciaDiagramaService,
)
from app.modules.diagramas.application.use_cases.atributo.atributo_use_cases import (
    AtributoUseCase,
)
from app.modules.diagramas.application.use_cases.clase.crear_clase import (
    CrearClaseUseCase,
)
from app.modules.diagramas.application.use_cases.estructura_relacion_nm.crear_estructura_relacion_nm import (
    CrearEstructuraRelacionNmUseCase,
)
from app.modules.diagramas.application.use_cases.relacion.crear_relacion import (
    CrearRelacionUseCase,
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
from app.modules.intercambio_enterprise_architect.application.use_cases.exportar_diagrama_ea import (
    ExportarDiagramaEaUseCase,
)
from app.modules.intercambio_enterprise_architect.application.use_cases.importar_diagrama_ea import (
    ImportarDiagramaEaUseCase,
)
from app.modules.intercambio_enterprise_architect.infrastructure.api.schemas.intercambio_enterprise_architect_schemas import (
    ResultadoImportacionEaResponse,
)
from app.shared.domain.exceptions import PayloadTooLargeException

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/diagramas",
    tags=["Intercambio Enterprise Architect"],
)

TAMANO_MAXIMO_ARCHIVO_BYTES = 10 * 1024 * 1024  # 10 MB


@router.get(
    "/{id_diagrama}/enterprise-architect/exportar",
    summary="Exportar diagrama activo en formato XML XMI compatible con Enterprise Architect",
    response_class=Response,
    responses={
        200: {
            "content": {"application/xml": {}},
            "description": "Archivo XML con el modelo XMI 2.1 y la geometría visual de Enterprise Architect.",
        },
        400: {
            "description": "El diagrama actual está en blanco y no puede exportarse.",
        },
    },
)
def exportar_diagrama_ea(
    id_diagrama: UUID,
    usuario: CurrentUser,
    session: DBSession,
    proyecto_id: UUID = Query(..., description="ID del proyecto al que pertenece el diagrama"),
) -> Response:
    """Genera y descarga un archivo XML XMI 2.1 con la estructura y diagramación visual de Enterprise Architect."""
    proyecto_repo = SQLModelProyectoRepository(session)
    diagrama_repo = SQLModelDiagramaRepository(session)
    clase_repo = SQLModelClaseRepository(session)
    atributo_repo = SQLModelAtributoRepository(session)
    colaborador_repo = SQLModelColaboradorProyectoRepository(session)
    relacion_repo = SQLModelRelacionRepository(session)
    referencia_fk_repo = SQLModelReferenciaFKRepository(session)
    estructura_nm_repo = SQLModelEstructuraRelacionNmRepository(session)

    query_diagrama = ObtenerDiagramaCompletoQueryHandler(
        proyecto_repo,
        diagrama_repo,
        clase_repo,
        atributo_repo,
        colaborador_repo,
        relacion_repo,
        referencia_fk_repo,
        estructura_nm_repo,
    )

    caso_de_uso = ExportarDiagramaEaUseCase(
        proyecto_repository=proyecto_repo,
        diagrama_repository=diagrama_repo,
        query_diagrama=query_diagrama,
        colaborador_repository=colaborador_repo,
    )

    contenido_xml, nombre_archivo = caso_de_uso.execute(
        usuario_id=usuario.user_id,
        proyecto_id=proyecto_id,
        diagrama_id=id_diagrama,
    )

    headers = {
        "Content-Disposition": f'attachment; filename="{nombre_archivo}"',
    }

    return Response(
        content=contenido_xml,
        media_type="application/xml; charset=utf-8",
        headers=headers,
    )


@router.post(
    "/{id_diagrama}/enterprise-architect/importar",
    response_model=ResultadoImportacionEaResponse,
    status_code=status.HTTP_200_OK,
    summary="Importar archivo XML/XMI de Enterprise Architect al diagrama activo (requiere lienzo en blanco)",
    responses={
        200: {
            "model": ResultadoImportacionEaResponse,
            "description": "Estadísticas y advertencias de la importación exitosa.",
        },
        400: {
            "description": "Formato de archivo inválido o XML no parseable.",
        },
        409: {
            "description": "El diagrama no está en blanco. Solo se permite importar en páginas vacías.",
        },
        413: {
            "description": "El archivo excede el tamaño máximo permitido de 10 MB.",
        },
    },
)
async def importar_diagrama_ea(
    id_diagrama: UUID,
    usuario: CurrentUser,
    session: DBSession,
    uow: UoWDep,
    proyecto_id: UUID = Form(..., description="ID del proyecto"),
    archivo: UploadFile = File(..., description="Archivo .xml o .xmi de Enterprise Architect"),
) -> ResultadoImportacionEaResponse:
    """Procesa un archivo exportado de Enterprise Architect y reconstruye las clases y relaciones en DRAWI."""
    contenido_bytes = await archivo.read()

    if len(contenido_bytes) > TAMANO_MAXIMO_ARCHIVO_BYTES:
        raise PayloadTooLargeException(
            "El archivo supera el tamaño máximo permitido de 10 MB.",
            code="ARCHIVO_EXCEDE_TAMANO_MAXIMO",
        )

    proyecto_repo = SQLModelProyectoRepository(session)
    diagrama_repo = SQLModelDiagramaRepository(session)
    clase_repo = SQLModelClaseRepository(session)
    atributo_repo = SQLModelAtributoRepository(session)
    relacion_repo = SQLModelRelacionRepository(session)
    referencia_fk_repo = SQLModelReferenciaFKRepository(session)
    estructura_nm_repo = SQLModelEstructuraRelacionNmRepository(session)
    colaborador_repo = SQLModelColaboradorProyectoRepository(session)
    operacion_repo = SQLModelOperacionDiagramaRepository(session)
    idempotencia = IdempotenciaDiagramaService(operacion_repo)

    crear_clase_uc = CrearClaseUseCase(
        proyecto_repository=proyecto_repo,
        diagrama_repository=diagrama_repo,
        clase_repository=clase_repo,
        atributo_repository=atributo_repo,
        uow=uow,
        colaborador_repository=colaborador_repo,
    )

    atributo_uc = AtributoUseCase(
        proyecto_repo,
        diagrama_repo,
        clase_repo,
        atributo_repo,
        uow,
        colaborador_repo,
        referencia_fk_repo,
        relacion_repo,
    )

    crear_relacion_uc = CrearRelacionUseCase(
        proyecto_repository=proyecto_repo,
        diagrama_repository=diagrama_repo,
        clase_repository=clase_repo,
        relacion_repository=relacion_repo,
        uow=uow,
        colaborador_repository=colaborador_repo,
        atributo_repository=atributo_repo,
        referencia_fk_repository=referencia_fk_repo,
    )

    crear_estructura_nm_uc = CrearEstructuraRelacionNmUseCase(
        proyecto_repository=proyecto_repo,
        diagrama_repository=diagrama_repo,
        clase_repository=clase_repo,
        atributo_repository=atributo_repo,
        relacion_repository=relacion_repo,
        referencia_fk_repository=referencia_fk_repo,
        estructura_repository=estructura_nm_repo,
        idempotencia=idempotencia,
        uow=uow,
        colaborador_repository=colaborador_repo,
    )

    caso_de_uso = ImportarDiagramaEaUseCase(
        proyecto_repository=proyecto_repo,
        diagrama_repository=diagrama_repo,
        clase_repository=clase_repo,
        atributo_repository=atributo_repo,
        relacion_repository=relacion_repo,
        referencia_fk_repository=referencia_fk_repo,
        crear_clase_use_case=crear_clase_uc,
        atributo_use_case=atributo_uc,
        crear_relacion_use_case=crear_relacion_uc,
        crear_estructura_nm_use_case=crear_estructura_nm_uc,
        estructura_nm_repository=estructura_nm_repo,
        colaborador_repository=colaborador_repo,
    )

    resultado = caso_de_uso.execute(
        usuario_id=usuario.user_id,
        proyecto_id=proyecto_id,
        diagrama_id=id_diagrama,
        contenido_xml=contenido_bytes,
    )

    return ResultadoImportacionEaResponse(
        diagrama_id=resultado.diagrama_id,
        clases_importadas=resultado.clases_importadas,
        atributos_importados=resultado.atributos_importados,
        relaciones_importadas=resultado.relaciones_importadas,
        estructuras_nm_importadas=resultado.estructuras_nm_importadas,
        advertencias=resultado.advertencias,
    )
