from uuid import UUID

import pytest

from app.modules.diagramas.domain.entities.diagrama import Diagrama
from app.modules.diagramas.domain.exceptions import (
    NombreDiagramaInvalidoException,
    NumeroDiagramaInvalidoException,
)


def test_crear_diagrama_sin_nombre_usa_pagina_y_numero():
    diagrama = Diagrama.crear(id_proyecto=UUID(int=1), numero=4)

    assert diagrama.nombre == "Página 4"
    assert diagrama.numero == 4


@pytest.mark.parametrize("nombre", ["", "   "])
def test_nombre_diagrama_vacio_es_invalido(nombre: str):
    with pytest.raises(NombreDiagramaInvalidoException):
        Diagrama.crear(id_proyecto=UUID(int=1), numero=1, nombre=nombre)


def test_numero_diagrama_debe_ser_positivo():
    with pytest.raises(NumeroDiagramaInvalidoException):
        Diagrama.crear(id_proyecto=UUID(int=1), numero=0)


def test_obtener_menor_numero_positivo_disponible():
    assert Diagrama.obtener_siguiente_numero([1, 2, 5]) == 3
    assert Diagrama.obtener_siguiente_numero([1, 2, 3, 5]) == 4
    assert Diagrama.obtener_siguiente_numero([1, 2, 3, 4, 5]) == 6
