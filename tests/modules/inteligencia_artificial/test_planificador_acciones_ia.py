from uuid import uuid4
import pytest

from app.modules.inteligencia_artificial.application.services.planificador_acciones_ia import (
    PlanificadorAccionesIa,
)
from app.modules.inteligencia_artificial.application.services.validador_respuesta_ia import (
    AccionCrearAtributoSchema,
    AccionCrearClaseSchema,
    AccionCrearRelacionSchema,
)
from app.modules.inteligencia_artificial.domain.exceptions import PlanIaInvalidoException


def test_planificador_ordena_clases_atributos_relaciones():
    acciones = [
        AccionCrearRelacionSchema(
            clase_origen_referencia="a",
            clase_destino_referencia="b",
            nombre="R",
        ),
        AccionCrearAtributoSchema(
            clase_referencia="a",
            nombre="nombre",
        ),
        AccionCrearClaseSchema(
            referencia="b",
            nombre="B",
        ),
        AccionCrearClaseSchema(
            referencia="a",
            nombre="A",
        ),
    ]

    ordenadas = PlanificadorAccionesIa.planificar(acciones)

    assert isinstance(ordenadas[0], AccionCrearClaseSchema)
    assert isinstance(ordenadas[1], AccionCrearClaseSchema)
    assert isinstance(ordenadas[2], AccionCrearAtributoSchema)
    assert isinstance(ordenadas[3], AccionCrearRelacionSchema)


def test_planificador_falla_si_atributo_referencia_clase_inexistente():
    acciones = [
        AccionCrearAtributoSchema(
            clase_referencia="desconocida",
            nombre="campo",
        )
    ]
    with pytest.raises(PlanIaInvalidoException):
        PlanificadorAccionesIa.planificar(acciones)


def test_planificador_falla_si_relacion_referencia_origen_inexistente():
    acciones = [
        AccionCrearClaseSchema(referencia="a", nombre="A"),
        AccionCrearRelacionSchema(
            clase_origen_referencia="a",
            clase_destino_referencia="no_existe",
        ),
    ]
    with pytest.raises(PlanIaInvalidoException):
        PlanificadorAccionesIa.planificar(acciones)


def test_planificador_acepta_clases_existentes_del_diagrama():
    id_existente = uuid4()
    clases_existentes = {"usuario": id_existente}

    acciones = [
        AccionCrearAtributoSchema(
            clase_referencia="usuario",
            nombre="telefono",
        )
    ]

    ordenadas = PlanificadorAccionesIa.planificar(acciones, clases_existentes=clases_existentes)
    assert len(ordenadas) == 1
    assert ordenadas[0].nombre == "telefono"


def test_planificador_estructura_nm_con_atributos():
    from app.modules.inteligencia_artificial.application.services.validador_respuesta_ia import (
        AccionCrearEstructuraNmSchema,
    )

    clases_existentes = {"cliente": uuid4(), "vehiculo": uuid4()}
    acciones = [
        AccionCrearAtributoSchema(
            clase_referencia="Cliente_Vehiculo",
            nombre="prueba",
            tipo_dato="text",
        ),
        AccionCrearEstructuraNmSchema(
            clase_origen_referencia="Cliente",
            clase_destino_referencia="Vehiculo",
            nombre_intermedia="Cliente_Vehiculo",
        ),
    ]

    ordenadas = PlanificadorAccionesIa.planificar(acciones, clases_existentes=clases_existentes)
    assert len(ordenadas) == 2
    # La estructura N:M debe ordenarse antes del atributo de la tabla intermedia
    assert isinstance(ordenadas[0], AccionCrearEstructuraNmSchema)
    assert isinstance(ordenadas[1], AccionCrearAtributoSchema)
    assert ordenadas[1].clase_referencia == "Cliente_Vehiculo"
    assert ordenadas[1].nombre == "prueba"


def test_planificador_estructura_nm_falla_si_origen_desconocido():
    from app.modules.inteligencia_artificial.application.services.validador_respuesta_ia import (
        AccionCrearEstructuraNmSchema,
    )

    clases_existentes = {"vehiculo": uuid4()}
    acciones = [
        AccionCrearEstructuraNmSchema(
            clase_origen_referencia="Inexistente",
            clase_destino_referencia="Vehiculo",
            nombre_intermedia="Inexistente_Vehiculo",
        )
    ]
    with pytest.raises(PlanIaInvalidoException):
        PlanificadorAccionesIa.planificar(acciones, clases_existentes=clases_existentes)


def test_planificador_orden_topologico_mixto_base_nm_intermedia():
    from app.modules.inteligencia_artificial.application.services.validador_respuesta_ia import (
        AccionCrearEstructuraNmSchema,
    )

    # Entradas en orden aleatorio
    acciones = [
        # Atributo de tabla intermedia (debe ir al final de creaciones)
        AccionCrearAtributoSchema(
            clase_referencia="Estudiante_Curso",
            nombre="calificacion",
            tipo_dato="decimal",
        ),
        # Relación N:M (debe ir después de clases base y sus atributos)
        AccionCrearEstructuraNmSchema(
            clase_origen_referencia="estudiante",
            clase_destino_referencia="curso",
            nombre_intermedia="Estudiante_Curso",
            referencia_intermedia="estudiante_curso",
        ),
        # Atributo de clase base Curso
        AccionCrearAtributoSchema(
            clase_referencia="curso",
            nombre="creditos",
            tipo_dato="integer",
        ),
        # Clase base Curso
        AccionCrearClaseSchema(
            referencia="curso",
            nombre="Curso",
        ),
        # Clase base Estudiante
        AccionCrearClaseSchema(
            referencia="estudiante",
            nombre="Estudiante",
        ),
        # Atributo de clase base Estudiante
        AccionCrearAtributoSchema(
            clase_referencia="estudiante",
            nombre="matricula",
            tipo_dato="varchar",
        ),
        # Relación 1:N entre Estudiante y Carrera
        AccionCrearRelacionSchema(
            clase_origen_referencia="carrera",
            clase_destino_referencia="estudiante",
            nombre="carrera_estudiante",
        ),
    ]

    carrera_id = uuid4()
    plan = PlanificadorAccionesIa.planificar(acciones, clases_existentes={"carrera": carrera_id})

    # Verificar orden:
    # 0, 1: Clases base (Curso, Estudiante)
    assert isinstance(plan[0], AccionCrearClaseSchema)
    assert isinstance(plan[1], AccionCrearClaseSchema)

    # 2, 3: Atributos base (creditos, matricula)
    assert isinstance(plan[2], AccionCrearAtributoSchema)
    assert plan[2].nombre in {"creditos", "matricula"}
    assert isinstance(plan[3], AccionCrearAtributoSchema)
    assert plan[3].nombre in {"creditos", "matricula"}

    # 4: Estructura NM (Estudiante_Curso)
    assert isinstance(plan[4], AccionCrearEstructuraNmSchema)

    # 5: Relación (carrera_estudiante)
    assert isinstance(plan[5], AccionCrearRelacionSchema)

    # 6: Atributo de tabla intermedia (calificacion)
    assert isinstance(plan[6], AccionCrearAtributoSchema)
    assert plan[6].nombre == "calificacion"
    assert plan[6].clase_referencia == "Estudiante_Curso"


def test_planificador_filtra_llaves_primarias_redundantes():
    acciones = [
        AccionCrearClaseSchema(referencia="prod", nombre="Producto"),
        AccionCrearAtributoSchema(
            clase_referencia="prod",
            nombre="id",
            tipo_dato="integer",
            es_llave_primaria=True,
        ),
        AccionCrearAtributoSchema(
            clase_referencia="prod",
            nombre="id_producto",
            tipo_dato="integer",
        ),
        AccionCrearAtributoSchema(
            clase_referencia="prod",
            nombre="nombre",
            tipo_dato="varchar",
        ),
        AccionCrearAtributoSchema(
            clase_referencia="prod",
            nombre="precio",
            tipo_dato="decimal",
        ),
    ]

    plan = PlanificadorAccionesIa.planificar(acciones)

    # Debe contener la clase Producto y SOLO 'nombre' y 'precio' (id e id_producto filtrados)
    assert len(plan) == 3
    assert isinstance(plan[0], AccionCrearClaseSchema)
    assert plan[0].nombre == "Producto"
    assert isinstance(plan[1], AccionCrearAtributoSchema)
    assert plan[1].nombre == "nombre"
    assert isinstance(plan[2], AccionCrearAtributoSchema)
    assert plan[2].nombre == "precio"


def test_planificador_filtra_fks_y_pks_en_estructura_nm_pero_conserva_payload():
    from app.modules.inteligencia_artificial.application.services.validador_respuesta_ia import (
        AccionCrearEstructuraNmSchema,
    )

    acciones = [
        AccionCrearClaseSchema(referencia="prod", nombre="Producto"),
        AccionCrearClaseSchema(referencia="vta", nombre="Venta"),
        AccionCrearEstructuraNmSchema(
            clase_origen_referencia="prod",
            clase_destino_referencia="vta",
            nombre_intermedia="Producto_Venta",
            referencia_intermedia="pv",
        ),
        # Atributos redundantes en la intermedia:
        AccionCrearAtributoSchema(
            clase_referencia="pv",
            nombre="id",
            es_llave_primaria=True,
        ),
        AccionCrearAtributoSchema(
            clase_referencia="pv",
            nombre="id_producto",
            tipo_dato="integer",
        ),
        AccionCrearAtributoSchema(
            clase_referencia="Producto_Venta",
            nombre="venta_id",
            tipo_dato="integer",
        ),
        # Atributo payload real que SÍ debe conservarse:
        AccionCrearAtributoSchema(
            clase_referencia="Producto_Venta",
            nombre="cantidad",
            tipo_dato="integer",
        ),
        AccionCrearAtributoSchema(
            clase_referencia="pv",
            nombre="precio_unitario",
            tipo_dato="decimal",
        ),
    ]

    plan = PlanificadorAccionesIa.planificar(acciones)

    # Clases: Producto, Venta
    # Estructura N:M: Producto_Venta
    # Atributos de intermedia: cantidad, precio_unitario
    assert len(plan) == 5
    assert isinstance(plan[0], AccionCrearClaseSchema)
    assert isinstance(plan[1], AccionCrearClaseSchema)
    assert isinstance(plan[2], AccionCrearEstructuraNmSchema)
    assert isinstance(plan[3], AccionCrearAtributoSchema)
    assert plan[3].nombre in {"cantidad", "precio_unitario"}
    assert isinstance(plan[4], AccionCrearAtributoSchema)
    assert plan[4].nombre in {"cantidad", "precio_unitario"}


def test_planificador_reconcilia_fk_en_relacion_1_a_n():
    acciones = [
        AccionCrearClaseSchema(referencia="u", nombre="Usuario"),
        AccionCrearClaseSchema(referencia="p", nombre="Pedido"),
        AccionCrearAtributoSchema(
            clase_referencia="p",
            nombre="usuario_id",
            tipo_dato="integer",
        ),
        AccionCrearAtributoSchema(
            clase_referencia="p",
            nombre="total",
            tipo_dato="decimal",
        ),
        AccionCrearRelacionSchema(
            clase_origen_referencia="u",
            clase_destino_referencia="p",
            cardinalidad_origen="1",
            cardinalidad_destino="0..*",
            nombre="usuario_pedidos",
        ),
    ]

    plan = PlanificadorAccionesIa.planificar(acciones)

    # 1, 2: Clases Usuario, Pedido
    # 3: Atributo 'total' (usuario_id fue reconciliado con la relación y excluido de atributos sueltos)
    # 4: Relación con nombre_fk = "usuario_id"
    assert len(plan) == 4
    assert isinstance(plan[0], AccionCrearClaseSchema)
    assert isinstance(plan[1], AccionCrearClaseSchema)
    assert isinstance(plan[2], AccionCrearAtributoSchema)
    assert plan[2].nombre == "total"
    assert isinstance(plan[3], AccionCrearRelacionSchema)
    assert plan[3].nombre_fk == "usuario_id"
    assert plan[3].clase_fk_referencia in {"p", "Pedido"}



