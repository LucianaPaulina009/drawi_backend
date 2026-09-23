from __future__ import annotations

import json
from uuid import uuid4
import pytest
from sqlmodel import Session

from app.core.dependencies import get_event_bus

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
from app.modules.inteligencia_artificial.application.services.ejecutor_plan_ia import (
    EjecutorPlanIa,
)
from app.modules.inteligencia_artificial.application.services.estrategia_modelos_gemini import (
    EstrategiaModelosGemini,
    reset_circuit_breakers,
)
from app.modules.inteligencia_artificial.application.use_cases.procesar_imagen_diagrama_ia import (
    ProcesarImagenDiagramaIaCommand,
    ProcesarImagenDiagramaIaUseCase,
)
from app.modules.inteligencia_artificial.domain.exceptions import (
    ClaveIdempotenciaConflictoException,
    FormatoImagenNoSoportadoException,
    ImagenVaciaException,
    ProveedorIaRecuperableException,
)
from app.modules.inteligencia_artificial.domain.value_objects.estado_interaccion_ia import (
    EstadoInteraccionIa,
)
from app.modules.inteligencia_artificial.infrastructure.persistence.repositories.sqlmodel_interaccion_ia_repository import (
    SQLModelInteraccionIaRepository,
)
from app.shared.infrastructure.db.better_auth import BetterAuthUser
from app.shared.infrastructure.unit_of_work import SqlModelUnitOfWork
from tests.modules.inteligencia_artificial.fixtures.imagen_ia_fixtures import (
    FakeProveedorIaImagen,
    PNG_VALIDO_BYTES,
)


@pytest.fixture(autouse=True)
def limpiar_breakers():
    reset_circuit_breakers()
    yield
    reset_circuit_breakers()


def _crear_entorno_imagen(session: Session, respuesta_json_imagen: str = "{}"):
    uid = f"user-img-{uuid4().hex[:6]}"
    usuario = BetterAuthUser(id=uid, name="ImgUser", email=f"{uid}@drawi.com", email_verified=True)
    session.add(usuario)
    session.commit()

    proyecto = ProyectoModel(
        propietario_id=usuario.id,
        nombre="Proy Img",
        color="azul",
        icono="caja",
        slug=f"proy-img-{uuid4().hex[:6]}",
    )
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
    op_repo = SQLModelOperacionDiagramaRepository(session)

    uow = SqlModelUnitOfWork(session, event_bus=get_event_bus())
    idempotencia = IdempotenciaDiagramaService(op_repo)

    crear_clase_uc = CrearClaseUseCase(p_repo, d_repo, c_repo, a_repo, uow, col_repo)
    atributo_uc = AtributoUseCase(
        p=p_repo, d=d_repo, c=c_repo, a=a_repo, u=uow, col=col_repo,
        rfk=rfk_repo, relacion_repository=r_repo, estructura_repository=nm_repo
    )
    crear_relacion_uc = CrearRelacionUseCase(
        proyecto_repository=p_repo,
        diagrama_repository=d_repo,
        clase_repository=c_repo,
        relacion_repository=r_repo,
        uow=uow,
        colaborador_repository=col_repo,
        atributo_repository=a_repo,
        referencia_fk_repository=rfk_repo,
    )
    act_clase_uc = ActualizarClaseUseCase(p_repo, d_repo, c_repo, uow, col_repo)
    elim_clase_uc = EliminarClaseUseCase(p_repo, d_repo, c_repo, a_repo, uow, col_repo, r_repo, rfk_repo, nm_repo)
    act_rel_uc = ActualizarRelacionUseCase(p_repo, d_repo, c_repo, r_repo, a_repo, rfk_repo, uow, col_repo)
    elim_rel_uc = EliminarRelacionUseCase(p_repo, d_repo, r_repo, rfk_repo, uow, col_repo, a_repo, c_repo, nm_repo)
    crear_nm_uc = CrearEstructuraRelacionNmUseCase(p_repo, d_repo, c_repo, a_repo, r_repo, rfk_repo, nm_repo, idempotencia, uow, col_repo)
    elim_nm_uc = EliminarEstructuraRelacionNmUseCase(p_repo, d_repo, nm_repo, c_repo, a_repo, r_repo, rfk_repo, uow, col_repo)

    ejecutor = EjecutorPlanIa(
        crear_clase_use_case=crear_clase_uc,
        atributo_use_case=atributo_uc,
        crear_relacion_use_case=crear_relacion_uc,
        clase_repository=c_repo,
        atributo_repository=a_repo,
        relacion_repository=r_repo,
        referencia_fk_repository=rfk_repo,
        actualizar_clase_use_case=act_clase_uc,
        eliminar_clase_use_case=elim_clase_uc,
        actualizar_relacion_use_case=act_rel_uc,
        eliminar_relacion_use_case=elim_rel_uc,
        crear_estructura_nm_use_case=crear_nm_uc,
        eliminar_estructura_nm_use_case=elim_nm_uc,
        estructura_nm_repository=nm_repo,
    )

    fake_proveedor = FakeProveedorIaImagen(respuesta_json_imagen=respuesta_json_imagen)
    coordinador = EstrategiaModelosGemini(fake_proveedor)

    use_case = ProcesarImagenDiagramaIaUseCase(
        proyecto_repository=p_repo,
        diagrama_repository=d_repo,
        interaccion_repository=i_repo,
        clase_repository=c_repo,
        atributo_repository=a_repo,
        relacion_repository=r_repo,
        coordinador_gemini=coordinador,
        ejecutor_plan=ejecutor,
        uow=uow,
        colaborador_repository=col_repo,
    )

    return {
        "usuario": usuario,
        "proyecto": proyecto,
        "diagrama": diagrama,
        "use_case": use_case,
        "fake_proveedor": fake_proveedor,
        "clase_repo": c_repo,
        "atributo_repo": a_repo,
        "relacion_repo": r_repo,
        "referencia_fk_repo": rfk_repo,
        "estructura_nm_repo": nm_repo,
        "interaccion_repo": i_repo,
    }


def test_importar_imagen_diagrama_vacio_exito(session: Session):
    json_respuesta = json.dumps({
        "clases": [
            {
                "referencia_semantica": "ref_cliente",
                "nombre": "Cliente",
                "atributos": [
                    {"nombre": "id", "tipo_detectado": "integer", "es_pk": True, "permite_nulo": False},
                    {"nombre": "email", "tipo_detectado": "varchar", "es_pk": False, "permite_nulo": False},
                ],
                "posicion_relativa_x": 0.2,
                "posicion_relativa_y": 0.3,
            },
            {
                "referencia_semantica": "ref_pedido",
                "nombre": "Pedido",
                "atributos": [
                    {"nombre": "id", "tipo_detectado": "integer", "es_pk": True, "permite_nulo": False},
                    {"nombre": "total", "tipo_detectado": "decimal", "es_pk": False, "permite_nulo": True},
                ],
                "posicion_relativa_x": 0.7,
                "posicion_relativa_y": 0.3,
            },
        ],
        "relaciones": [
            {
                "origen_ref": "ref_cliente",
                "destino_ref": "ref_pedido",
                "tipo": "asociacion",
                "cardinalidad_origen": "1",
                "cardinalidad_destino": "0..*",
                "nombre": "realiza",
            }
        ],
        "advertencias": [],
    })

    env = _crear_entorno_imagen(session, respuesta_json_imagen=json_respuesta)
    cmd = ProcesarImagenDiagramaIaCommand(
        usuario_id=env["usuario"].id,
        diagrama_id=env["diagrama"].id,
        contenido_imagen=PNG_VALIDO_BYTES,
        mime_type="image/png",
        nombre_archivo="diagrama_uml.png",
        clave_idempotencia=uuid4(),
    )

    interaccion = env["use_case"].execute(cmd)

    assert interaccion.estado == EstadoInteraccionIa.COMPLETADO
    assert interaccion.tipo_interaccion == "imagen"
    assert "Cliente" in interaccion.respuesta_ia
    assert "Pedido" in interaccion.respuesta_ia

    # Verificar que el proveedor Gemini recibió directamente los bytes en memoria
    assert len(env["fake_proveedor"].llamadas_imagen) == 1
    assert env["fake_proveedor"].llamadas_imagen[0]["contenido_imagen_len"] == len(PNG_VALIDO_BYTES)
    assert env["fake_proveedor"].llamadas_imagen[0]["mime_type"] == "image/png"

    # Verificar elementos creados en BD
    clases = env["clase_repo"].listar_por_diagrama(env["diagrama"].id)
    assert len(clases) == 2
    nombres = {c.nombre for c in clases}
    assert nombres == {"Cliente", "Pedido"}

    relaciones = env["relacion_repo"].listar_por_diagrama(env["diagrama"].id)
    assert len(relaciones) == 1
    assert relaciones[0].nombre == "realiza"


def test_importar_imagen_relacion_recursiva_y_nm(session: Session):
    json_respuesta = json.dumps({
        "clases": [
            {
                "referencia_semantica": "ref_emp",
                "nombre": "Empleado",
                "atributos": [
                    {"nombre": "id", "tipo_detectado": "integer", "es_pk": True},
                    {"nombre": "nombre", "tipo_detectado": "varchar", "es_pk": False},
                ],
            },
            {
                "referencia_semantica": "ref_proj",
                "nombre": "Proyecto",
                "atributos": [
                    {"nombre": "id", "tipo_detectado": "integer", "es_pk": True},
                    {"nombre": "codigo", "tipo_detectado": "varchar", "es_pk": False},
                ],
            },
        ],
        "relaciones": [
            {
                "origen_ref": "ref_emp",
                "destino_ref": "ref_emp",
                "tipo": "asociacion",
                "cardinalidad_origen": "1",
                "cardinalidad_destino": "0..*",
                "nombre": "supervisa",
                "es_recursiva": True,
            },
            {
                "origen_ref": "ref_emp",
                "destino_ref": "ref_proj",
                "tipo": "asociacion",
                "cardinalidad_origen": "0..*",
                "cardinalidad_destino": "0..*",
                "nombre": "asignacion",
                "es_nm": True,
            },
        ],
        "advertencias": [],
    })

    env = _crear_entorno_imagen(session, respuesta_json_imagen=json_respuesta)
    cmd = ProcesarImagenDiagramaIaCommand(
        usuario_id=env["usuario"].id,
        diagrama_id=env["diagrama"].id,
        contenido_imagen=PNG_VALIDO_BYTES,
        mime_type="image/png",
        nombre_archivo="uml_nm.png",
        clave_idempotencia=uuid4(),
    )

    interaccion = env["use_case"].execute(cmd)

    assert interaccion.estado == EstadoInteraccionIa.COMPLETADO
    assert "asignacion" in interaccion.respuesta_ia

    # Verificar relación recursiva
    relaciones = env["relacion_repo"].listar_por_diagrama(env["diagrama"].id)
    # Puede haber la recursiva más las 2 relaciones generadas por la estructura N:M
    rel_recursiva = next((r for r in relaciones if r.nombre == "supervisa"), None)
    assert rel_recursiva is not None
    assert rel_recursiva.id_clase_origen == rel_recursiva.id_clase_destino

    # Verificar estructura N:M creada por CrearEstructuraRelacionNmUseCase
    estructuras_nm = env["estructura_nm_repo"].listar_por_diagrama(env["diagrama"].id)
    assert len(estructuras_nm) == 1


def test_idempotencia_misma_clave_mismo_resultado(session: Session):
    json_respuesta = json.dumps({
        "clases": [
            {
                "referencia_semantica": "ref_c",
                "nombre": "Categoria",
                "atributos": [{"nombre": "id", "es_pk": True}],
            }
        ],
        "relaciones": [],
        "advertencias": [],
    })

    env = _crear_entorno_imagen(session, respuesta_json_imagen=json_respuesta)
    clave = uuid4()
    cmd1 = ProcesarImagenDiagramaIaCommand(
        usuario_id=env["usuario"].id,
        diagrama_id=env["diagrama"].id,
        contenido_imagen=PNG_VALIDO_BYTES,
        mime_type="image/png",
        nombre_archivo="cat.png",
        clave_idempotencia=clave,
    )

    res1 = env["use_case"].execute(cmd1)
    assert res1.estado == EstadoInteraccionIa.COMPLETADO

    # Segunda invocación con la misma clave e imagen
    res2 = env["use_case"].execute(cmd1)
    assert res2.id == res1.id

    # No debe haberse creado una segunda clase Categoria
    clases = env["clase_repo"].listar_por_diagrama(env["diagrama"].id)
    assert len(clases) == 1


def test_idempotencia_conflicto_tipo_distinto(session: Session):
    env = _crear_entorno_imagen(session)
    clave = uuid4()

    # Inserción previa de interacción tipo 'texto' con la misma clave
    from app.modules.inteligencia_artificial.domain.entities.interaccion_ia import InteraccionIa
    inter = InteraccionIa.crear(
        id_usuario=env["usuario"].id,
        id_diagrama=env["diagrama"].id,
        clave_idempotencia=clave,
        tipo_interaccion="texto",
        entrada_usuario="crear tabla usuario",
    )
    env["interaccion_repo"].guardar(inter)
    env["use_case"].uow.commit()

    cmd = ProcesarImagenDiagramaIaCommand(
        usuario_id=env["usuario"].id,
        diagrama_id=env["diagrama"].id,
        contenido_imagen=PNG_VALIDO_BYTES,
        mime_type="image/png",
        nombre_archivo="diag.png",
        clave_idempotencia=clave,
    )

    with pytest.raises(ClaveIdempotenciaConflictoException):
        env["use_case"].execute(cmd)


def test_error_gemini_registra_interaccion_error(session: Session):
    env = _crear_entorno_imagen(session)
    env["fake_proveedor"].debe_fallar_imagen = True

    cmd = ProcesarImagenDiagramaIaCommand(
        usuario_id=env["usuario"].id,
        diagrama_id=env["diagrama"].id,
        contenido_imagen=PNG_VALIDO_BYTES,
        mime_type="image/png",
        nombre_archivo="error.png",
        clave_idempotencia=uuid4(),
    )

    with pytest.raises(ProveedorIaRecuperableException):
        env["use_case"].execute(cmd)

    # Interacción registrada en ERROR
    interacciones = env["interaccion_repo"].listar_por_diagrama(env["diagrama"].id)
    assert len(interacciones) == 1
    assert interacciones[0].estado == EstadoInteraccionIa.ERROR


def test_archivo_vacio_rechazado(session: Session):
    env = _crear_entorno_imagen(session)
    cmd = ProcesarImagenDiagramaIaCommand(
        usuario_id=env["usuario"].id,
        diagrama_id=env["diagrama"].id,
        contenido_imagen=b"",
        mime_type="image/png",
        nombre_archivo="vacio.png",
        clave_idempotencia=uuid4(),
    )

    with pytest.raises(ImagenVaciaException):
        env["use_case"].execute(cmd)


def test_procesar_imagen_fk_explicita_reconciliada_una_sola_fk_estructural(session: Session):
    json_respuesta = json.dumps({
        "clases": [
            {
                "referencia_semantica": "ref_cli",
                "nombre": "Cliente",
                "atributos": [
                    {"nombre": "id", "tipo_detectado": "integer", "es_pk": True},
                ],
            },
            {
                "referencia_semantica": "ref_ped",
                "nombre": "Pedido",
                "atributos": [
                    {"nombre": "id", "tipo_detectado": "integer", "es_pk": True},
                    {
                        "nombre": "cliente_id",
                        "tipo_detectado": "integer",
                        "es_pk": False,
                        "es_fk": True,
                        "fk_destino_ref": "ref_cli",
                    },
                ],
            },
        ],
        "relaciones": [
            {
                "origen_ref": "ref_cli",
                "destino_ref": "ref_ped",
                "tipo": "asociacion",
                "cardinalidad_origen": "1",
                "cardinalidad_destino": "0..*",
                "nombre": "realiza",
            }
        ],
        "advertencias": [],
    })

    env = _crear_entorno_imagen(session, respuesta_json_imagen=json_respuesta)

    cmd = ProcesarImagenDiagramaIaCommand(
        usuario_id=env["usuario"].id,
        diagrama_id=env["diagrama"].id,
        contenido_imagen=PNG_VALIDO_BYTES,
        mime_type="image/png",
        nombre_archivo="uml_cliente_pedido.png",
        clave_idempotencia=uuid4(),
    )

    interaccion = env["use_case"].execute(cmd)
    assert interaccion.estado == EstadoInteraccionIa.COMPLETADO

    # Verificar entidades reales en base de datos
    clases = env["clase_repo"].listar_por_diagrama(env["diagrama"].id)
    assert len(clases) == 2
    clase_cli = next(c for c in clases if c.nombre == "Cliente")
    clase_ped = next(c for c in clases if c.nombre == "Pedido")

    attrs_cli = env["atributo_repo"].listar_por_clase(clase_cli.id)
    attrs_ped = env["atributo_repo"].listar_por_clase(clase_ped.id)

    # Cliente solo tiene su PK id
    assert len(attrs_cli) == 1
    assert attrs_cli[0].nombre == "id"
    assert attrs_cli[0].es_llave_primaria is True

    # Pedido tiene exactamente 2 atributos: 'id' PK y 'cliente_id' SISTEMA_FK (cero duplicados)
    assert len(attrs_ped) == 2
    nombres_ped = {a.nombre: a for a in attrs_ped}
    assert "id" in nombres_ped
    assert "cliente_id" in nombres_ped
    assert nombres_ped["cliente_id"].procedencia == "sistema_fk"

    # Verificar relación creada
    relaciones = env["relacion_repo"].listar_por_diagrama(env["diagrama"].id)
    assert len(relaciones) == 1
    rel = relaciones[0]
    assert rel.id_clase_origen == clase_cli.id
    assert rel.id_clase_destino == clase_ped.id
    assert rel.cardinalidad_origen == "1"
    assert rel.cardinalidad_destino == "0..*"

    # Verificar ReferenciaFK en BD
    rfks = env["referencia_fk_repo"].listar_por_relacion(rel.id)
    assert len(rfks) == 1
    assert rfks[0].id_atributo_fk == nombres_ped["cliente_id"].id
    assert rfks[0].id_atributo_referenciado == attrs_cli[0].id


def test_procesar_imagen_recursiva_fk_explicita_una_sola_fk_estructural(session: Session):
    json_respuesta = json.dumps({
        "clases": [
            {
                "referencia_semantica": "ref_emp",
                "nombre": "Empleado",
                "atributos": [
                    {"nombre": "id", "tipo_detectado": "integer", "es_pk": True},
                    {
                        "nombre": "supervisor_id",
                        "tipo_detectado": "integer",
                        "es_pk": False,
                        "es_fk": True,
                        "fk_destino_ref": "ref_emp",
                    },
                ],
            },
        ],
        "relaciones": [
            {
                "origen_ref": "ref_emp",
                "destino_ref": "ref_emp",
                "tipo": "asociacion",
                "cardinalidad_origen": "1",
                "cardinalidad_destino": "0..*",
                "nombre": "supervisa",
                "es_recursiva": True,
            }
        ],
        "advertencias": [],
    })

    env = _crear_entorno_imagen(session, respuesta_json_imagen=json_respuesta)

    cmd = ProcesarImagenDiagramaIaCommand(
        usuario_id=env["usuario"].id,
        diagrama_id=env["diagrama"].id,
        contenido_imagen=PNG_VALIDO_BYTES,
        mime_type="image/png",
        nombre_archivo="uml_empleado_recursivo.png",
        clave_idempotencia=uuid4(),
    )

    interaccion = env["use_case"].execute(cmd)
    assert interaccion.estado == EstadoInteraccionIa.COMPLETADO

    # Verificar entidades en BD
    clases = env["clase_repo"].listar_por_diagrama(env["diagrama"].id)
    assert len(clases) == 1
    emp = clases[0]

    attrs_emp = env["atributo_repo"].listar_por_clase(emp.id)
    # Exactamente 2 atributos: id PK y supervisor_id sistema_fk (cero duplicados)
    assert len(attrs_emp) == 2
    nombres_emp = {a.nombre: a for a in attrs_emp}
    assert "id" in nombres_emp
    assert "supervisor_id" in nombres_emp
    assert nombres_emp["supervisor_id"].procedencia == "sistema_fk"

    # Verificar relación recursiva con ambas cardinalidades
    relaciones = env["relacion_repo"].listar_por_diagrama(env["diagrama"].id)
    assert len(relaciones) == 1
    rel = relaciones[0]
    assert rel.id_clase_origen == emp.id
    assert rel.id_clase_destino == emp.id
    assert rel.cardinalidad_origen == "1"
    assert rel.cardinalidad_destino == "0..*"
    assert rel.nombre == "supervisa"

    # Verificar ReferenciaFK recursiva
    rfks = env["referencia_fk_repo"].listar_por_relacion(rel.id)
    assert len(rfks) == 1
    assert rfks[0].id_atributo_fk == nombres_emp["supervisor_id"].id
    assert rfks[0].id_atributo_referenciado == nombres_emp["id"].id


def test_procesar_imagen_nm_intermedia_visible_e2e_sin_duplicados(session: Session):
    json_respuesta = json.dumps({
        "clases": [
            {
                "referencia_semantica": "ref_prod",
                "nombre": "Producto",
                "atributos": [
                    {"nombre": "id", "tipo_detectado": "integer", "es_pk": True},
                ],
                "posicion_relativa_x": 0.1,
                "posicion_relativa_y": 0.2,
            },
            {
                "referencia_semantica": "ref_venta",
                "nombre": "Venta",
                "atributos": [
                    {"nombre": "id", "tipo_detectado": "integer", "es_pk": True},
                ],
                "posicion_relativa_x": 0.9,
                "posicion_relativa_y": 0.2,
            },
            {
                "referencia_semantica": "ref_pv",
                "nombre": "ProductoVenta",
                "atributos": [
                    {"nombre": "id", "tipo_detectado": "integer", "es_pk": True},
                    {
                        "nombre": "id-producto",
                        "tipo_detectado": "integer",
                        "es_pk": False,
                        "es_fk": True,
                        "fk_destino_ref": "ref_prod",
                    },
                    {
                        "nombre": "id-venta",
                        "tipo_detectado": "integer",
                        "es_pk": False,
                        "es_fk": True,
                        "fk_destino_ref": "ref_venta",
                    },
                    {"nombre": "cantidad", "tipo_detectado": "integer", "es_pk": False, "es_fk": False},
                ],
                "posicion_relativa_x": 0.5,
                "posicion_relativa_y": 0.5,
            },
        ],
        "relaciones": [
            {
                "origen_ref": "ref_prod",
                "destino_ref": "ref_venta",
                "tipo": "asociacion",
                "cardinalidad_origen": "0..*",
                "cardinalidad_destino": "0..*",
                "nombre": "contiene",
                "es_nm": True,
            }
        ],
        "advertencias": [],
    })

    env = _crear_entorno_imagen(session, respuesta_json_imagen=json_respuesta)

    cmd = ProcesarImagenDiagramaIaCommand(
        usuario_id=env["usuario"].id,
        diagrama_id=env["diagrama"].id,
        contenido_imagen=PNG_VALIDO_BYTES,
        mime_type="image/png",
        nombre_archivo="uml_nm_intermedia.png",
        clave_idempotencia=uuid4(),
    )

    interaccion = env["use_case"].execute(cmd)
    assert interaccion.estado == EstadoInteraccionIa.COMPLETADO

    # 1. Cero segunda clase intermedia: exactamente 3 clases en BD (Producto, Venta, ProductoVenta)
    clases = env["clase_repo"].listar_por_diagrama(env["diagrama"].id)
    assert len(clases) == 3
    nombres_clases = {c.nombre: c for c in clases}
    assert "Producto" in nombres_clases
    assert "Venta" in nombres_clases
    assert "ProductoVenta" in nombres_clases
    assert "Producto_Venta" not in nombres_clases  # CERO segunda intermedia generada con nombre default

    clase_pv = nombres_clases["ProductoVenta"]
    attrs_pv = env["atributo_repo"].listar_por_clase(clase_pv.id)

    # 2. Atributos en ProductoVenta: id (PK), producto_id (FK), venta_id (FK), cantidad (extra)
    assert len(attrs_pv) == 4
    nombres_pv = {a.nombre: a for a in attrs_pv}
    assert "id" in nombres_pv
    assert "producto_id" in nombres_pv or "id_producto" in nombres_pv
    assert "venta_id" in nombres_pv or "id_venta" in nombres_pv
    assert "cantidad" in nombres_pv
    assert nombres_pv["cantidad"].tipo_dato == "integer"

    # 3. Estructura N:M en BD
    estructuras_nm = env["estructura_nm_repo"].listar_por_diagrama(env["diagrama"].id)
    assert len(estructuras_nm) == 1
    struct = estructuras_nm[0]
    assert struct.id_clase_intermedia == clase_pv.id
    assert struct.id_clase_origen == nombres_clases["Producto"].id
    assert struct.id_clase_destino == nombres_clases["Venta"].id

    # 4. Referencias FK en BD
    rfks_orig = env["referencia_fk_repo"].listar_por_relacion(struct.id_relacion_origen)
    rfks_dest = env["referencia_fk_repo"].listar_por_relacion(struct.id_relacion_destino)
    assert len(rfks_orig) == 1
    assert len(rfks_dest) == 1


def test_procesar_imagen_nm_nombre_distinto_e2e_con_atributos_extras(session: Session):
    json_respuesta = json.dumps({
        "clases": [
            {
                "referencia_semantica": "ref_est",
                "nombre": "Estudiante",
                "atributos": [{"nombre": "id", "es_pk": True}],
            },
            {
                "referencia_semantica": "ref_cur",
                "nombre": "Curso",
                "atributos": [{"nombre": "id", "es_pk": True}],
            },
            {
                "referencia_semantica": "ref_ins",
                "nombre": "Inscripcion",
                "atributos": [
                    {"nombre": "id", "es_pk": True},
                    {"nombre": "estudiante_id", "es_fk": True, "fk_destino_ref": "ref_est"},
                    {"nombre": "curso_id", "es_fk": True, "fk_destino_ref": "ref_cur"},
                    {"nombre": "fecha_inscripcion", "tipo_detectado": "date"},
                    {"nombre": "nota_final", "tipo_detectado": "decimal"},
                ],
            },
        ],
        "relaciones": [
            {
                "origen_ref": "ref_est",
                "destino_ref": "ref_cur",
                "tipo": "asociacion",
                "cardinalidad_origen": "0..*",
                "cardinalidad_destino": "0..*",
                "nombre": "matriculado",
                "es_nm": True,
            }
        ],
        "advertencias": [],
    })

    env = _crear_entorno_imagen(session, respuesta_json_imagen=json_respuesta)

    cmd = ProcesarImagenDiagramaIaCommand(
        usuario_id=env["usuario"].id,
        diagrama_id=env["diagrama"].id,
        contenido_imagen=PNG_VALIDO_BYTES,
        mime_type="image/png",
        nombre_archivo="uml_matricula.png",
        clave_idempotencia=uuid4(),
    )

    interaccion = env["use_case"].execute(cmd)
    assert interaccion.estado == EstadoInteraccionIa.COMPLETADO

    # Exactamente 3 clases creadas
    clases = env["clase_repo"].listar_por_diagrama(env["diagrama"].id)
    assert len(clases) == 3
    nombres_clases = {c.nombre: c for c in clases}
    assert "Inscripcion" in nombres_clases
    assert "Estudiante_Curso" not in nombres_clases

    clase_ins = nombres_clases["Inscripcion"]
    attrs_ins = env["atributo_repo"].listar_por_clase(clase_ins.id)
    nombres_ins = {a.nombre: a for a in attrs_ins}
    assert "fecha_inscripcion" in nombres_ins
    assert "nota_final" in nombres_ins
    assert len(attrs_ins) == 5  # id, estudiante_id, curso_id, fecha_inscripcion, nota_final


def test_procesar_imagen_e2e_caso_usuario_producto_venta_hola_agregacion_y_nm(session: Session):
    json_respuesta = json.dumps({
        "clases": [
            {
                "referencia_semantica": "ref_prod",
                "nombre": "Producto",
                "atributos": [
                    {"nombre": "id", "tipo_detectado": "integer", "es_pk": True},
                    {"nombre": "nombre", "tipo_detectado": "varchar", "es_pk": False},
                    {"nombre": "precio", "tipo_detectado": "decimal", "es_pk": False},
                    {"nombre": "imagen", "tipo_detectado": "varchar", "es_pk": False},
                ],
                "posicion_relativa_x": 0.1,
                "posicion_relativa_y": 0.2,
            },
            {
                "referencia_semantica": "ref_venta",
                "nombre": "Venta",
                "atributos": [
                    {"nombre": "id", "tipo_detectado": "integer", "es_pk": True},
                    {"nombre": "fecha", "tipo_detectado": "timestamp", "es_pk": False},
                ],
                "posicion_relativa_x": 0.8,
                "posicion_relativa_y": 0.2,
            },
            {
                "referencia_semantica": "ref_hola",
                "nombre": "Hola",
                "atributos": [
                    {"nombre": "id", "tipo_detectado": "integer", "es_pk": True},
                ],
                "posicion_relativa_x": 0.8,
                "posicion_relativa_y": 0.7,
            },
            {
                "referencia_semantica": "ref_pv",
                "nombre": "Producto_Venta",
                "atributos": [
                    {"nombre": "id", "tipo_detectado": "integer", "es_pk": True},
                    {"nombre": "producto_id", "tipo_detectado": "integer", "es_fk": True, "fk_destino_ref": "ref_prod"},
                    {"nombre": "venta_id", "tipo_detectado": "integer", "es_fk": True, "fk_destino_ref": "ref_venta"},
                    {"nombre": "cantidad", "tipo_detectado": "integer", "es_pk": False, "es_fk": False},
                ],
                "posicion_relativa_x": 0.45,
                "posicion_relativa_y": 0.2,
            },
        ],
        "relaciones": [
            {
                "origen_ref": "ref_prod",
                "destino_ref": "ref_pv",
                "tipo": "asociacion",
                "cardinalidad_origen": "1",
                "cardinalidad_destino": "0..*",
            },
            {
                "origen_ref": "ref_venta",
                "destino_ref": "ref_pv",
                "tipo": "asociacion",
                "cardinalidad_origen": "1",
                "cardinalidad_destino": "0..*",
            },
            {
                "origen_ref": "ref_hola",
                "destino_ref": "ref_venta",
                "tipo": "agregacion",
                "cardinalidad_origen": "0..*",
                "cardinalidad_destino": "1",
            },
        ],
        "advertencias": [],
    })

    env = _crear_entorno_imagen(session, respuesta_json_imagen=json_respuesta)

    cmd = ProcesarImagenDiagramaIaCommand(
        usuario_id=env["usuario"].id,
        diagrama_id=env["diagrama"].id,
        contenido_imagen=PNG_VALIDO_BYTES,
        mime_type="image/png",
        nombre_archivo="diagrama_completo.png",
        clave_idempotencia=uuid4(),
    )

    interaccion = env["use_case"].execute(cmd)
    assert interaccion.estado == EstadoInteraccionIa.COMPLETADO

    # 1. Exactamente 4 clases en BD: Producto, Venta, Hola, Producto_Venta
    clases = env["clase_repo"].listar_por_diagrama(env["diagrama"].id)
    assert len(clases) == 4
    nombres_clases = {c.nombre: c for c in clases}
    assert "Producto" in nombres_clases
    assert "Venta" in nombres_clases
    assert "Hola" in nombres_clases
    assert "Producto_Venta" in nombres_clases

    # 2. Atributos en Producto
    attrs_prod = env["atributo_repo"].listar_por_clase(nombres_clases["Producto"].id)
    nombres_prod = {a.nombre for a in attrs_prod}
    assert nombres_prod == {"id", "nombre", "precio", "imagen"}

    # 3. Atributos en Venta
    attrs_venta = env["atributo_repo"].listar_por_clase(nombres_clases["Venta"].id)
    nombres_venta = {a.nombre for a in attrs_venta}
    assert "id" in nombres_venta
    assert "fecha" in nombres_venta

    # 4. Atributos en Producto_Venta
    attrs_pv = env["atributo_repo"].listar_por_clase(nombres_clases["Producto_Venta"].id)
    nombres_pv = {a.nombre for a in attrs_pv}
    assert "id" in nombres_pv
    assert "cantidad" in nombres_pv
    assert len(attrs_pv) == 4  # id, id_producto, id_venta, cantidad

    # 5. Estructura NM en BD
    estructuras_nm = env["estructura_nm_repo"].listar_por_diagrama(env["diagrama"].id)
    assert len(estructuras_nm) == 1
    assert estructuras_nm[0].id_clase_intermedia == nombres_clases["Producto_Venta"].id

    # 6. Relación de agregación en BD
    relaciones = env["relacion_repo"].listar_por_diagrama(env["diagrama"].id)
    assert len(relaciones) == 3  # 2 de la estructura N:M + 1 de agregación
    rel_agreg = next((r for r in relaciones if r.tipo_relacion == "agregacion"), None)
    assert rel_agreg is not None
    assert rel_agreg.id_clase_origen == nombres_clases["Hola"].id
    assert rel_agreg.id_clase_destino == nombres_clases["Venta"].id



