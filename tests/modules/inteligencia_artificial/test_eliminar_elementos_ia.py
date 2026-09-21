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
from app.modules.diagramas.application.use_cases.clase.eliminar_clase import (
    EliminarClaseUseCase,
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


class FakeEliminarProveedor(ProveedorIa):
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


def _crear_contexto_eliminacion(session: Session, respuesta_json: str):
    usuario = BetterAuthUser(id="usuario-editor-del", name="EditorDel", email="editordel@drawi.com", email_verified=True)
    session.add(usuario)
    session.commit()

    proyecto = ProyectoModel(propietario_id=usuario.id, nombre="Proy Del", color="azul", icono="caja", slug="proy-del")
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
    coordinador = EstrategiaModelosGemini(FakeEliminarProveedor(respuesta_json))

    cc_uc = CrearClaseUseCase(p_repo, d_repo, c_repo, a_repo, uow, col_repo)
    act_c_uc = ActualizarClaseUseCase(p_repo, d_repo, c_repo, uow, col_repo)
    elim_c_uc = EliminarClaseUseCase(p_repo, d_repo, c_repo, a_repo, uow, col_repo, r_repo, rfk_repo, nm_repo)
    at_uc = AtributoUseCase(p_repo, d_repo, c_repo, a_repo, uow, col_repo, rfk_repo, r_repo, nm_repo)
    cr_uc = CrearRelacionUseCase(p_repo, d_repo, c_repo, r_repo, uow, col_repo, a_repo, rfk_repo)
    act_r_uc = ActualizarRelacionUseCase(p_repo, d_repo, c_repo, r_repo, a_repo, rfk_repo, uow, col_repo)
    elim_r_uc = EliminarRelacionUseCase(p_repo, d_repo, r_repo, rfk_repo, uow, col_repo, a_repo, c_repo, nm_repo)
    elim_nm_uc = EliminarEstructuraRelacionNmUseCase(p_repo, d_repo, nm_repo, c_repo, a_repo, r_repo, rfk_repo, uow, col_repo)

    ejecutor = EjecutorPlanIa(
        crear_clase_use_case=cc_uc,
        atributo_use_case=at_uc,
        crear_relacion_use_case=cr_uc,
        clase_repository=c_repo,
        atributo_repository=a_repo,
        relacion_repository=r_repo,
        referencia_fk_repository=rfk_repo,
        actualizar_clase_use_case=act_c_uc,
        eliminar_clase_use_case=elim_c_uc,
        actualizar_relacion_use_case=act_r_uc,
        eliminar_relacion_use_case=elim_r_uc,
        eliminar_estructura_nm_use_case=elim_nm_uc,
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

    return use_case, usuario, diagrama, c_repo, a_repo, r_repo, p_repo, d_repo, uow


def test_eliminar_clase_elimina_correctamente_en_cascada(session: Session):
    respuesta_json = """{
      "respuesta_usuario": "He eliminado la clase Auditoria.",
      "acciones": [
        {
          "tipo": "eliminar_clase",
          "clase_referencia": "Auditoria"
        }
      ]
    }"""
    use_case, usuario, diagrama, c_repo, a_repo, _, p_repo, d_repo, uow = _crear_contexto_eliminacion(session, respuesta_json)

    cc_uc = CrearClaseUseCase(p_repo, d_repo, c_repo, a_repo, uow)
    from app.modules.diagramas.application.use_cases.clase.crear_clase import CrearClaseCommand
    clase_creada, _ = cc_uc.execute(CrearClaseCommand(propietario_id=usuario.id, diagrama_id=diagrama.id, nombre="Auditoria", posicion_x=100, posicion_y=100, ancho=280))

    interaccion = use_case.execute(
        ProcesarMensajeIaCommand(
            usuario_id=usuario.id,
            diagrama_id=diagrama.id,
            texto="Elimina la tabla Auditoria",
            clave_idempotencia=uuid4(),
        )
    )

    assert interaccion.estado.value == "completado" or str(interaccion.estado) == "completado"
    clase_consultada = c_repo.obtener_por_id(clase_creada.id)
    assert clase_consultada is None


def test_eliminar_atributo_manual_exitoso(session: Session):
    respuesta_json = """{
      "respuesta_usuario": "He eliminado el campo telefono de Cliente.",
      "acciones": [
        {
          "tipo": "eliminar_atributo",
          "clase_referencia": "Cliente",
          "atributo_referencia": "telefono"
        }
      ]
    }"""
    use_case, usuario, diagrama, c_repo, a_repo, _, p_repo, d_repo, uow = _crear_contexto_eliminacion(session, respuesta_json)

    cc_uc = CrearClaseUseCase(p_repo, d_repo, c_repo, a_repo, uow)
    from app.modules.diagramas.application.use_cases.clase.crear_clase import CrearClaseCommand
    clase_creada, _ = cc_uc.execute(CrearClaseCommand(propietario_id=usuario.id, diagrama_id=diagrama.id, nombre="Cliente", posicion_x=100, posicion_y=100, ancho=280))

    at_uc = AtributoUseCase(p_repo, d_repo, c_repo, a_repo, uow)
    from app.modules.diagramas.application.use_cases.atributo.atributo_use_cases import AtributoCommand
    nuevo_attr = at_uc.crear(AtributoCommand(propietario_id=usuario.id, clase_id=clase_creada.id, datos={"nombre": "telefono", "tipo_dato": "varchar", "longitud": 20}))

    interaccion = use_case.execute(
        ProcesarMensajeIaCommand(
            usuario_id=usuario.id,
            diagrama_id=diagrama.id,
            texto="Elimina el campo telefono de Cliente",
            clave_idempotencia=uuid4(),
        )
    )

    assert interaccion.estado.value == "completado" or str(interaccion.estado) == "completado"
    attr_consultado = a_repo.obtener_por_id(nuevo_attr.id)
    assert attr_consultado is None


def test_eliminar_atributo_pk_sistema_es_rechazado_por_dominio(session: Session):
    respuesta_json = """{
      "respuesta_usuario": "He eliminado la clave primaria (PK) 'id' de la clase 'Cliente'.",
      "acciones": [
        {
          "tipo": "eliminar_atributo",
          "clase_referencia": "Cliente",
          "atributo_referencia": "id"
        }
      ]
    }"""
    use_case, usuario, diagrama, c_repo, a_repo, _, p_repo, d_repo, uow = _crear_contexto_eliminacion(session, respuesta_json)

    cc_uc = CrearClaseUseCase(p_repo, d_repo, c_repo, a_repo, uow)
    from app.modules.diagramas.application.use_cases.clase.crear_clase import CrearClaseCommand
    clase_creada, _ = cc_uc.execute(CrearClaseCommand(propietario_id=usuario.id, diagrama_id=diagrama.id, nombre="Cliente", posicion_x=100, posicion_y=100, ancho=280))

    # El atributo 'id' creado automáticamente por CrearClase tiene procedencia SISTEMA_CLASE y es PK
    interaccion = use_case.execute(
        ProcesarMensajeIaCommand(
            usuario_id=usuario.id,
            diagrama_id=diagrama.id,
            texto="Elimina la PK de Cliente",
            clave_idempotencia=uuid4(),
        )
    )

    # El paso es rechazado por protección del dominio y se conserva el estado en detalle_ejecucion
    assert interaccion.detalle_ejecucion is not None
    assert len(interaccion.detalle_ejecucion) == 1
    assert interaccion.detalle_ejecucion[0]["estado"] == "rechazado"
    assert "No se puede eliminar la llave primaria" in interaccion.detalle_ejecucion[0]["motivo"]

    # La respuesta final visible a DRAWI NO puede afirmar falso éxito
    assert "He eliminado" not in interaccion.respuesta_ia
    assert "No se pudo realizar la operación" in interaccion.respuesta_ia
    assert "No se puede eliminar la llave primaria" in interaccion.respuesta_ia

    # El atributo id sigue existiendo en BD
    attrs = a_repo.listar_por_clase(clase_creada.id)
    assert any(a.nombre == "id" for a in attrs)


def test_eliminar_relacion_exitoso(session: Session):
    respuesta_json = """{
      "respuesta_usuario": "He eliminado la relación entre Cliente y Pedido.",
      "acciones": [
        {
          "tipo": "eliminar_relacion",
          "clase_origen_referencia": "Cliente",
          "clase_destino_referencia": "Pedido"
        }
      ]
    }"""
    use_case, usuario, diagrama, c_repo, a_repo, r_repo, p_repo, d_repo, uow = _crear_contexto_eliminacion(session, respuesta_json)

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
    )
    session.add(rel_model)
    session.commit()

    interaccion = use_case.execute(
        ProcesarMensajeIaCommand(
            usuario_id=usuario.id,
            diagrama_id=diagrama.id,
            texto="Elimina la relación entre Cliente y Pedido",
            clave_idempotencia=uuid4(),
        )
    )

    assert interaccion.estado.value == "completado" or str(interaccion.estado) == "completado"
    assert r_repo.obtener_por_id(rel_model.id) is None


def test_operaciones_mixtas_reportan_exito_parcial_y_rechazo(session: Session):
    respuesta_json = """{
      "respuesta_usuario": "Creando campo edad, eliminando id y renombrando clase.",
      "acciones": [
        {
          "tipo": "crear_atributo",
          "clase_referencia": "Usuario",
          "nombre": "edad",
          "tipo_dato": "integer"
        },
        {
          "tipo": "eliminar_atributo",
          "clase_referencia": "Usuario",
          "atributo_referencia": "id"
        },
        {
          "tipo": "actualizar_clase",
          "clase_referencia": "Usuario",
          "nuevo_nombre": "UsuarioRenombrado"
        }
      ]
    }"""
    use_case, usuario, diagrama, c_repo, a_repo, _, p_repo, d_repo, uow = _crear_contexto_eliminacion(session, respuesta_json)

    cc_uc = CrearClaseUseCase(p_repo, d_repo, c_repo, a_repo, uow)
    from app.modules.diagramas.application.use_cases.clase.crear_clase import CrearClaseCommand
    clase_creada, _ = cc_uc.execute(CrearClaseCommand(propietario_id=usuario.id, diagrama_id=diagrama.id, nombre="Usuario", posicion_x=100, posicion_y=100, ancho=280))

    interaccion = use_case.execute(
        ProcesarMensajeIaCommand(
            usuario_id=usuario.id,
            diagrama_id=diagrama.id,
            texto="Agrega edad, elimina id y renombra clase",
            clave_idempotencia=uuid4(),
        )
    )

    assert interaccion.detalle_ejecucion is not None
    assert len(interaccion.detalle_ejecucion) == 3
    assert interaccion.detalle_ejecucion[0]["estado"] == "completado"
    assert interaccion.detalle_ejecucion[1]["estado"] == "rechazado"
    assert interaccion.detalle_ejecucion[2]["estado"] == "omitido"

    # Verificar que respuesta_ia contiene el reporte de éxito parcial y motivo de rechazo
    assert "Se completó exitosamente" in interaccion.respuesta_ia
    assert "No se pudo ejecutar eliminar_atributo" in interaccion.respuesta_ia
    assert "No se puede eliminar la llave primaria" in interaccion.respuesta_ia
    assert "Se omitieron 1 acción(es) posterior(es)" in interaccion.respuesta_ia

    # Verificar BD: edad existe, id existe (no se eliminó), clase NO se renombró (se omitió)
    attrs = a_repo.listar_por_clase(clase_creada.id)
    nombres = {a.nombre for a in attrs}
    assert "edad" in nombres
    assert "id" in nombres

    clase_db = c_repo.obtener_por_id(clase_creada.id)
    assert clase_db.nombre == "Usuario"


def test_referencia_inexistente_es_rechazada_claramente(session: Session):
    respuesta_json = """{
      "respuesta_usuario": "Eliminando clase Inexistente.",
      "acciones": [
        {
          "tipo": "eliminar_clase",
          "clase_referencia": "Inexistente"
        }
      ]
    }"""
    use_case, usuario, diagrama, c_repo, a_repo, _, p_repo, d_repo, uow = _crear_contexto_eliminacion(session, respuesta_json)

    interaccion = use_case.execute(
        ProcesarMensajeIaCommand(
            usuario_id=usuario.id,
            diagrama_id=diagrama.id,
            texto="Elimina la clase Inexistente",
            clave_idempotencia=uuid4(),
        )
    )

    assert interaccion.detalle_ejecucion is not None
    assert len(interaccion.detalle_ejecucion) == 1
    assert interaccion.detalle_ejecucion[0]["estado"] == "rechazado"
    assert "Inexistente" in interaccion.detalle_ejecucion[0]["motivo"]
    assert "No se pudo realizar la operación" in interaccion.respuesta_ia
    assert "Inexistente" in interaccion.respuesta_ia

