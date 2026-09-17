import pytest

from app.modules.diagramas.domain.exceptions import CardinalidadInvalidaException
from app.modules.diagramas.domain.value_objects.cardinalidad import Cardinalidad


def test_cardinalidad_valores_validos():
    assert Cardinalidad("1").value == "1"
    assert Cardinalidad(" 0..1 ").value == "0..1"
    assert Cardinalidad("0..*").value == "0..*"
    assert Cardinalidad("1..*").value == "1..*"
    assert Cardinalidad("1..5").value == "1..5"
    assert Cardinalidad("0..10").value == "0..10"


def test_cardinalidad_invalida_vacia():
    with pytest.raises(CardinalidadInvalidaException):
        Cardinalidad("")
    with pytest.raises(CardinalidadInvalidaException):
        Cardinalidad("   ")


def test_cardinalidad_invalida_caracteres_no_numericos():
    with pytest.raises(CardinalidadInvalidaException):
        Cardinalidad("N..M")
    with pytest.raises(CardinalidadInvalidaException):
        Cardinalidad("a..b")
    with pytest.raises(CardinalidadInvalidaException):
        Cardinalidad("muchos")


def test_cardinalidad_invalida_limite_inferior_mayor():
    with pytest.raises(CardinalidadInvalidaException):
        Cardinalidad("5..1")
    with pytest.raises(CardinalidadInvalidaException):
        Cardinalidad("10..2")


def test_cardinalidad_invalida_comodin_mal_ubicado():
    with pytest.raises(CardinalidadInvalidaException):
        Cardinalidad("*..1")
    with pytest.raises(CardinalidadInvalidaException):
        Cardinalidad("*..*")
    with pytest.raises(CardinalidadInvalidaException):
        Cardinalidad("*")
