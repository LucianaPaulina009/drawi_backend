from uuid import uuid4

import pytest

from app.modules.diagramas.domain.entities.referencia_fk import ReferenciaFK
from app.modules.diagramas.domain.exceptions import AccionReferencialInvalidaException
from app.modules.diagramas.domain.value_objects.accion_referencial import (
    AccionReferencial,
)


def test_crear_referencia_fk_valida():
    ref_id = uuid4()
    rel_id = uuid4()
    attr_fk_id = uuid4()
    attr_ref_id = uuid4()

    referencia = ReferenciaFK.crear(
        id=ref_id,
        id_relacion=rel_id,
        id_atributo_fk=attr_fk_id,
        id_atributo_referenciado=attr_ref_id,
        on_delete="CASCADE",
        on_update="RESTRICT",
    )

    assert referencia.id == ref_id
    assert referencia.id_relacion == rel_id
    assert referencia.id_atributo_fk == attr_fk_id
    assert referencia.id_atributo_referenciado == attr_ref_id
    assert referencia.on_delete == "CASCADE"
    assert referencia.on_update == "RESTRICT"


def test_crear_referencia_fk_default_actions():
    ref_id = uuid4()
    rel_id = uuid4()
    attr_fk_id = uuid4()
    attr_ref_id = uuid4()

    referencia = ReferenciaFK.crear(
        id=ref_id,
        id_relacion=rel_id,
        id_atributo_fk=attr_fk_id,
        id_atributo_referenciado=attr_ref_id,
    )

    assert referencia.on_delete == "NO_ACTION"
    assert referencia.on_update == "NO_ACTION"


def test_crear_referencia_fk_accion_invalida():
    ref_id = uuid4()
    rel_id = uuid4()
    attr_fk_id = uuid4()
    attr_ref_id = uuid4()

    with pytest.raises(AccionReferencialInvalidaException):
        ReferenciaFK.crear(
            id=ref_id,
            id_relacion=rel_id,
            id_atributo_fk=attr_fk_id,
            id_atributo_referenciado=attr_ref_id,
            on_delete="INVALID_ACTION",
        )


def test_actualizar_referencia_fk():
    ref_id = uuid4()
    rel_id = uuid4()
    attr_fk_id = uuid4()
    attr_ref_id = uuid4()
    nuevo_fk = uuid4()

    referencia = ReferenciaFK.crear(
        id=ref_id,
        id_relacion=rel_id,
        id_atributo_fk=attr_fk_id,
        id_atributo_referenciado=attr_ref_id,
    )

    referencia.actualizar(
        id_atributo_fk=nuevo_fk,
        on_delete=AccionReferencial.SET_NULL,
    )

    assert referencia.id_atributo_fk == nuevo_fk
    assert referencia.id_atributo_referenciado == attr_ref_id
    assert referencia.on_delete == "SET_NULL"
    assert referencia.on_update == "NO_ACTION"
