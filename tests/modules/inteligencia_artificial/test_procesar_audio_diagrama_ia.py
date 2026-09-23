from __future__ import annotations

import json
from uuid import uuid4
import pytest
from fastapi import HTTPException
from sqlmodel import Session, select

from app.modules.diagramas.application.queries.diagrama.obtener_diagrama import (
    ObtenerDiagramaCompletoQueryHandler,
)
from app.modules.diagramas.application.services.idempotencia_diagrama import (
    IdempotenciaDiagramaService,
)
from app.modules.diagramas.application.use_cases.atributo.atributo_use_cases import (
    AtributoUseCase,
)
from app.modules.diagramas.application.use_cases.clase.actualizar_clase import (
    ActualizarClaseUseCase,
)
from app.modules.diagramas.application.use_cases.clase.crear_clase import (
    CrearClaseUseCase,
)
from app.modules.diagramas.application.use_cases.clase.eliminar_clase import (
    EliminarClaseUseCase,
)
from app.modules.diagramas.application.use_cases.estructura_relacion_nm.crear_estructura_relacion_nm import (
    CrearEstructuraRelacionNmUseCase,
)
from app.modules.diagramas.application.use_cases.estructura_relacion_nm.eliminar_estructura_relacion_nm import (
    EliminarEstructuraRelacionNmUseCase,
)
from app.modules.diagramas.application.use_cases.relacion.actualizar_relacion import (
    ActualizarRelacionUseCase,
)
from app.modules.diagramas.application.use_cases.relacion.crear_relacion import (
    CrearRelacionUseCase,
)
from app.modules.diagramas.application.use_cases.relacion.eliminar_relacion import (
    EliminarRelacionUseCase,
)
from app.modules.diagramas.infrastructure.persistence.models.clase_model import (
    ClaseModel,
)
from app.modules.diagramas.infrastructure.persistence.models.diagrama_model import (
    DiagramaModel,
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
from app.modules.gestion_proyectos.infrastructure.persistence.models.proyecto_model import (
    ProyectoModel,
)
from app.modules.gestion_proyectos.infrastructure.persistence.repositories.sqlmodel_proyecto_repository import (
    SQLModelProyectoRepository,
)
from app.modules.inteligencia_artificial.application.ports.providers.proveedor_ia import (
    ProveedorIa,
    ResultadoProveedorIa,
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
from app.modules.inteligencia_artificial.domain.exceptions import (
    AudioVacioException,
    FormatoAudioNoSoportadoException,
)
from app.modules.inteligencia_artificial.infrastructure.persistence.repositories.sqlmodel_interaccion_ia_repository import (
    SQLModelInteraccionIaRepository,
)
from app.shared.infrastructure.db.better_auth import BetterAuthUser
from app.core.dependencies import get_event_bus
from app.shared.infrastructure.unit_of_work import SqlModelUnitOfWork


class FakeAudioProvider(ProveedorIa):
    def __init__(self, json_response: str) -> None:
        self.json_response = json_response
        self.audio_calls = 0

    def generar_respuesta(
        self,
        *,
        modelo: str,
        prompt_sistema: str,
        mensaje_usuario: str,
        temperatura: float = 0.2,
    ) -> ResultadoProveedorIa:
        return ResultadoProveedorIa(texto_respuesta="", modelo=modelo)

    def generar_respuesta_audio(
        self,
        *,
        modelo: str,
        prompt_sistema: str,
        contenido_audio: bytes,
        mime_type: str,
        temperatura: float = 0.2,
    ) -> ResultadoProveedorIa:
        self.audio_calls += 1
        return ResultadoProveedorIa(
            texto_respuesta=self.json_response,
            modelo=modelo,
        )


def _crear_caso_uso_audio(session: Session, proveedor: ProveedorIa) -> ProcesarAudioDiagramaIaUseCase:
    proyecto_repo = SQLModelProyectoRepository(session)
    diagrama_repo = SQLModelDiagramaRepository(session)
    interaccion_repo = SQLModelInteraccionIaRepository(session)
    clase_repo = SQLModelClaseRepository(session)
    atributo_repo = SQLModelAtributoRepository(session)
    relacion_repo = SQLModelRelacionRepository(session)
    referencia_fk_repo = SQLModelReferenciaFKRepository(session)
    estructura_nm_repo = SQLModelEstructuraRelacionNmRepository(session)
    colaborador_repo = SQLModelColaboradorProyectoRepository(session)
    uow = SqlModelUnitOfWork(session, get_event_bus())

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


def test_procesar_audio_exitoso_con_transcripcion_y_creacion_clase(session: Session):
    usuario = BetterAuthUser(id="user-audio-1", name="Audio Tester", email="audio1@drawi.com", email_verified=True)
    session.add(usuario)
    session.commit()

    proyecto = ProyectoModel(propietario_id=usuario.id, nombre="Proy Audio UC", color="verde", icono="caja", slug="proy-audio-uc")
    session.add(proyecto)
    session.commit()

    diagrama = DiagramaModel(id_proyecto=proyecto.id, nombre="Diagrama Audio", numero=1)
    session.add(diagrama)
    session.commit()

    # Clase existente para validar no colisión de layout
    c_existente = ClaseModel(id_diagrama=diagrama.id, nombre="Usuario", posicion_x=100.0, posicion_y=100.0, ancho=280.0)
    session.add(c_existente)
    session.commit()

    fake_response = json.dumps({
        "transcripcion_usuario": "Crea una clase Producto con precio y stock",
        "respuesta_usuario": "He creado la clase Producto con los atributos solicitados.",
        "acciones": [
            {
                "tipo": "crear_clase",
                "referencia": "producto",
                "nombre": "Producto",
            },
            {
                "tipo": "crear_atributo",
                "clase_referencia": "producto",
                "nombre": "precio",
                "tipo_dato": "decimal",
            },
            {
                "tipo": "crear_atributo",
                "clase_referencia": "producto",
                "nombre": "stock",
                "tipo_dato": "integer",
            },
        ],
    })

    fake_provider = FakeAudioProvider(fake_response)
    use_case = _crear_caso_uso_audio(session, fake_provider)

    cmd = ProcesarAudioDiagramaIaCommand(
        usuario_id=usuario.id,
        diagrama_id=diagrama.id,
        contenido_audio=b"fake-audio-bytes-data",
        mime_type="audio/webm",
        clave_idempotencia=uuid4(),
        duracion_segundos=4.0,
    )

    interaccion = use_case.execute(cmd)

    # 1 sola llamada a Gemini multimodal
    assert fake_provider.audio_calls == 1

    # Verificar datos de interacción
    assert interaccion.tipo_interaccion.value == "audio"
    assert interaccion.entrada_usuario == "Crea una clase Producto con precio y stock"
    assert interaccion.respuesta_ia == "He creado la clase Producto con los atributos solicitados."
    assert interaccion.estado.value == "completado"

    # Verificar que la clase fue creada en el diagrama sin solapar a la existente
    clases = session.exec(select(ClaseModel).where(ClaseModel.id_diagrama == diagrama.id)).all()
    assert len(clases) == 2
    clase_nueva = next(c for c in clases if c.nombre == "Producto")
    assert clase_nueva is not None
    # No debe solapar la posición de la clase existente (100, 100)
    assert not (clase_nueva.posicion_x == 100.0 and clase_nueva.posicion_y == 100.0)


def test_procesar_audio_rechaza_vacio_y_formato_no_soportado(session: Session):
    usuario = BetterAuthUser(id="user-audio-2", name="Audio Tester 2", email="audio2@drawi.com", email_verified=True)
    session.add(usuario)
    session.commit()

    proyecto = ProyectoModel(propietario_id=usuario.id, nombre="Proy Audio 2", color="azul", icono="caja", slug="proy-audio-2")
    session.add(proyecto)
    session.commit()

    diagrama = DiagramaModel(id_proyecto=proyecto.id, nombre="Diagrama Audio 2", numero=1)
    session.add(diagrama)
    session.commit()

    fake_provider = FakeAudioProvider("{}")
    use_case = _crear_caso_uso_audio(session, fake_provider)

    # 1. Audio vacío
    with pytest.raises(AudioVacioException):
        use_case.execute(
            ProcesarAudioDiagramaIaCommand(
                usuario_id=usuario.id,
                diagrama_id=diagrama.id,
                contenido_audio=b"",
                mime_type="audio/webm",
                clave_idempotencia=uuid4(),
            )
        )

    # 2. Formato no soportado
    with pytest.raises(FormatoAudioNoSoportadoException):
        use_case.execute(
            ProcesarAudioDiagramaIaCommand(
                usuario_id=usuario.id,
                diagrama_id=diagrama.id,
                contenido_audio=b"dummy-audio",
                mime_type="video/mp4",
                clave_idempotencia=uuid4(),
            )
        )


def test_procesar_audio_silencio_sin_transcripcion_falla(session: Session):
    usuario = BetterAuthUser(id="user-audio-3", name="Audio Tester 3", email="audio3@drawi.com", email_verified=True)
    session.add(usuario)
    session.commit()

    proyecto = ProyectoModel(propietario_id=usuario.id, nombre="Proy Audio 3", color="azul", icono="caja", slug="proy-audio-3")
    session.add(proyecto)
    session.commit()

    diagrama = DiagramaModel(id_proyecto=proyecto.id, nombre="Diagrama Audio 3", numero=1)
    session.add(diagrama)
    session.commit()

    # Gemini devuelve transcripción vacía
    fake_response = json.dumps({
        "transcripcion_usuario": "",
        "respuesta_usuario": "No se detectó audio comprensible.",
        "acciones": [],
    })
    fake_provider = FakeAudioProvider(fake_response)
    use_case = _crear_caso_uso_audio(session, fake_provider)

    with pytest.raises(HTTPException) as exc_info:
        use_case.execute(
            ProcesarAudioDiagramaIaCommand(
                usuario_id=usuario.id,
                diagrama_id=diagrama.id,
                contenido_audio=b"silence-bytes-12345",
                mime_type="audio/webm",
                clave_idempotencia=uuid4(),
            )
        )
    assert exc_info.value.status_code == 422
    assert "No se detectó contenido comprensible" in exc_info.value.detail
