from uuid import UUID

import pytest

from app.modules.diagramas.domain.entities.atributo import Atributo
from app.modules.diagramas.domain.exceptions import (
    ConfiguracionAtributoInvalidaException,
    NombreAtributoInvalidoException,
)


def test_atributo_normaliza_campos_dependientes_del_tipo_de_dato():
    atributo = Atributo.crear(
        id_clase=UUID(int=1),
        tipo_dato=" VARCHAR ",
        nombre=" codigo ",
        longitud=40,
        precision=10,
        escala=2,
        orden_de_posicion=1,
    )

    assert atributo.tipo_dato == "varchar"
    assert atributo.nombre == "codigo"
    assert (atributo.longitud, atributo.precision, atributo.escala) == (40, None, None)

    atributo.actualizar(tipo_dato="numeric", precision=12, escala=3)

    assert (atributo.longitud, atributo.precision, atributo.escala) == (None, 12, 3)


def test_tipo_sin_configuracion_limpia_longitud_precision_y_escala():
    atributo = Atributo.crear(
        id_clase=UUID(int=1),
        tipo_dato="numeric",
        nombre="total",
        precision=10,
        escala=2,
        orden_de_posicion=1,
    )

    atributo.actualizar(tipo_dato="boolean")

    assert (atributo.longitud, atributo.precision, atributo.escala) == (None, None, None)


def test_escala_no_puede_superar_la_precision():
    with pytest.raises(ConfiguracionAtributoInvalidaException):
        Atributo.crear(
            id_clase=UUID(int=1),
            tipo_dato="numeric",
            nombre="monto",
            precision=3,
            escala=4,
            orden_de_posicion=1,
        )


@pytest.mark.parametrize("nombre", ["", "   "])
def test_nombre_atributo_vacio_es_invalido(nombre: str):
    with pytest.raises(NombreAtributoInvalidoException):
        Atributo.crear(
            id_clase=UUID(int=1),
            tipo_dato="text",
            nombre=nombre,
            orden_de_posicion=1,
        )
