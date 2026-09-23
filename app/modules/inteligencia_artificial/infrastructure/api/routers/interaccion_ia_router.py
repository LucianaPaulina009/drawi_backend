from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, File, Form, Query, UploadFile, status

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
from app.modules.inteligencia_artificial.application.ports.providers.proveedor_transcripcion import (
    ProveedorTranscripcion,
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
from app.modules.inteligencia_artificial.application.use_cases.procesar_audio_diagrama_ia import (
    ProcesarAudioDiagramaIaCommand,
    ProcesarAudioDiagramaIaUseCase,
)
from app.modules.inteligencia_artificial.application.use_cases.procesar_imagen_diagrama_ia import (
    ProcesarImagenDiagramaIaCommand,
    ProcesarImagenDiagramaIaUseCase,
)
from app.modules.inteligencia_artificial.application.use_cases.procesar_mensaje_ia import (
    ProcesarMensajeIaCommand,
    ProcesarMensajeIaUseCase,
)
from app.modules.inteligencia_artificial.application.use_cases.transcribir_audio_ia import (
    TranscribirAudioIaCommand,
    TranscribirAudioIaUseCase,
)
from app.modules.inteligencia_artificial.domain.entities.interaccion_ia import (
    InteraccionIa,
)
from app.modules.inteligencia_artificial.infrastructure.api.schemas.interaccion_ia_schemas import (
    EnviarMensajeIaRequest,
    InteraccionIaRead,
    ListaInteraccionesIaRead,
)
from app.modules.inteligencia_artificial.infrastructure.api.schemas.transcripcion_ia_schemas import (
    TranscripcionIaResponse,
)
from app.modules.inteligencia_artificial.infrastructure.external.proveedor_google_gemini import (
    ProveedorGoogleGemini,
)
from app.modules.inteligencia_artificial.infrastructure.external.proveedor_transcripcion_gemini import (
    ProveedorTranscripcionGemini,
)
from app.modules.inteligencia_artificial.infrastructure.persistence.repositories.sqlmodel_interaccion_ia_repository import (
    SQLModelInteraccionIaRepository,
)

router = APIRouter(prefix="/diagramas", tags=["Inteligencia Artificial"])

_proveedor_ia_singleton: ProveedorIa | None = None
_proveedor_transcripcion_singleton: ProveedorTranscripcion | None = None


def get_proveedor_ia() -> ProveedorIa:
    global _proveedor_ia_singleton
    if _proveedor_ia_singleton is None:
        _proveedor_ia_singleton = ProveedorGoogleGemini()
    return _proveedor_ia_singleton


def set_proveedor_ia_override(override: ProveedorIa | None) -> None:
    global _proveedor_ia_singleton
    _proveedor_ia_singleton = override


def get_proveedor_transcripcion() -> ProveedorTranscripcion:
    global _proveedor_transcripcion_singleton
    if _proveedor_transcripcion_singleton is None:
        _proveedor_transcripcion_singleton = ProveedorTranscripcionGemini(
            proveedor_ia=get_proveedor_ia()
        )
    return _proveedor_transcripcion_singleton


def set_proveedor_transcripcion_override(
    override: ProveedorTranscripcion | None,
) -> None:
    global _proveedor_transcripcion_singleton
    _proveedor_transcripcion_singleton = override


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
    limit: int = Query(default=5, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
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

    resultado = handler.execute(
        ListarInteraccionesIaQuery(
            usuario_id=usuario.user_id,
            diagrama_id=id_diagrama,
            limite=limit,
            offset=offset,
            antes_de_id=before,
        )
    )

    return ListaInteraccionesIaRead(
        items=[_a_read(i) for i in resultado.items],
        siguienteCursor=str(resultado.siguiente_cursor) if resultado.siguiente_cursor else None,
        total=resultado.total,
        hayMas=resultado.hay_mas,
        offset=resultado.offset,
        limit=resultado.limite,
    )


def _crear_procesar_mensaje_ia_use_case(
    session: DBSession,
    uow: UoWDep,
) -> ProcesarMensajeIaUseCase:
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

    from app.modules.diagramas.application.services.idempotencia_diagrama import (
        IdempotenciaDiagramaService,
    )
    from app.modules.diagramas.infrastructure.persistence.repositories.sqlmodel_operacion_diagrama_repository import (
        SQLModelOperacionDiagramaRepository,
    )
    from app.modules.diagramas.application.use_cases.clase.actualizar_clase import (
        ActualizarClaseUseCase,
    )
    from app.modules.diagramas.application.use_cases.clase.eliminar_clase import (
        EliminarClaseUseCase,
    )
    from app.modules.diagramas.application.use_cases.relacion.actualizar_relacion import (
        ActualizarRelacionUseCase,
    )
    from app.modules.diagramas.application.use_cases.relacion.eliminar_relacion import (
        EliminarRelacionUseCase,
    )
    from app.modules.diagramas.application.use_cases.estructura_relacion_nm.crear_estructura_relacion_nm import (
        CrearEstructuraRelacionNmUseCase,
    )
    from app.modules.diagramas.application.use_cases.estructura_relacion_nm.eliminar_estructura_relacion_nm import (
        EliminarEstructuraRelacionNmUseCase,
    )

    idempotencia = IdempotenciaDiagramaService(SQLModelOperacionDiagramaRepository(session))

    crear_estructura_nm_use_case = CrearEstructuraRelacionNmUseCase(
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

    actualizar_clase_use_case = ActualizarClaseUseCase(
        proyecto_repository=proyecto_repo,
        diagrama_repository=diagrama_repo,
        clase_repository=clase_repo,
        uow=uow,
        colaborador_repository=colaborador_repo,
    )

    eliminar_clase_use_case = EliminarClaseUseCase(
        proyecto_repository=proyecto_repo,
        diagrama_repository=diagrama_repo,
        clase_repository=clase_repo,
        atributo_repository=atributo_repo,
        uow=uow,
        colaborador_repository=colaborador_repo,
        relacion_repository=relacion_repo,
        referencia_fk_repository=referencia_fk_repo,
        estructura_repository=estructura_nm_repo,
    )

    actualizar_relacion_use_case = ActualizarRelacionUseCase(
        proyecto_repository=proyecto_repo,
        diagrama_repository=diagrama_repo,
        clase_repository=clase_repo,
        relacion_repository=relacion_repo,
        atributo_repository=atributo_repo,
        referencia_fk_repository=referencia_fk_repo,
        uow=uow,
        colaborador_repository=colaborador_repo,
    )

    eliminar_relacion_use_case = EliminarRelacionUseCase(
        proyecto_repository=proyecto_repo,
        diagrama_repository=diagrama_repo,
        relacion_repository=relacion_repo,
        referencia_fk_repository=referencia_fk_repo,
        uow=uow,
        colaborador_repository=colaborador_repo,
        atributo_repository=atributo_repo,
        clase_repository=clase_repo,
        estructura_repository=estructura_nm_repo,
    )

    eliminar_estructura_nm_use_case = EliminarEstructuraRelacionNmUseCase(
        proyecto_repository=proyecto_repo,
        diagrama_repository=diagrama_repo,
        estructura_repository=estructura_nm_repo,
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
        actualizar_clase_use_case=actualizar_clase_use_case,
        eliminar_clase_use_case=eliminar_clase_use_case,
        actualizar_relacion_use_case=actualizar_relacion_use_case,
        eliminar_relacion_use_case=eliminar_relacion_use_case,
        crear_estructura_nm_use_case=crear_estructura_nm_use_case,
        eliminar_estructura_nm_use_case=eliminar_estructura_nm_use_case,
        estructura_nm_repository=estructura_nm_repo,
    )

    return ProcesarMensajeIaUseCase(
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


def _crear_procesar_audio_ia_use_case(
    session: DBSession,
    uow: UoWDep,
) -> ProcesarAudioDiagramaIaUseCase:
    proyecto_repo = SQLModelProyectoRepository(session)
    diagrama_repo = SQLModelDiagramaRepository(session)
    interaccion_repo = SQLModelInteraccionIaRepository(session)
    clase_repo = SQLModelClaseRepository(session)
    atributo_repo = SQLModelAtributoRepository(session)
    relacion_repo = SQLModelRelacionRepository(session)
    referencia_fk_repo = SQLModelReferenciaFKRepository(session)
    estructura_nm_repo = SQLModelEstructuraRelacionNmRepository(session)
    colaborador_repo = SQLModelColaboradorProyectoRepository(session)

    query_diagrama = ObtenerDiagramaCompletoQueryHandler(
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
        query_diagrama=query_diagrama,
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

    from app.modules.diagramas.application.services.idempotencia_diagrama import (
        IdempotenciaDiagramaService,
    )
    from app.modules.diagramas.infrastructure.persistence.repositories.sqlmodel_operacion_diagrama_repository import (
        SQLModelOperacionDiagramaRepository,
    )
    from app.modules.diagramas.application.use_cases.clase.actualizar_clase import (
        ActualizarClaseUseCase,
    )
    from app.modules.diagramas.application.use_cases.clase.eliminar_clase import (
        EliminarClaseUseCase,
    )
    from app.modules.diagramas.application.use_cases.relacion.actualizar_relacion import (
        ActualizarRelacionUseCase,
    )
    from app.modules.diagramas.application.use_cases.relacion.eliminar_relacion import (
        EliminarRelacionUseCase,
    )
    from app.modules.diagramas.application.use_cases.estructura_relacion_nm.crear_estructura_relacion_nm import (
        CrearEstructuraRelacionNmUseCase,
    )
    from app.modules.diagramas.application.use_cases.estructura_relacion_nm.eliminar_estructura_relacion_nm import (
        EliminarEstructuraRelacionNmUseCase,
    )

    idempotencia = IdempotenciaDiagramaService(SQLModelOperacionDiagramaRepository(session))

    crear_estructura_nm_use_case = CrearEstructuraRelacionNmUseCase(
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

    actualizar_clase_use_case = ActualizarClaseUseCase(
        proyecto_repository=proyecto_repo,
        diagrama_repository=diagrama_repo,
        clase_repository=clase_repo,
        uow=uow,
        colaborador_repository=colaborador_repo,
    )

    eliminar_clase_use_case = EliminarClaseUseCase(
        proyecto_repository=proyecto_repo,
        diagrama_repository=diagrama_repo,
        clase_repository=clase_repo,
        atributo_repository=atributo_repo,
        uow=uow,
        colaborador_repository=colaborador_repo,
        relacion_repository=relacion_repo,
        referencia_fk_repository=referencia_fk_repo,
        estructura_repository=estructura_nm_repo,
    )

    actualizar_relacion_use_case = ActualizarRelacionUseCase(
        proyecto_repository=proyecto_repo,
        diagrama_repository=diagrama_repo,
        clase_repository=clase_repo,
        relacion_repository=relacion_repo,
        atributo_repository=atributo_repo,
        referencia_fk_repository=referencia_fk_repo,
        uow=uow,
        colaborador_repository=colaborador_repo,
    )

    eliminar_relacion_use_case = EliminarRelacionUseCase(
        proyecto_repository=proyecto_repo,
        diagrama_repository=diagrama_repo,
        relacion_repository=relacion_repo,
        referencia_fk_repository=referencia_fk_repo,
        uow=uow,
        colaborador_repository=colaborador_repo,
        atributo_repository=atributo_repo,
        clase_repository=clase_repo,
        estructura_repository=estructura_nm_repo,
    )

    eliminar_estructura_nm_use_case = EliminarEstructuraRelacionNmUseCase(
        proyecto_repository=proyecto_repo,
        diagrama_repository=diagrama_repo,
        estructura_repository=estructura_nm_repo,
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
        actualizar_clase_use_case=actualizar_clase_use_case,
        eliminar_clase_use_case=eliminar_clase_use_case,
        actualizar_relacion_use_case=actualizar_relacion_use_case,
        eliminar_relacion_use_case=eliminar_relacion_use_case,
        crear_estructura_nm_use_case=crear_estructura_nm_use_case,
        eliminar_estructura_nm_use_case=eliminar_estructura_nm_use_case,
        estructura_nm_repository=estructura_nm_repo,
    )

    return ProcesarAudioDiagramaIaUseCase(
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
    use_case = _crear_procesar_mensaje_ia_use_case(session, uow)

    interaccion = use_case.execute(
        ProcesarMensajeIaCommand(
            usuario_id=usuario.user_id,
            diagrama_id=id_diagrama,
            texto=payload.texto,
            clave_idempotencia=payload.clave_idempotencia,
            tipo_interaccion=payload.tipo_interaccion or "texto",
        )
    )

    return _a_read(interaccion)


@router.post(
    "/{id_diagrama}/interacciones-ia/audio",
    response_model=InteraccionIaRead,
    status_code=status.HTTP_201_CREATED,
)
async def enviar_audio_ia(
    id_diagrama: UUID,
    usuario: CurrentUser,
    session: DBSession,
    uow: UoWDep,
    audio: UploadFile = File(..., description="Archivo de audio temporal grabado por el usuario."),
    clave_idempotencia: UUID = Form(..., description="Clave única de idempotencia."),
    duracion_segundos: float | None = Form(default=None, alias="duracion_segundos"),
    idioma: str | None = Form(default=None),
) -> InteraccionIaRead:
    contenido_audio = await audio.read()
    if not contenido_audio:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo de audio proporcionado está vacío.",
        )

    mime_type = audio.content_type or "audio/webm"
    use_case = _crear_procesar_audio_ia_use_case(session, uow)

    interaccion = use_case.execute(
        ProcesarAudioDiagramaIaCommand(
            usuario_id=usuario.user_id,
            diagrama_id=id_diagrama,
            contenido_audio=contenido_audio,
            mime_type=mime_type,
            clave_idempotencia=clave_idempotencia,
            duracion_segundos=duracion_segundos,
            idioma=idioma,
        )
    )

    return _a_read(interaccion)


@router.post(
    "/{id_diagrama}/transcripciones-ia",
    response_model=TranscripcionIaResponse,
    status_code=status.HTTP_200_OK,
)
async def transcribir_audio_ia(
    id_diagrama: UUID,
    usuario: CurrentUser,
    session: DBSession,
    audio: UploadFile = File(..., description="Archivo de audio grabado por el usuario."),
    duracion_segundos: float | None = Form(default=None, alias="duracion_segundos"),
    idioma: str | None = Form(default=None),
) -> TranscripcionIaResponse:
    proyecto_repo = SQLModelProyectoRepository(session)
    diagrama_repo = SQLModelDiagramaRepository(session)
    colaborador_repo = SQLModelColaboradorProyectoRepository(session)
    proveedor = get_proveedor_transcripcion()

    use_case = TranscribirAudioIaUseCase(
        proyecto_repository=proyecto_repo,
        diagrama_repository=diagrama_repo,
        proveedor_transcripcion=proveedor,
        colaborador_repository=colaborador_repo,
    )

    contenido_audio = await audio.read()
    mime_type = audio.content_type or "audio/webm"

    resultado = use_case.execute(
        TranscribirAudioIaCommand(
            usuario_id=usuario.user_id,
            diagrama_id=id_diagrama,
            contenido_audio=contenido_audio,
            mime_type=mime_type,
            duracion_segundos=duracion_segundos,
            idioma=idioma,
        )
    )

    return TranscripcionIaResponse(
        texto=resultado.texto,
        idioma=resultado.idioma,
    )


def _crear_procesar_imagen_ia_use_case(
    session: DBSession,
    uow: UoWDep,
) -> ProcesarImagenDiagramaIaUseCase:
    proyecto_repo = SQLModelProyectoRepository(session)
    diagrama_repo = SQLModelDiagramaRepository(session)
    interaccion_repo = SQLModelInteraccionIaRepository(session)
    clase_repo = SQLModelClaseRepository(session)
    atributo_repo = SQLModelAtributoRepository(session)
    relacion_repo = SQLModelRelacionRepository(session)
    referencia_fk_repo = SQLModelReferenciaFKRepository(session)
    estructura_nm_repo = SQLModelEstructuraRelacionNmRepository(session)
    colaborador_repo = SQLModelColaboradorProyectoRepository(session)

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

    from app.modules.diagramas.application.services.idempotencia_diagrama import (
        IdempotenciaDiagramaService,
    )
    from app.modules.diagramas.infrastructure.persistence.repositories.sqlmodel_operacion_diagrama_repository import (
        SQLModelOperacionDiagramaRepository,
    )
    from app.modules.diagramas.application.use_cases.clase.actualizar_clase import (
        ActualizarClaseUseCase,
    )
    from app.modules.diagramas.application.use_cases.clase.eliminar_clase import (
        EliminarClaseUseCase,
    )
    from app.modules.diagramas.application.use_cases.relacion.actualizar_relacion import (
        ActualizarRelacionUseCase,
    )
    from app.modules.diagramas.application.use_cases.relacion.eliminar_relacion import (
        EliminarRelacionUseCase,
    )
    from app.modules.diagramas.application.use_cases.estructura_relacion_nm.crear_estructura_relacion_nm import (
        CrearEstructuraRelacionNmUseCase,
    )
    from app.modules.diagramas.application.use_cases.estructura_relacion_nm.eliminar_estructura_relacion_nm import (
        EliminarEstructuraRelacionNmUseCase,
    )

    idempotencia = IdempotenciaDiagramaService(SQLModelOperacionDiagramaRepository(session))

    crear_estructura_nm_use_case = CrearEstructuraRelacionNmUseCase(
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

    actualizar_clase_use_case = ActualizarClaseUseCase(
        proyecto_repository=proyecto_repo,
        diagrama_repository=diagrama_repo,
        clase_repository=clase_repo,
        uow=uow,
        colaborador_repository=colaborador_repo,
    )

    eliminar_clase_use_case = EliminarClaseUseCase(
        proyecto_repository=proyecto_repo,
        diagrama_repository=diagrama_repo,
        clase_repository=clase_repo,
        atributo_repository=atributo_repo,
        uow=uow,
        colaborador_repository=colaborador_repo,
        relacion_repository=relacion_repo,
        referencia_fk_repository=referencia_fk_repo,
        estructura_repository=estructura_nm_repo,
    )

    actualizar_relacion_use_case = ActualizarRelacionUseCase(
        proyecto_repository=proyecto_repo,
        diagrama_repository=diagrama_repo,
        clase_repository=clase_repo,
        relacion_repository=relacion_repo,
        atributo_repository=atributo_repo,
        referencia_fk_repository=referencia_fk_repo,
        uow=uow,
        colaborador_repository=colaborador_repo,
    )

    eliminar_relacion_use_case = EliminarRelacionUseCase(
        proyecto_repository=proyecto_repo,
        diagrama_repository=diagrama_repo,
        relacion_repository=relacion_repo,
        referencia_fk_repository=referencia_fk_repo,
        uow=uow,
        colaborador_repository=colaborador_repo,
        atributo_repository=atributo_repo,
        clase_repository=clase_repo,
        estructura_repository=estructura_nm_repo,
    )

    eliminar_estructura_nm_use_case = EliminarEstructuraRelacionNmUseCase(
        proyecto_repository=proyecto_repo,
        diagrama_repository=diagrama_repo,
        estructura_repository=estructura_nm_repo,
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
        actualizar_clase_use_case=actualizar_clase_use_case,
        eliminar_clase_use_case=eliminar_clase_use_case,
        actualizar_relacion_use_case=actualizar_relacion_use_case,
        eliminar_relacion_use_case=eliminar_relacion_use_case,
        crear_estructura_nm_use_case=crear_estructura_nm_use_case,
        eliminar_estructura_nm_use_case=eliminar_estructura_nm_use_case,
        estructura_nm_repository=estructura_nm_repo,
    )

    return ProcesarImagenDiagramaIaUseCase(
        proyecto_repository=proyecto_repo,
        diagrama_repository=diagrama_repo,
        interaccion_repository=interaccion_repo,
        clase_repository=clase_repo,
        atributo_repository=atributo_repo,
        relacion_repository=relacion_repo,
        coordinador_gemini=coordinador_gemini,
        ejecutor_plan=ejecutor_plan,
        uow=uow,
        colaborador_repository=colaborador_repo,
        estructura_nm_repository=estructura_nm_repo,
        referencia_fk_repository=referencia_fk_repo,
    )


@router.post(
    "/{id_diagrama}/interacciones-ia/imagen",
    response_model=InteraccionIaRead,
    status_code=status.HTTP_201_CREATED,
)
async def enviar_imagen_ia(
    id_diagrama: UUID,
    usuario: CurrentUser,
    session: DBSession,
    uow: UoWDep,
    imagen: UploadFile = File(..., description="Archivo de imagen UML temporal seleccionado por el usuario."),
    clave_idempotencia: UUID = Form(..., description="Clave única de idempotencia."),
) -> InteraccionIaRead:
    contenido_imagen = await imagen.read()
    if not contenido_imagen:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo de imagen proporcionado está vacío.",
        )

    mime_type = imagen.content_type or "image/png"
    nombre_archivo = imagen.filename or "diagrama.png"

    use_case = _crear_procesar_imagen_ia_use_case(session, uow)
    interaccion = use_case.execute(
        ProcesarImagenDiagramaIaCommand(
            usuario_id=usuario.user_id,
            diagrama_id=id_diagrama,
            contenido_imagen=contenido_imagen,
            mime_type=mime_type,
            nombre_archivo=nombre_archivo,
            clave_idempotencia=clave_idempotencia,
        )
    )

    return _a_read(interaccion)

