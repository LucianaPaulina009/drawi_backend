import pytest

from app.modules.diagramas.domain.exceptions import TipoRelacionInvalidoException
from app.modules.diagramas.domain.value_objects.tipo_relacion import TipoRelacion


def test_tipo_relacion_validos():
    assert TipoRelacion.validar("asociacion") == TipoRelacion.ASOCIACION
    assert TipoRelacion.validar("ASOCIACION_DIRIGIDA") == TipoRelacion.ASOCIACION_DIRIGIDA
    assert TipoRelacion.validar("herencia") == TipoRelacion.HERENCIA
    assert TipoRelacion.validar("realizacion") == TipoRelacion.REALIZACION
    assert TipoRelacion.validar("dependencia") == TipoRelacion.DEPENDENCIA
    assert TipoRelacion.validar("agregacion") == TipoRelacion.AGREGACION
    assert TipoRelacion.validar("composicion") == TipoRelacion.COMPOSICION


def test_tipo_relacion_invalido():
    with pytest.raises(TipoRelacionInvalidoException):
        TipoRelacion.validar("muchos_a_muchos")
    with pytest.raises(TipoRelacionInvalidoException):
        TipoRelacion.validar("")
