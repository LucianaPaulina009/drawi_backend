from uuid import uuid4
import pytest
from sqlmodel import Session

from app.core.dependencies import get_event_bus
from app.shared.infrastructure.unit_of_work import SqlModelUnitOfWork
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
from app.modules.inteligencia_artificial.application.services.ejecutor_plan_ia import EjecutorPlanIa
from app.modules.diagramas.application.services.idempotencia_diagrama import IdempotenciaDiagramaService
from app.modules.diagramas.application.use_cases.estructura_relacion_nm.crear_estructura_relacion_nm import (
    CrearEstructuraRelacionNmUseCase,
)
from app.modules.diagramas.infrastructure.persistence.repositories.sqlmodel_operacion_diagrama_repository import (
    SQLModelOperacionDiagramaRepository,
)
from app.modules.inteligencia_artificial.application.services.validador_respuesta_ia import (
    AccionCrearAtributoSchema,
    AccionCrearClaseSchema,
    AccionCrearEstructuraNmSchema,
    AccionCrearRelacionSchema,
    PosicionSchema,
)
from app.shared.infrastructure.db.better_auth import BetterAuthUser


def _setup_repos(session: Session):
    p_repo = SQLModelProyectoRepository(session)
    d_repo = SQLModelDiagramaRepository(session)
    c_repo = SQLModelClaseRepository(session)
    a_repo = SQLModelAtributoRepository(session)
    r_repo = SQLModelRelacionRepository(session)
    rfk_repo = SQLModelReferenciaFKRepository(session)
    nm_repo = SQLModelEstructuraRelacionNmRepository(session)
    op_repo = SQLModelOperacionDiagramaRepository(session)
    col_repo = SQLModelColaboradorProyectoRepository(session)
    uow = SqlModelUnitOfWork(session, get_event_bus())
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
    return ejecutor, c_repo, a_repo, r_repo, nm_repo


def test_ejecutor_plan_ia_crea_clases_atributos_y_relaciones(session: Session):
    usuario = BetterAuthUser(id="user-ejec-1", name="Ejec", email="ejec@drawi.com", email_verified=True)
    session.add(usuario)
    session.commit()

    proyecto = ProyectoModel(propietario_id=usuario.id, nombre="Proy", color="azul", icono="caja", slug="proy-ejec")
    session.add(proyecto)
    session.commit()

    diagrama = DiagramaModel(id_proyecto=proyecto.id, nombre="Pag 1", numero=1)
    session.add(diagrama)
    session.commit()

    ejecutor, c_repo, a_repo, r_repo, _ = _setup_repos(session)

    acciones = [
        AccionCrearClaseSchema(referencia="cliente", nombre="Cliente"),
        AccionCrearClaseSchema(referencia="pedido", nombre="Pedido"),
        AccionCrearAtributoSchema(clase_referencia="cliente", nombre="nombre", tipo_dato="varchar", longitud=100),
        AccionCrearRelacionSchema(clase_origen_referencia="cliente", clase_destino_referencia="pedido", tipo_relacion="asociacion", nombre="Realiza"),
    ]

    resultados = ejecutor.ejecutar_plan(
        usuario_id=usuario.id,
        diagrama_id=diagrama.id,
        acciones=acciones,
    )

    assert len(resultados) == 4, f"Resultados: {resultados}"
    for r in resultados:
        assert r["estado"] == "completado", f"Paso {r.get('paso')} falló: {r.get('error')}"

    # Verificar que las entidades existen en la base de datos
    clases = c_repo.listar_por_diagrama(diagrama.id)
    assert len(clases) == 2
    nombres_clases = {c.nombre for c in clases}
    assert "Cliente" in nombres_clases
    assert "Pedido" in nombres_clases

    relaciones = r_repo.listar_por_diagrama(diagrama.id)
    assert len(relaciones) == 1
    assert relaciones[0].nombre == "Realiza"


def test_ejecutor_plan_ia_crea_estructura_nm_con_atributo_en_intermedia(session: Session):
    usuario = BetterAuthUser(id="user-ejec-nm", name="EjecNM", email="ejecnm@drawi.com", email_verified=True)
    session.add(usuario)
    session.commit()

    proyecto = ProyectoModel(propietario_id=usuario.id, nombre="Proy NM", color="azul", icono="caja", slug="proy-ejec-nm")
    session.add(proyecto)
    session.commit()

    diagrama = DiagramaModel(id_proyecto=proyecto.id, nombre="Diagrama NM", numero=1)
    session.add(diagrama)
    session.commit()

    ejecutor, c_repo, a_repo, r_repo, nm_repo = _setup_repos(session)

    # 1. Crear clases Cliente y Vehiculo previamente
    acciones_iniciales = [
        AccionCrearClaseSchema(referencia="cliente", nombre="Cliente"),
        AccionCrearClaseSchema(referencia="vehiculo", nombre="Vehiculo"),
    ]
    ejecutor.ejecutar_plan(
        usuario_id=usuario.id,
        diagrama_id=diagrama.id,
        acciones=acciones_iniciales,
    )

    # 2. Plan ordenado con relación muchos a muchos y creación de atributo 'prueba' en la tabla intermedia
    acciones_nm = [
        AccionCrearEstructuraNmSchema(
            clase_origen_referencia="Cliente",
            clase_destino_referencia="Vehiculo",
            nombre_intermedia="Cliente_Vehiculo",
        ),
        AccionCrearAtributoSchema(
            clase_referencia="Cliente_Vehiculo",
            nombre="prueba",
            tipo_dato="text",
        ),
    ]

    resultados = ejecutor.ejecutar_plan(
        usuario_id=usuario.id,
        diagrama_id=diagrama.id,
        acciones=acciones_nm,
    )

    assert len(resultados) == 2, f"Resultados: {resultados}"
    assert resultados[0]["estado"] == "completado"
    assert resultados[0]["tipo"] == "crear_estructura_nm"
    assert resultados[1]["estado"] == "completado"
    assert resultados[1]["tipo"] == "crear_atributo"
    assert resultados[1]["nombre"] == "prueba"

    # Verificar que la estructura NM existe
    estructuras = nm_repo.listar_por_diagrama(diagrama.id)
    assert len(estructuras) == 1

    # Verificar que la clase intermedia existe y tiene sus llaves (id, cliente_id/id_cliente, vehiculo_id/id_vehiculo) más el atributo 'prueba'
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

    # Verificar que las 2 relaciones hacia la intermedia existen
    relaciones = r_repo.listar_por_diagrama(diagrama.id)
    assert len(relaciones) == 2


def test_ejecutor_plan_ia_selecciona_mejores_conectores_segun_geometria(session: Session):
    usuario = BetterAuthUser(id="user-ejec-geo", name="EjecGeo", email="geo@drawi.com", email_verified=True)
    session.add(usuario)
    session.commit()

    proyecto = ProyectoModel(propietario_id=usuario.id, nombre="Proy Geo", color="azul", icono="caja", slug="proy-geo")
    session.add(proyecto)
    session.commit()

    diagrama = DiagramaModel(id_proyecto=proyecto.id, nombre="Diagrama Geo", numero=1)
    session.add(diagrama)
    session.commit()

    ejecutor, c_repo, a_repo, r_repo, nm_repo = _setup_repos(session)

    # 1. Caso Horizontal: Clase A a la izquierda (x=100), Clase B a la derecha (x=600)
    from app.modules.inteligencia_artificial.application.services.validador_respuesta_ia import PosicionSchema

    acciones_h = [
        AccionCrearClaseSchema(referencia="a", nombre="ClaseA", posicion=PosicionSchema(x=100.0, y=200.0)),
        AccionCrearClaseSchema(referencia="b", nombre="ClaseB", posicion=PosicionSchema(x=600.0, y=200.0)),
        AccionCrearRelacionSchema(clase_origen_referencia="a", clase_destino_referencia="b", tipo_relacion="asociacion"),
    ]
    res_h = ejecutor.ejecutar_plan(usuario_id=usuario.id, diagrama_id=diagrama.id, acciones=acciones_h)
    assert all(r["estado"] == "completado" for r in res_h)

    rel_h = next(r for r in r_repo.listar_por_diagrama(diagrama.id) if r.nombre == "Asociación" or not r.nombre)
    assert rel_h.conector_origen.startswith("right")
    assert rel_h.conector_destino.startswith("left")

    # 2. Caso Vertical: Clase C abajo (y=600), Clase D arriba (y=100)
    acciones_v = [
        AccionCrearClaseSchema(referencia="c", nombre="ClaseC", posicion=PosicionSchema(x=200.0, y=600.0)),
        AccionCrearClaseSchema(referencia="d", nombre="ClaseD", posicion=PosicionSchema(x=200.0, y=100.0)),
        AccionCrearRelacionSchema(clase_origen_referencia="c", clase_destino_referencia="d", tipo_relacion="asociacion"),
    ]
    res_v = ejecutor.ejecutar_plan(usuario_id=usuario.id, diagrama_id=diagrama.id, acciones=acciones_v)
    assert all(r["estado"] == "completado" for r in res_v)

    clase_c = next(c for c in c_repo.listar_por_diagrama(diagrama.id) if c.nombre == "ClaseC")
    clase_d = next(c for c in c_repo.listar_por_diagrama(diagrama.id) if c.nombre == "ClaseD")
    rel_v = next(r for r in r_repo.listar_por_diagrama(diagrama.id) if r.id_clase_origen == clase_c.id and r.id_clase_destino == clase_d.id)
    assert rel_v.conector_origen.startswith("top")
    assert rel_v.conector_destino.startswith("bottom")


def test_ejecutor_plan_ia_crear_clase_precio_con_atributos_numero_y_cantidad(session: Session):
    usuario = BetterAuthUser(id="user-precio-1", name="UserPrecio", email="precio@drawi.com", email_verified=True)
    session.add(usuario)
    session.commit()

    proyecto = ProyectoModel(propietario_id=usuario.id, nombre="Proy Precio", color="azul", icono="caja", slug="proy-precio")
    session.add(proyecto)
    session.commit()

    diagrama = DiagramaModel(id_proyecto=proyecto.id, nombre="Diagrama Precio", numero=1)
    session.add(diagrama)
    session.commit()

    ejecutor, c_repo, a_repo, _, _ = _setup_repos(session)

    # Simular la respuesta de Gemini cuando el usuario pide: "crea una clase llamada Precio con atributos número y cantidad"
    acciones = [
        AccionCrearClaseSchema(referencia="precio", nombre="Precio"),
        AccionCrearAtributoSchema(clase_referencia="precio", nombre="número", tipo_dato="número"),
        AccionCrearAtributoSchema(clase_referencia="precio", nombre="cantidad", tipo_dato="cantidad"),
    ]

    resultados = ejecutor.ejecutar_plan(
        usuario_id=usuario.id,
        diagrama_id=diagrama.id,
        acciones=acciones,
    )

    assert len(resultados) == 3, f"Resultados: {resultados}"
    assert all(r["estado"] == "completado" for r in resultados), f"Falló algún paso: {resultados}"

    clases = c_repo.listar_por_diagrama(diagrama.id)
    assert len(clases) == 1
    clase_precio = clases[0]
    assert clase_precio.nombre == "Precio"

    attrs = a_repo.listar_por_clase(clase_precio.id)
    # Debe tener el id automático + los 2 atributos creados
    nombres_attrs = {a.nombre: a.tipo_dato for a in attrs}
    assert "id" in nombres_attrs
    assert "número" in nombres_attrs
    assert "cantidad" in nombres_attrs
    assert nombres_attrs["número"] == "integer"
    assert nombres_attrs["cantidad"] == "integer"


def test_ejecutor_plan_ia_crear_clase_evita_colision_con_clases_existentes(session: Session):
    from app.modules.inteligencia_artificial.application.services.servicio_layout_importacion import (
        BoundingBox,
        ServicioLayoutImportacion,
    )
    usuario = BetterAuthUser(id="user-colision-1", name="UserColision", email="colision@drawi.com", email_verified=True)
    session.add(usuario)
    session.commit()

    proyecto = ProyectoModel(propietario_id=usuario.id, nombre="Proy Colision", color="azul", icono="caja", slug="proy-colision")
    session.add(proyecto)
    session.commit()

    diagrama = DiagramaModel(id_proyecto=proyecto.id, nombre="Diagrama Colision", numero=1)
    session.add(diagrama)
    session.commit()

    ejecutor, c_repo, a_repo, _, _ = _setup_repos(session)

    # 1. Crear Clase A en (100, 100)
    acciones_1 = [
        AccionCrearClaseSchema(referencia="a", nombre="ClaseA", posicion=PosicionSchema(x=100.0, y=100.0)),
    ]
    ejecutor.ejecutar_plan(usuario_id=usuario.id, diagrama_id=diagrama.id, acciones=acciones_1)

    # 2. Intentar crear Clase B exactamente en la misma posición (100, 100)
    acciones_2 = [
        AccionCrearClaseSchema(referencia="b", nombre="ClaseB", posicion=PosicionSchema(x=100.0, y=100.0)),
    ]
    res = ejecutor.ejecutar_plan(usuario_id=usuario.id, diagrama_id=diagrama.id, acciones=acciones_2)
    assert all(r["estado"] == "completado" for r in res)

    clases = c_repo.listar_por_diagrama(diagrama.id)
    assert len(clases) == 2
    clase_a = next(c for c in clases if c.nombre == "ClaseA")
    clase_b = next(c for c in clases if c.nombre == "ClaseB")

    # Verificar que no colisionan
    dim_a = ServicioLayoutImportacion.estimar_dimensiones_clase(len(a_repo.listar_por_clase(clase_a.id)), ancho=float(clase_a.ancho))
    dim_b = ServicioLayoutImportacion.estimar_dimensiones_clase(len(a_repo.listar_por_clase(clase_b.id)), ancho=float(clase_b.ancho))

    box_a = BoundingBox(float(clase_a.posicion_x), float(clase_a.posicion_y), float(clase_a.posicion_x) + dim_a[0], float(clase_a.posicion_y) + dim_a[1])
    box_b = BoundingBox(float(clase_b.posicion_x), float(clase_b.posicion_y), float(clase_b.posicion_x) + dim_b[0], float(clase_b.posicion_y) + dim_b[1])

    assert not box_b.intersecta(box_a, margen=20.0), f"Las clases A ({box_a}) y B ({box_b}) colisionan"


def test_ejecutor_plan_ia_crear_multiples_clases_sin_solapamiento(session: Session):
    from app.modules.inteligencia_artificial.application.services.servicio_layout_importacion import (
        BoundingBox,
        ServicioLayoutImportacion,
    )
    usuario = BetterAuthUser(id="user-multi-pos", name="UserMultiPos", email="multi@drawi.com", email_verified=True)
    session.add(usuario)
    session.commit()

    proyecto = ProyectoModel(propietario_id=usuario.id, nombre="Proy Multi", color="azul", icono="caja", slug="proy-multi")
    session.add(proyecto)
    session.commit()

    diagrama = DiagramaModel(id_proyecto=proyecto.id, nombre="Diagrama Multi", numero=1)
    session.add(diagrama)
    session.commit()

    ejecutor, c_repo, a_repo, _, _ = _setup_repos(session)

    # Crear 3 clases sin especificar posición (o con la misma posición por defecto)
    acciones = [
        AccionCrearClaseSchema(referencia="c1", nombre="Cliente"),
        AccionCrearClaseSchema(referencia="c2", nombre="Pedido"),
        AccionCrearClaseSchema(referencia="c3", nombre="Producto"),
    ]
    res = ejecutor.ejecutar_plan(usuario_id=usuario.id, diagrama_id=diagrama.id, acciones=acciones)
    assert all(r["estado"] == "completado" for r in res)

    clases = c_repo.listar_por_diagrama(diagrama.id)
    assert len(clases) == 3

    boxes = []
    for c in clases:
        dim = ServicioLayoutImportacion.estimar_dimensiones_clase(len(a_repo.listar_por_clase(c.id)), ancho=float(c.ancho))
        boxes.append((c.nombre, BoundingBox(float(c.posicion_x), float(c.posicion_y), float(c.posicion_x) + dim[0], float(c.posicion_y) + dim[1])))

    # Verificar todas las parejas
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            nombre_1, b1 = boxes[i]
            nombre_2, b2 = boxes[j]
            assert not b1.intersecta(b2, margen=20.0), f"Colisión entre {nombre_1} ({b1}) y {nombre_2} ({b2})"


def test_ejecutor_plan_ia_resuelve_referencias_con_prefijos_y_espacios(session: Session):
    usuario = BetterAuthUser(id="user-ref-norm", name="RefNorm", email="refnorm@drawi.com", email_verified=True)
    session.add(usuario)
    session.commit()

    proyecto = ProyectoModel(propietario_id=usuario.id, nombre="Proy RefNorm", color="azul", icono="caja", slug="proy-refnorm")
    session.add(proyecto)
    session.commit()

    diagrama = DiagramaModel(id_proyecto=proyecto.id, nombre="Diagrama RefNorm", numero=1)
    session.add(diagrama)
    session.commit()

    ejecutor, c_repo, a_repo, r_repo, _ = _setup_repos(session)

    # Note: Class references are "ref_prod" and "ref_cat", but relation references "ref producto" and "categoría"
    acciones = [
        AccionCrearClaseSchema(referencia="ref_prod", nombre="Producto"),
        AccionCrearClaseSchema(referencia="ref_cat", nombre="Categoría"),
        AccionCrearRelacionSchema(
            clase_origen_referencia="ref producto",
            clase_destino_referencia="categoría",
            tipo_relacion="asociacion",
            nombre="pertenece_a",
        ),
    ]

    resultados = ejecutor.ejecutar_plan(
        usuario_id=usuario.id,
        diagrama_id=diagrama.id,
        acciones=acciones,
    )

    assert len(resultados) == 3
    assert all(r["estado"] == "completado" for r in resultados), f"Resultados: {resultados}"

    rels = r_repo.listar_por_diagrama(diagrama.id)
    assert len(rels) == 1
    assert rels[0].nombre == "pertenece_a"





