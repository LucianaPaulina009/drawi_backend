from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Query, status

from app.core.dependencies import CurrentUser, DBSession, UoWDep
from app.modules.diagramas.application.queries.diagrama.obtener_diagrama import (
    ObtenerDiagramaCompletoQueryHandler,
)
from app.modules.diagramas.application.use_cases.atributo.atributo_use_cases import (
    AtributoUseCase,
)
from app.modules.diagramas.application.use_cases.clase.crear_clase import (
    CrearClaseUseCase,
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
from app.modules.inteligencia_artificial.application.ports.providers.proveedor_ia import (
    ProveedorIa,
)
from app.modules.inteligencia_artificial.application.queries.listar_interacciones_ia import (
    ListarInteraccionesIaQuery,
    ListarInteraccionesIaQueryHandler,
)
from app.modules.inteligencia_artificial.application.services.constructor_contexto_diagrama import (
    ConstructorContextoDiagrama,
)
from app.modules.inteligencia_artificial.application.services.ejecutor_plan_ia import (
    EjecutorPlanIa,
)
from app.modules.inteligencia_artificial.application.services.estrategia_modelos_gemini import (
    EstrategiaModelosGemini,
)
from app.modules.inteligencia_artificial.application.use_cases.procesar_mensaje_ia import (
    ProcesarMensajeIaCommand,
    ProcesarMensajeIaUseCase,
)
from app.modules.inteligencia_artificial.domain.entities.interaccion_ia import (
    InteraccionIa,
)
from app.modules.inteligencia_artificial.infrastructure.api.schemas.interaccion_ia_schemas import (
    EnviarMensajeIaRequest,
    InteraccionIaRead,
    ListaInteraccionesIaRead,
)
from app.modules.inteligencia_artificial.infrastructure.external.proveedor_google_gemini import (
    ProveedorGoogleGemini,
)
from app.modules.inteligencia_artificial.infrastructure.persistence.repositories.sqlmodel_interaccion_ia_repository import (
    SQLModelInteraccionIaRepository,
)

router = APIRouter(prefix="/diagramas", tags=["Inteligencia Artificial"])

_proveedor_ia_singleton: ProveedorIa | None = None


def get_proveedor_ia() -> ProveedorIa:
    global _proveedor_ia_singleton
    if _proveedor_ia_singleton is None:
        _proveedor_ia_singleton = ProveedorGoogleGemini()
    return _proveedor_ia_singleton


def set_proveedor_ia_override(override: ProveedorIa | None) -> None:
    global _proveedor_ia_singleton
    _proveedor_ia_singleton = override


def _a_read(entidad: InteraccionIa) -> InteraccionIaRead:
    return InteraccionIaRead(
        id=entidad.id,
        idDiagrama=entidad.id_diagrama,
        idUsuario=entidad.id_usuario,
        tipoInteraccion=(
            entidad.tipo_interaccion.value
            if hasattr(entidad.tipo_interaccion, "value")
            else str(entidad.tipo_interaccion)
        ),
        entradaUsuario=entidad.entrada_usuario,
        respuestaIa=entidad.respuesta_ia,
        urlImagen=entidad.url_imagen,
        estado=(
            entidad.estado.value
            if hasattr(entidad.estado, "value")
            else str(entidad.estado)
        ),
        creadoEn=entidad.creado_en,
    )


@router.get(
    "/{id_diagrama}/interacciones-ia",
    response_model=ListaInteraccionesIaRead,
    status_code=status.HTTP_200_OK,
)
def listar_interacciones_ia(
    id_diagrama: UUID,
    usuario: CurrentUser,
    session: DBSession,
    limit: int = Query(default=40, ge=1, le=100),
    before: UUID | None = Query(default=None),
) -> ListaInteraccionesIaRead:
    proyecto_repo = SQLModelProyectoRepository(session)
    diagrama_repo = SQLModelDiagramaRepository(session)
    interaccion_repo = SQLModelInteraccionIaRepository(session)
    colaborador_repo = SQLModelColaboradorProyectoRepository(session)

    handler = ListarInteraccionesIaQueryHandler(
        proyecto_repository=proyecto_repo,
        diagrama_repository=diagrama_repo,
        interaccion_repository=interaccion_repo,
        colaborador_repository=colaborador_repo,
    )

    interacciones = handler.execute(
        ListarInteraccionesIaQuery(
            usuario_id=usuario.user_id,
            diagrama_id=id_diagrama,
            limite=limit,
            antes_de_id=before,
        )
    )

    return ListaInteraccionesIaRead(
        items=[_a_read(i) for i in interacciones],
        siguienteCursor=None,
    )


@router.post(
    "/{id_diagrama}/interacciones-ia",
    response_model=InteraccionIaRead,
    status_code=status.HTTP_201_CREATED,
)
def enviar_mensaje_ia(
    id_diagrama: UUID,
    payload: EnviarMensajeIaRequest,
    usuario: CurrentUser,
    session: DBSession,
    uow: UoWDep,
) -> InteraccionIaRead:
    proyecto_repo = SQLModelProyectoRepository(session)
    diagrama_repo = SQLModelDiagramaRepository(session)
    interaccion_repo = SQLModelInteraccionIaRepository(session)
    clase_repo = SQLModelClaseRepository(session)
    atributo_repo = SQLModelAtributoRepository(session)
    relacion_repo = SQLModelRelacionRepository(session)
    referencia_fk_repo = SQLModelReferenciaFKRepository(session)
    estructura_nm_repo = SQLModelEstructuraRelacionNmRepository(session)
    colaborador_repo = SQLModelColaboradorProyectoRepository(session)

    query_diagrama_completo = ObtenerDiagramaCompletoQueryHandler(
        proyecto_repository=proyecto_repo,
        diagrama_repository=diagrama_repo,
        clase_repository=clase_repo,
        atributo_repository=atributo_repo,
        colaborador_repository=colaborador_repo,
        relacion_repository=relacion_repo,
        referencia_fk_repository=referencia_fk_repo,
        estructura_nm_repository=estructura_nm_repo,
    )

    constructor_contexto = ConstructorContextoDiagrama(
        query_diagrama=query_diagrama_completo,
        interaccion_repo=interaccion_repo,
    )

    proveedor = get_proveedor_ia()
    coordinador_gemini = EstrategiaModelosGemini(proveedor)

    crear_clase_use_case = CrearClaseUseCase(
        proyecto_repository=proyecto_repo,
        diagrama_repository=diagrama_repo,
        clase_repository=clase_repo,
        atributo_repository=atributo_repo,
        uow=uow,
        colaborador_repository=colaborador_repo,
    )

    atributo_use_case = AtributoUseCase(
        p=proyecto_repo,
        d=diagrama_repo,
        c=clase_repo,
        a=atributo_repo,
        u=uow,
        col=colaborador_repo,
        rfk=referencia_fk_repo,
        relacion_repository=relacion_repo,
        estructura_repository=estructura_nm_repo,
    )

    crear_relacion_use_case = CrearRelacionUseCase(
        proyecto_repository=proyecto_repo,
        diagrama_repository=diagrama_repo,
        clase_repository=clase_repo,
        atributo_repository=atributo_repo,
        relacion_repository=relacion_repo,
        referencia_fk_repository=referencia_fk_repo,
        uow=uow,
        colaborador_repository=colaborador_repo,
    )

    ejecutor_plan = EjecutorPlanIa(
        crear_clase_use_case=crear_clase_use_case,
        atributo_use_case=atributo_use_case,
        crear_relacion_use_case=crear_relacion_use_case,
        clase_repository=clase_repo,
        atributo_repository=atributo_repo,
        relacion_repository=relacion_repo,
        referencia_fk_repository=referencia_fk_repo,
    )

    use_case = ProcesarMensajeIaUseCase(
        proyecto_repository=proyecto_repo,
        diagrama_repository=diagrama_repo,
        interaccion_repository=interaccion_repo,
        clase_repository=clase_repo,
        constructor_contexto=constructor_contexto,
        coordinador_gemini=coordinador_gemini,
        ejecutor_plan=ejecutor_plan,
        uow=uow,
        colaborador_repository=colaborador_repo,
    )

    interaccion = use_case.execute(
        ProcesarMensajeIaCommand(
            usuario_id=usuario.user_id,
            diagrama_id=id_diagrama,
            texto=payload.texto,
            clave_idempotencia=payload.clave_idempotencia,
        )
    )

    return _a_read(interaccion)
