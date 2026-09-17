import pytest

from app.modules.diagramas.domain.exceptions import ConectorInvalidoException
from app.modules.diagramas.domain.value_objects.conector import Conector


def test_conector_validos():
    assert Conector.validar("top") == Conector.TOP
    assert Conector.validar("RIGHT") == Conector.RIGHT
    assert Conector.validar("bottom") == Conector.BOTTOM
    assert Conector.validar("left") == Conector.LEFT


def test_conector_invalido():
    with pytest.raises(ConectorInvalidoException):
        Conector.validar("center")
    with pytest.raises(ConectorInvalidoException):
        Conector.validar("arriba")
