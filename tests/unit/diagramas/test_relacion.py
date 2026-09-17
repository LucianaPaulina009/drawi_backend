from uuid import uuid4

import pytest

from app.modules.diagramas.domain.entities.relacion import Relacion
from app.modules.diagramas.domain.exceptions import (
    CardinalidadInvalidaException,
    ConectorInvalidoException,
    TipoRelacionInvalidoException,
)
from app.modules.diagramas.domain.value_objects.conector import Conector
from app.modules.diagramas.domain.value_objects.tipo_relacion import TipoRelacion


def test_crear_relacion_valida():
    r_id = uuid4()
    d_id = uuid4()
    c1_id = uuid4()
    c2_id = uuid4()

    relacion = Relacion.crear(
        id=r_id,
        id_diagrama=d_id,
        id_clase_origen=c1_id,
        id_clase_destino=c2_id,
        tipo_relacion="asociacion",
        cardinalidad_origen="1",
        cardinalidad_destino="0..*",
        conector_origen="right",
        conector_destino="left",
    )

    assert relacion.id == r_id
    assert relacion.id_diagrama == d_id
    assert relacion.id_clase_origen == c1_id
    assert relacion.id_clase_destino == c2_id
    assert relacion.tipo_relacion == "asociacion"
    assert relacion.cardinalidad_origen == "1"
    assert relacion.cardinalidad_destino == "0..*"
    assert relacion.conector_origen == "right"
    assert relacion.conector_destino == "left"


def test_crear_relacion_recursiva():
    r_id = uuid4()
    d_id = uuid4()
    c1_id = uuid4()

    relacion = Relacion.crear(
        id=r_id,
        id_diagrama=d_id,
        id_clase_origen=c1_id,
        id_clase_destino=c1_id,
        tipo_relacion=TipoRelacion.ASOCIACION,
        cardinalidad_origen="0..1",
        cardinalidad_destino="0..*",
        conector_origen=Conector.TOP,
        conector_destino=Conector.RIGHT,
    )

    assert relacion.id_clase_origen == relacion.id_clase_destino


def test_actualizar_relacion_parcial():
    r_id = uuid4()
    d_id = uuid4()
    c1_id = uuid4()
    c2_id = uuid4()

    relacion = Relacion.crear(
        id=r_id,
        id_diagrama=d_id,
        id_clase_origen=c1_id,
        id_clase_destino=c2_id,
        tipo_relacion="asociacion",
        cardinalidad_origen="1",
        cardinalidad_destino="1",
        conector_origen="top",
        conector_destino="bottom",
    )

    relacion.actualizar(
        cardinalidad_destino="1..*",
        conector_destino="right",
    )

    assert relacion.cardinalidad_destino == "1..*"
    assert relacion.conector_destino == "right"
    assert relacion.cardinalidad_origen == "1"
    assert relacion.conector_origen == "top"
