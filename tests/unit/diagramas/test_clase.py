from uuid import UUID

import pytest

from app.modules.diagramas.domain.entities.clase import Clase
from app.modules.diagramas.domain.exceptions import (
    AnchoClaseInvalidoException,
    NombreClaseInvalidoException,
)


def test_crear_clase_persiste_estado_visual():
    clase = Clase.crear(
        id_diagrama=UUID(int=1),
        nombre="Usuario",
        posicion_x=120,
        posicion_y=80,
        ancho=260,
    )

    assert clase.nombre == "Usuario"
    assert clase.posicion_x == 120
    assert clase.posicion_y == 80
    assert clase.ancho == 260


@pytest.mark.parametrize("nombre", ["", "   "])
def test_nombre_clase_vacio_es_invalido(nombre: str):
    with pytest.raises(NombreClaseInvalidoException):
        Clase.crear(
            id_diagrama=UUID(int=1),
            nombre=nombre,
            posicion_x=0,
            posicion_y=0,
            ancho=1,
        )


def test_ancho_clase_debe_ser_mayor_que_cero():
    with pytest.raises(AnchoClaseInvalidoException):
        Clase.crear(
            id_diagrama=UUID(int=1),
            nombre="Usuario",
            posicion_x=0,
            posicion_y=0,
            ancho=0,
        )


def test_actualizacion_parcial_conserva_datos_no_enviados():
    clase = Clase.crear(
        id_diagrama=UUID(int=1),
        nombre="Usuario",
        posicion_x=10,
        posicion_y=20,
        ancho=300,
    )

    clase.actualizar(posicion_x=35, posicion_y=45)

    assert clase.nombre == "Usuario"
    assert clase.posicion_x == 35
    assert clase.posicion_y == 45
    assert clase.ancho == 300
