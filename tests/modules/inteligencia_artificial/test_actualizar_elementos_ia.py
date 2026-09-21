from uuid import uuid4
import pytest
from sqlmodel import Session

from app.core.dependencies import get_event_bus
from app.modules.diagramas.application.queries.diagrama.obtener_diagrama import (
    ObtenerDiagramaCompletoQueryHandler,
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
from app.modules.diagramas.application.use_cases.relacion.actualizar_relacion import (
    ActualizarRelacionUseCase,
)
from app.modules.diagramas.application.use_cases.relacion.crear_relacion import (
    CrearRelacionUseCase,
)
from app.modules.diagramas.infrastructure.persistence.models.clase_model import ClaseModel
from app.modules.diagramas.infrastructure.persistence.models.diagrama_model import DiagramaModel
from app.modules.diagramas.infrastructure.persistence.models.relacion_model import RelacionModel
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
from app.modules.inteligencia_artificial.application.use_cases.procesar_mensaje_ia import (
    ProcesarMensajeIaCommand,
    ProcesarMensajeIaUseCase,
)
from app.modules.inteligencia_artificial.infrastructure.persistence.repositories.sqlmodel_interaccion_ia_repository import (
    SQLModelInteraccionIaRepository,
)
from app.shared.infrastructure.db.better_auth import BetterAuthUser
from app.shared.infrastructure.unit_of_work import SqlModelUnitOfWork


class FakeActualizarProveedor(ProveedorIa):
    def __init__(self, respuesta_json: str):
        self.respuesta_json = respuesta_json

    def generar_respuesta(
        self,
        *,
        modelo: str,
        prompt_sistema: str,
        mensaje_usuario: str,
        temperatura: float = 0.2,
    ) -> ResultadoProveedorIa:
        return ResultadoProveedorIa(texto_respuesta=self.respuesta_json, modelo=modelo)


def _crear_contexto_actualizacion(session: Session, respuesta_json: str):
    usuario = BetterAuthUser(id="usuario-editor-1", name="Editor", email="editor@drawi.com", email_verified=True)
    session.add(usuario)
    session.commit()

    proyecto = ProyectoModel(propietario_id=usuario.id, nombre="Proy Act", color="azul", icono="caja", slug="proy-act")
    session.add(proyecto)
    session.commit()

    diagrama = DiagramaModel(id_proyecto=proyecto.id, nombre="Pagina 1", numero=1)
    session.add(diagrama)
    session.commit()

    uow = SqlModelUnitOfWork(session, get_event_bus())
    p_repo = SQLModelProyectoRepository(session)
    d_repo = SQLModelDiagramaRepository(session)
    c_repo = SQLModelClaseRepository(session)
    a_repo = SQLModelAtributoRepository(session)
    r_repo = SQLModelRelacionRepository(session)
    rfk_repo = SQLModelReferenciaFKRepository(session)
    nm_repo = SQLModelEstructuraRelacionNmRepository(session)
    col_repo = SQLModelColaboradorProyectoRepository(session)
    i_repo = SQLModelInteraccionIaRepository(session)

    q_diag = ObtenerDiagramaCompletoQueryHandler(p_repo, d_repo, c_repo, a_repo, col_repo, r_repo, rfk_repo, nm_repo)
    constructor = ConstructorContextoDiagrama(q_diag, i_repo)
    coordinador = EstrategiaModelosGemini(FakeActualizarProveedor(respuesta_json))

    cc_uc = CrearClaseUseCase(p_repo, d_repo, c_repo, a_repo, uow, col_repo)
    act_c_uc = ActualizarClaseUseCase(p_repo, d_repo, c_repo, uow, col_repo)
    at_uc = AtributoUseCase(p_repo, d_repo, c_repo, a_repo, uow, col_repo, rfk_repo, r_repo, nm_repo)
    cr_uc = CrearRelacionUseCase(p_repo, d_repo, c_repo, r_repo, uow, col_repo, a_repo, rfk_repo)
    act_r_uc = ActualizarRelacionUseCase(p_repo, d_repo, c_repo, r_repo, a_repo, rfk_repo, uow, col_repo)

    ejecutor = EjecutorPlanIa(
        crear_clase_use_case=cc_uc,
        atributo_use_case=at_uc,
        crear_relacion_use_case=cr_uc,
        clase_repository=c_repo,
        atributo_repository=a_repo,
        relacion_repository=r_repo,
        referencia_fk_repository=rfk_repo,
        actualizar_clase_use_case=act_c_uc,
        actualizar_relacion_use_case=act_r_uc,
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

    return use_case, usuario, diagrama, c_repo, a_repo, r_repo, p_repo, d_repo, uow


def test_actualizar_clase_renombra_correctamente(session: Session):
    respuesta_json = """{
      "respuesta_usuario": "He renombrado la clase Cliente a ClienteVip.",
      "acciones": [
        {
          "tipo": "actualizar_clase",
          "clase_referencia": "Cliente",
          "nuevo_nombre": "ClienteVip"
        }
      ]
    }"""
    use_case, usuario, diagrama, c_repo, a_repo, _, _, _, uow = _crear_contexto_actualizacion(session, respuesta_json)

    # Crear clase inicial con CrearClaseUseCase
    cc_uc = CrearClaseUseCase(SQLModelProyectoRepository(session), SQLModelDiagramaRepository(session), c_repo, a_repo, uow)
    from app.modules.diagramas.application.use_cases.clase.crear_clase import CrearClaseCommand
    clase_creada, _ = cc_uc.execute(CrearClaseCommand(propietario_id=usuario.id, diagrama_id=diagrama.id, nombre="Cliente", posicion_x=100, posicion_y=100, ancho=280))

    interaccion = use_case.execute(
        ProcesarMensajeIaCommand(
            usuario_id=usuario.id,
            diagrama_id=diagrama.id,
            texto="Renombra la clase Cliente a ClienteVip",
            clave_idempotencia=uuid4(),
        )
    )

    assert interaccion.estado.value == "completado" or str(interaccion.estado) == "completado"
    clase_actualizada = c_repo.obtener_por_id(clase_creada.id)
    assert clase_actualizada is not None
    assert clase_actualizada.nombre == "ClienteVip"


def test_actualizar_atributo_renombra_campo(session: Session):
    respuesta_json = """{
      "respuesta_usuario": "He renombrado el campo telefono a celular en la clase Cliente.",
      "acciones": [
        {
          "tipo": "actualizar_atributo",
          "clase_referencia": "Cliente",
          "atributo_referencia": "telefono",
          "nuevo_nombre": "celular"
        }
      ]
    }"""
    use_case, usuario, diagrama, c_repo, a_repo, _, p_repo, d_repo, uow = _crear_contexto_actualizacion(session, respuesta_json)

    cc_uc = CrearClaseUseCase(p_repo, d_repo, c_repo, a_repo, uow)
    from app.modules.diagramas.application.use_cases.clase.crear_clase import CrearClaseCommand
    clase_creada, _ = cc_uc.execute(CrearClaseCommand(propietario_id=usuario.id, diagrama_id=diagrama.id, nombre="Cliente", posicion_x=100, posicion_y=100, ancho=280))

    at_uc = AtributoUseCase(p_repo, d_repo, c_repo, a_repo, uow)
    from app.modules.diagramas.application.use_cases.atributo.atributo_use_cases import AtributoCommand
    at_uc.crear(AtributoCommand(propietario_id=usuario.id, clase_id=clase_creada.id, datos={"nombre": "telefono", "tipo_dato": "varchar", "longitud": 20}))

    interaccion = use_case.execute(
        ProcesarMensajeIaCommand(
            usuario_id=usuario.id,
            diagrama_id=diagrama.id,
            texto="Renombra el campo telefono de Cliente a celular",
            clave_idempotencia=uuid4(),
        )
    )

    assert interaccion.estado.value == "completado" or str(interaccion.estado) == "completado"
    attrs = a_repo.listar_por_clase(clase_creada.id)
    nombres = [a.nombre for a in attrs]
    assert "celular" in nombres
    assert "telefono" not in nombres


def test_actualizar_relacion_renombra_correctamente(session: Session):
    respuesta_json = """{
      "respuesta_usuario": "He renombrado la relación a compras_cliente.",
      "acciones": [
        {
          "tipo": "actualizar_relacion",
          "clase_origen_referencia": "Cliente",
          "clase_destino_referencia": "Pedido",
          "nuevo_nombre": "compras_cliente"
        }
      ]
    }"""
    use_case, usuario, diagrama, c_repo, a_repo, r_repo, p_repo, d_repo, uow = _crear_contexto_actualizacion(session, respuesta_json)

    cc_uc = CrearClaseUseCase(p_repo, d_repo, c_repo, a_repo, uow)
    from app.modules.diagramas.application.use_cases.clase.crear_clase import CrearClaseCommand
    c1, _ = cc_uc.execute(CrearClaseCommand(propietario_id=usuario.id, diagrama_id=diagrama.id, nombre="Cliente", posicion_x=100, posicion_y=100, ancho=280))
    c2, _ = cc_uc.execute(CrearClaseCommand(propietario_id=usuario.id, diagrama_id=diagrama.id, nombre="Pedido", posicion_x=400, posicion_y=100, ancho=280))

    rel_model = RelacionModel(
        id_diagrama=diagrama.id,
        id_clase_origen=c1.id,
        id_clase_destino=c2.id,
        tipo_relacion="asociacion",
        cardinalidad_origen="1",
        cardinalidad_destino="1..*",
        conector_origen="right",
        conector_destino="left",
        nombre="antiguo_nombre",
    )
    session.add(rel_model)
    session.commit()

    interaccion = use_case.execute(
        ProcesarMensajeIaCommand(
            usuario_id=usuario.id,
            diagrama_id=diagrama.id,
            texto="Renombra la relación entre Cliente y Pedido a compras_cliente",
            clave_idempotencia=uuid4(),
        )
    )

    assert interaccion.estado.value == "completado" or str(interaccion.estado) == "completado"
    rel_actualizada = r_repo.obtener_por_id(rel_model.id)
    assert rel_actualizada is not None
    assert rel_actualizada.nombre == "compras_cliente"
