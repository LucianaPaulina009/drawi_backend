from types import SimpleNamespace
from uuid import uuid4

from app.modules.diagramas.application.services.geometria_conectores import (
    calcular_mejores_conectores,
)


def test_conectores_horizontal_a_izquierda_b_derecha():
    clase_a = SimpleNamespace(id=uuid4(), posicion_x=100.0, posicion_y=200.0, ancho=220.0)
    clase_b = SimpleNamespace(id=uuid4(), posicion_x=600.0, posicion_y=200.0, ancho=220.0)

    con_a, con_b = calcular_mejores_conectores(clase_a, clase_b)

    assert con_a in ("right-center", "right")
    assert con_b in ("left-center", "left")


def test_conectores_horizontal_a_derecha_b_izquierda():
    clase_a = SimpleNamespace(id=uuid4(), posicion_x=700.0, posicion_y=150.0, ancho=220.0)
    clase_b = SimpleNamespace(id=uuid4(), posicion_x=100.0, posicion_y=150.0, ancho=220.0)

    con_a, con_b = calcular_mejores_conectores(clase_a, clase_b)

    assert con_a in ("left-center", "left")
    assert con_b in ("right-center", "right")


def test_conectores_vertical_a_arriba_b_abajo():
    clase_a = SimpleNamespace(id=uuid4(), posicion_x=200.0, posicion_y=50.0, ancho=220.0)
    clase_b = SimpleNamespace(id=uuid4(), posicion_x=200.0, posicion_y=500.0, ancho=220.0)

    con_a, con_b = calcular_mejores_conectores(clase_a, clase_b)

    assert con_a in ("bottom-center", "bottom")
    assert con_b in ("top-center", "top")


def test_conectores_vertical_a_abajo_b_arriba():
    clase_a = SimpleNamespace(id=uuid4(), posicion_x=200.0, posicion_y=600.0, ancho=220.0)
    clase_b = SimpleNamespace(id=uuid4(), posicion_x=200.0, posicion_y=100.0, ancho=220.0)

    con_a, con_b = calcular_mejores_conectores(clase_a, clase_b)

    assert con_a in ("top-center", "top")
    assert con_b in ("bottom-center", "bottom")


def test_conectores_recursivo():
    id_comun = uuid4()
    clase_a = SimpleNamespace(id=id_comun, posicion_x=100.0, posicion_y=100.0, ancho=220.0)
    clase_b = SimpleNamespace(id=id_comun, posicion_x=100.0, posicion_y=100.0, ancho=220.0)

    con_a, con_b = calcular_mejores_conectores(clase_a, clase_b)

    assert con_a.startswith("right")
    assert con_b.startswith("top")


def test_conectores_evita_puertos_ocupados():
    id_a = uuid4()
    id_b = uuid4()
    clase_a = SimpleNamespace(id=id_a, posicion_x=100.0, posicion_y=200.0, ancho=220.0)
    clase_b = SimpleNamespace(id=id_b, posicion_x=600.0, posicion_y=200.0, ancho=220.0)

    # Simular que right-center de clase A ya está ocupado por otra relación
    rel_existente = SimpleNamespace(
        id_clase_origen=id_a,
        conector_origen="right-center",
        id_clase_destino=uuid4(),
        conector_destino="left-center",
    )

    con_a, con_b = calcular_mejores_conectores(
        clase_a, clase_b, relaciones_existentes=[rel_existente]
    )

    # Debe escoger un sub-handle libre en el lado derecho (p. ej. right-top o right-bottom)
    assert con_a in ("right-top", "right-bottom")
    assert con_b in ("left-center", "left")
