from __future__ import annotations

from app.modules.intercambio_enterprise_architect.application.dtos.atributo_ea_dto import AtributoEaDTO
from app.modules.intercambio_enterprise_architect.application.dtos.clase_ea_dto import ClaseEaDTO
from app.modules.intercambio_enterprise_architect.application.dtos.relacion_ea_dto import RelacionEaDTO
from app.modules.intercambio_enterprise_architect.application.services.reconciliador_modelo_ea import (
    ReconciliadorModeloEa,
)


def test_reconciliador_normaliza_tipos_y_remueve_pk_artificial():
    clases = [
        ClaseEaDTO(
            id_ea="EAID_1",
            nombre="Usuario",
            atributos=[
                AtributoEaDTO(nombre="id", tipo_dato="int", es_pk=True),  # Debe ignorarse porque DRAWI genera 'id'
                AtributoEaDTO(nombre="nombre", tipo_dato="VARCHAR2(100)", es_pk=False),
                AtributoEaDTO(nombre="activo", tipo_dato="BOOL", es_pk=False),
                AtributoEaDTO(nombre="precio", tipo_dato="FLOAT8", es_pk=False),
            ],
            posicion_x=100.0,
            posicion_y=100.0,
        )
    ]
    relaciones: list[RelacionEaDTO] = []

    plan = ReconciliadorModeloEa.reconciliar(clases, relaciones)

    assert len(plan.clases_regulares) == 1
    usuario = plan.clases_regulares[0]
    # 'id' fue descartado
    assert len(usuario.atributos) == 3
    nombres = [a.nombre for a in usuario.atributos]
    assert "id" not in nombres
    assert "nombre" in nombres

    tipos = {a.nombre: a.tipo_dato for a in usuario.atributos}
    assert tipos["nombre"] == "varchar"
    assert tipos["activo"] == "boolean"
    assert tipos["precio"] == "decimal"


def test_reconciliador_detecta_estructura_nm_intermedia():
    clases = [
        ClaseEaDTO(id_ea="EAID_P", nombre="Producto", posicion_x=100.0, posicion_y=100.0),
        ClaseEaDTO(id_ea="EAID_V", nombre="Venta", posicion_x=600.0, posicion_y=100.0),
        ClaseEaDTO(
            id_ea="EAID_PV",
            nombre="ProductoVenta",
            atributos=[
                AtributoEaDTO(nombre="id", tipo_dato="int", es_pk=True),
                AtributoEaDTO(nombre="id_producto", tipo_dato="int"),  # FK hacia Producto
                AtributoEaDTO(nombre="id_venta", tipo_dato="int"),     # FK hacia Venta
                AtributoEaDTO(nombre="cantidad", tipo_dato="int"),     # Payload
            ],
            posicion_x=350.0,
            posicion_y=100.0,
        ),
    ]

    relaciones = [
        # Producto (1) <---> (0..*) ProductoVenta
        RelacionEaDTO(
            id_ea="EAID_R1",
            id_clase_origen_ea="EAID_P",
            id_clase_destino_ea="EAID_PV",
            cardinalidad_origen="1",
            cardinalidad_destino="0..*",
            tipo_relacion="asociacion",
        ),
        # Venta (1) <---> (0..*) ProductoVenta
        RelacionEaDTO(
            id_ea="EAID_R2",
            id_clase_origen_ea="EAID_V",
            id_clase_destino_ea="EAID_PV",
            cardinalidad_origen="1",
            cardinalidad_destino="0..*",
            tipo_relacion="asociacion",
        ),
    ]

    plan = ReconciliadorModeloEa.reconciliar(clases, relaciones)

    assert len(plan.estructuras_nm) == 1
    nm = plan.estructuras_nm[0]
    assert nm.nombre_intermedia == "ProductoVenta"
    assert nm.clase_origen_ea == "EAID_P"
    assert nm.clase_destino_ea == "EAID_V"
    assert len(nm.atributos_payload) == 1
    assert nm.atributos_payload[0].nombre == "cantidad"

    # Producto y Venta quedan en regulares, ProductoVenta pasa a estructuras_nm
    assert len(plan.clases_regulares) == 2
    # Las relaciones binarias fueron absorbidas por la estructura N:M
    assert len(plan.relaciones_binarias) == 0


def test_reconciliador_asigna_posiciones_grid_si_no_hay_geometria():
    clases = [
        ClaseEaDTO(id_ea="EAID_1", nombre="A", posicion_x=None, posicion_y=None),
        ClaseEaDTO(id_ea="EAID_2", nombre="B", posicion_x=None, posicion_y=None),
    ]
    plan = ReconciliadorModeloEa.reconciliar(clases, [])
    assert plan.clases_regulares[0].posicion_x is not None
    assert plan.clases_regulares[0].posicion_y is not None
    assert plan.clases_regulares[1].posicion_x is not None
    assert plan.clases_regulares[1].posicion_y is not None
