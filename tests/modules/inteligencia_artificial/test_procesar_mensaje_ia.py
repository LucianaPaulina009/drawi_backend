import logging
from uuid import uuid4
import pytest
from sqlmodel import Session

from app.core.dependencies import get_event_bus
from app.shared.infrastructure.unit_of_work import SqlModelUnitOfWork
from app.modules.diagramas.application.queries.diagrama.obtener_diagrama import ObtenerDiagramaCompletoQueryHandler
from app.modules.diagramas.application.use_cases.atributo.atributo_use_cases import AtributoUseCase
from app.modules.diagramas.application.use_cases.clase.crear_clase import CrearClaseUseCase
from app.modules.diagramas.application.use_cases.relacion.crear_relacion import CrearRelacionUseCase
from app.modules.diagramas.infrastructure.persistence.models.diagrama_model import DiagramaModel
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
from app.modules.gestion_proyectos.infrastructure.persistence.models.proyecto_model import ProyectoModel
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
from app.modules.inteligencia_artificial.application.services.ejecutor_plan_ia import EjecutorPlanIa
from app.modules.inteligencia_artificial.application.services.estrategia_modelos_gemini import (
    EstrategiaModelosGemini,
    reset_circuit_breakers,
)
from app.modules.inteligencia_artificial.application.use_cases.procesar_mensaje_ia import (
    ProcesarMensajeIaCommand,
    ProcesarMensajeIaUseCase,
)
from app.modules.inteligencia_artificial.domain.exceptions import (
    ClaveIdempotenciaConflictoException,
    EntradaUsuarioInvalidaException,
    ProveedorIaRecuperableException,
)
from app.modules.inteligencia_artificial.domain.value_objects.estado_interaccion_ia import EstadoInteraccionIa
from app.modules.inteligencia_artificial.infrastructure.persistence.repositories.sqlmodel_interaccion_ia_repository import (
    SQLModelInteraccionIaRepository,
)
from app.shared.infrastructure.db.better_auth import BetterAuthUser


class FakeProveedor(ProveedorIa):
    def __init__(
        self,
        respuesta_json: str = '{"respuesta_usuario": "Hola!", "acciones": []}',
        respuestas_por_modelo: dict[str, ResultadoProveedorIa | Exception] | None = None,
    ) -> None:
        self.respuesta_json = respuesta_json
        self.respuestas_por_modelo = respuestas_por_modelo or {}
        self.invocaciones = 0
        self.modelos_invocados: list[str] = []

    def generar_respuesta(self, *, modelo: str, prompt_sistema: str, mensaje_usuario: str, temperatura: float = 0.2) -> ResultadoProveedorIa:
        self.invocaciones += 1
        self.modelos_invocados.append(modelo)
        if modelo in self.respuestas_por_modelo:
            resp = self.respuestas_por_modelo[modelo]
            if isinstance(resp, Exception):
                raise resp
            return resp
        return ResultadoProveedorIa(texto_respuesta=self.respuesta_json, modelo=modelo)


@pytest.fixture(autouse=True)
def limpiar_breakers():
    reset_circuit_breakers()
    yield
    reset_circuit_breakers()


def _crear_entorno(
    session: Session,
    respuesta_json: str | None = None,
    respuestas_por_modelo: dict[str, ResultadoProveedorIa | Exception] | None = None,
):
    uid = f"user-proc-{uuid4().hex[:6]}"
    usuario = BetterAuthUser(id=uid, name="Proc", email=f"{uid}@drawi.com", email_verified=True)
    session.add(usuario)
    session.commit()

    proyecto = ProyectoModel(propietario_id=usuario.id, nombre="Proy Proc", color="azul", icono="caja", slug=f"proy-proc-{uuid4().hex[:6]}")
    session.add(proyecto)
    session.commit()

    diagrama = DiagramaModel(id_proyecto=proyecto.id, nombre="Página 1", numero=1)
    session.add(diagrama)
    session.commit()

    p_repo = SQLModelProyectoRepository(session)
    d_repo = SQLModelDiagramaRepository(session)
    i_repo = SQLModelInteraccionIaRepository(session)
    c_repo = SQLModelClaseRepository(session)
    a_repo = SQLModelAtributoRepository(session)
    r_repo = SQLModelRelacionRepository(session)
    rfk_repo = SQLModelReferenciaFKRepository(session)
    nm_repo = SQLModelEstructuraRelacionNmRepository(session)
    col_repo = SQLModelColaboradorProyectoRepository(session)
    uow = SqlModelUnitOfWork(session, get_event_bus())

    q_diag = ObtenerDiagramaCompletoQueryHandler(p_repo, d_repo, c_repo, a_repo, col_repo, r_repo, rfk_repo, nm_repo)
    constructor = ConstructorContextoDiagrama(q_diag, i_repo)

    fake_prov = FakeProveedor(
        respuesta_json=respuesta_json or '{"respuesta_usuario": "Respuesta simulada", "acciones": []}',
        respuestas_por_modelo=respuestas_por_modelo,
    )
    coordinador = EstrategiaModelosGemini(fake_prov, retry_backoff_ms=0)

    from app.modules.diagramas.application.services.idempotencia_diagrama import IdempotenciaDiagramaService
    from app.modules.diagramas.application.use_cases.estructura_relacion_nm.crear_estructura_relacion_nm import (
        CrearEstructuraRelacionNmUseCase,
    )
    from app.modules.diagramas.infrastructure.persistence.repositories.sqlmodel_operacion_diagrama_repository import (
        SQLModelOperacionDiagramaRepository,
    )

    op_repo = SQLModelOperacionDiagramaRepository(session)
    idempotencia = IdempotenciaDiagramaService(op_repo)

    cc_uc = CrearClaseUseCase(
        proyecto_repository=p_repo,
        diagrama_repository=d_repo,
        clase_repository=c_repo,
        atributo_repository=a_repo,
        uow=uow,
        colaborador_repository=col_repo,
    )
    at_uc = AtributoUseCase(
        p=p_repo,
        d=d_repo,
        c=c_repo,
        a=a_repo,
        u=uow,
        col=col_repo,
        rfk=rfk_repo,
        relacion_repository=r_repo,
        estructura_repository=nm_repo,
    )
    cr_uc = CrearRelacionUseCase(
        proyecto_repository=p_repo,
        diagrama_repository=d_repo,
        clase_repository=c_repo,
        relacion_repository=r_repo,
        uow=uow,
        colaborador_repository=col_repo,
        atributo_repository=a_repo,
        referencia_fk_repository=rfk_repo,
    )
    cnm_uc = CrearEstructuraRelacionNmUseCase(
        proyecto_repository=p_repo,
        diagrama_repository=d_repo,
        clase_repository=c_repo,
        atributo_repository=a_repo,
        relacion_repository=r_repo,
        referencia_fk_repository=rfk_repo,
        estructura_repository=nm_repo,
        idempotencia=idempotencia,
        uow=uow,
        colaborador_repository=col_repo,
    )

    ejecutor = EjecutorPlanIa(
        crear_clase_use_case=cc_uc,
        atributo_use_case=at_uc,
        crear_relacion_use_case=cr_uc,
        clase_repository=c_repo,
        atributo_repository=a_repo,
        relacion_repository=r_repo,
        referencia_fk_repository=rfk_repo,
        crear_estructura_nm_use_case=cnm_uc,
        estructura_nm_repository=nm_repo,
    )

    use_case = ProcesarMensajeIaUseCase(
        proyecto_repository=p_repo,
        diagrama_repository=d_repo,
        interaccion_repository=i_repo,
        clase_repository=c_repo,
        constructor_contexto=constructor,
        coordinador_gemini=coordinador,
        ejecutor_plan=ejecutor,
        uow=uow,
        colaborador_repository=col_repo,
    )

    return use_case, usuario, diagrama, fake_prov, c_repo, a_repo, r_repo, nm_repo, i_repo


def test_procesar_mensaje_conversacion_exitoso_y_persistido(session: Session):
    use_case, usuario, diagrama, fake_prov, *_ = _crear_entorno(session)

    clave = uuid4()
    interaccion = use_case.execute(
        ProcesarMensajeIaCommand(
            usuario_id=usuario.id,
            diagrama_id=diagrama.id,
            texto="¿Cómo diseño una relación 1 a N?",
            clave_idempotencia=clave,
        )
    )

    assert interaccion.estado == EstadoInteraccionIa.COMPLETADO
    assert interaccion.respuesta_ia == "Respuesta simulada"
    assert interaccion.modelo_utilizado == "gemini-3.6-flash"
    assert fake_prov.invocaciones == 1


# Caso 14: Voz (022) y texto comparten el mismo pipeline, breaker y fallback
def test_caso_14_voz_y_texto_comparten_pipeline_y_estrategia(session: Session):
    use_case, usuario, diagrama, fake_prov, *_ = _crear_entorno(session)

    # Interacción de texto
    clave_texto = uuid4()
    interaccion_texto = use_case.execute(
        ProcesarMensajeIaCommand(
            usuario_id=usuario.id,
            diagrama_id=diagrama.id,
            texto="Hola DRAWI desde texto",
            clave_idempotencia=clave_texto,
            tipo_interaccion="texto",
        )
    )
    assert interaccion_texto.tipo_interaccion.value == "texto" or str(interaccion_texto.tipo_interaccion) == "texto"
    assert interaccion_texto.modelo_utilizado == "gemini-3.6-flash"

    # Interacción de voz (procedente de audio transcrito)
    clave_voz = uuid4()
    interaccion_voz = use_case.execute(
        ProcesarMensajeIaCommand(
            usuario_id=usuario.id,
            diagrama_id=diagrama.id,
            texto="Crea la tabla Factura desde voz",
            clave_idempotencia=clave_voz,
            tipo_interaccion="audio",
        )
    )
    assert interaccion_voz.tipo_interaccion.value == "audio" or str(interaccion_voz.tipo_interaccion) == "audio"
    assert interaccion_voz.modelo_utilizado == "gemini-3.6-flash"
    assert fake_prov.invocaciones == 2


# Caso 15: Telemetría y logs estructurados registran métricas completas
def test_caso_15_metricas_estructuradas_y_telemetria(session: Session, caplog: pytest.LogCaptureFixture):
    use_case, usuario, diagrama, _, *_ = _crear_entorno(session)

    with caplog.at_level(logging.INFO):
        use_case.execute(
            ProcesarMensajeIaCommand(
                usuario_id=usuario.id,
                diagrama_id=diagrama.id,
                texto="Crea una clase Proveedor",
                clave_idempotencia=uuid4(),
            )
        )

    # Verificar log estructurado
    registros = [r.message for r in caplog.records if "[DRAWI IA]" in r.message]
    assert len(registros) >= 1
    log_linea = registros[0]
    assert "contextLevel=" in log_linea
    assert "contextMs=" in log_linea
    assert "model=gemini-3.6-flash" in log_linea
    assert "attempts=1" in log_linea
    assert "fallback=False" in log_linea
    assert "breakerOpen=False" in log_linea
    assert "geminiMs=" in log_linea
    assert "totalMs=" in log_linea


# Caso 16: Idempotencia respetada en reintentos, fallback y errores
def test_caso_16_idempotencia_preservada(session: Session):
    use_case, usuario, diagrama, fake_prov, *_ = _crear_entorno(session)

    clave = uuid4()
    cmd = ProcesarMensajeIaCommand(
        usuario_id=usuario.id,
        diagrama_id=diagrama.id,
        texto="¿Cómo funciona la clave primaria?",
        clave_idempotencia=clave,
    )

    primera = use_case.execute(cmd)
    assert fake_prov.invocaciones == 1

    # Segunda invocación con la misma clave e idéntico texto
    segunda = use_case.execute(cmd)
    assert segunda.id == primera.id
    # No volvió a llamar al proveedor de IA
    assert fake_prov.invocaciones == 1

    # Invocación con la misma clave pero texto modificado -> conflicto 409
    with pytest.raises(ClaveIdempotenciaConflictoException):
        use_case.execute(
            ProcesarMensajeIaCommand(
                usuario_id=usuario.id,
                diagrama_id=diagrama.id,
                texto="Texto completamente distinto con misma clave",
                clave_idempotencia=clave,
            )
        )


def test_procesar_mensaje_texto_vacio_falla_validacion(session: Session):
    use_case, usuario, diagrama, _, *_ = _crear_entorno(session)

    with pytest.raises(EntradaUsuarioInvalidaException):
        use_case.execute(
            ProcesarMensajeIaCommand(
                usuario_id=usuario.id,
                diagrama_id=diagrama.id,
                texto="   ",
                clave_idempotencia=uuid4(),
            )
        )


def test_procesar_mensaje_fallo_ambos_modelos_deja_error_sin_mutaciones(session: Session):
    respuestas_fallidas = {
        "gemini-3.6-flash": ProveedorIaRecuperableException("Timeout 504"),
        "gemini-3.5-flash-lite": ProveedorIaRecuperableException("503 Overloaded"),
    }
    use_case, usuario, diagrama, _, c_repo, _, _, _, i_repo = _crear_entorno(
        session, respuestas_por_modelo=respuestas_fallidas
    )

    clave = uuid4()
    with pytest.raises(ProveedorIaRecuperableException):
        use_case.execute(
            ProcesarMensajeIaCommand(
                usuario_id=usuario.id,
                diagrama_id=diagrama.id,
                texto="Crea una clase NoDeberiaCrearse",
                clave_idempotencia=clave,
            )
        )

    # Verificar 0 mutaciones en base de datos
    clases = c_repo.listar_por_diagrama(diagrama.id)
    assert len(clases) == 0

    # Verificar interacción registrada con mensaje amigable
    interaccion = i_repo.obtener_por_idempotencia(usuario.id, diagrama.id, clave)
    assert interaccion is not None
    assert interaccion.estado == EstadoInteraccionIa.ERROR
    assert "DRAWI no pudo procesar la solicitud en este momento" in interaccion.respuesta_ia


def test_procesar_mensaje_ia_crea_relacion_nm_con_atributo_en_intermedia(session: Session):
    from app.modules.diagramas.infrastructure.persistence.models.clase_model import ClaseModel
    from app.modules.diagramas.infrastructure.persistence.models.atributo_model import AtributoModel
    from app.modules.diagramas.domain.value_objects.procedencia_atributo import ProcedenciaAtributo

    respuesta_gemini = """{
      "respuesta_usuario": "He creado la relación de muchos a muchos entre Cliente y Vehiculo, generando la tabla intermedia Cliente_Vehiculo y agregando el atributo prueba.",
      "acciones": [
        {
          "tipo": "crear_estructura_nm",
          "referencia_intermedia": "cliente_vehiculo",
          "clase_origen_referencia": "Cliente",
          "clase_destino_referencia": "Vehiculo",
          "nombre_intermedia": "Cliente_Vehiculo"
        },
        {
          "tipo": "crear_atributo",
          "clase_referencia": "cliente_vehiculo",
          "nombre": "prueba",
          "tipo_dato": "text"
        }
      ]
    }"""

    use_case, usuario, diagrama, _, c_repo, a_repo, r_repo, nm_repo, _ = _crear_entorno(
        session, respuesta_json=respuesta_gemini
    )

    # Crear previamente clases Cliente y Vehiculo
    c1 = ClaseModel(id_diagrama=diagrama.id, nombre="Cliente", posicion_x=100.0, posicion_y=100.0, ancho=280.0)
    c2 = ClaseModel(id_diagrama=diagrama.id, nombre="Vehiculo", posicion_x=500.0, posicion_y=100.0, ancho=280.0)
    session.add(c1)
    session.add(c2)
    session.commit()

    a1 = AtributoModel(id_clase=c1.id, nombre="id", tipo_dato="integer", orden_de_posicion=1, es_llave_primaria=True, permite_nulo=False, es_unico=True, procedencia=ProcedenciaAtributo.SISTEMA_CLASE.value)
    a2 = AtributoModel(id_clase=c2.id, nombre="id", tipo_dato="integer", orden_de_posicion=1, es_llave_primaria=True, permite_nulo=False, es_unico=True, procedencia=ProcedenciaAtributo.SISTEMA_CLASE.value)
    session.add(a1)
    session.add(a2)
    session.commit()

    # Usuario pide la creación N:M con atributo en la intermedia
    interaccion = use_case.execute(
        ProcesarMensajeIaCommand(
            usuario_id=usuario.id,
            diagrama_id=diagrama.id,
            texto="Crea una relacion de la tabla Cliente con Vehiculo, una relacion de muchos a muchos, en la tabla de muchos a muchos crea un atributo llamado prueba de tipo texto.",
            clave_idempotencia=uuid4(),
        )
    )

    assert interaccion.estado == EstadoInteraccionIa.COMPLETADO
    assert "Cliente_Vehiculo" in interaccion.respuesta_ia

    # Verificar entidades en base de datos
    clases = c_repo.listar_por_diagrama(diagrama.id)
    assert len(clases) == 3
    intermedia = next((c for c in clases if c.nombre == "Cliente_Vehiculo"), None)
    assert intermedia is not None

    attrs = a_repo.listar_por_clase(intermedia.id)
    nombres_attrs = {a.nombre for a in attrs}
    assert "id" in nombres_attrs
    assert "prueba" in nombres_attrs
    attr_prueba = next(a for a in attrs if a.nombre == "prueba")
    assert attr_prueba.tipo_dato == "text"

    estructuras = nm_repo.listar_por_diagrama(diagrama.id)
    assert len(estructuras) == 1
    assert estructuras[0].id_clase_intermedia == intermedia.id

    relaciones = r_repo.listar_por_diagrama(diagrama.id)
    assert len(relaciones) == 2
