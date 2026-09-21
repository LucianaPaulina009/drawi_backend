from uuid import uuid4
import pytest

from app.modules.inteligencia_artificial.application.services.planificador_acciones_ia import (
    PlanificadorAccionesIa,
)
from app.modules.inteligencia_artificial.application.services.validador_respuesta_ia import (
    AccionCrearAtributoSchema,
    AccionCrearClaseSchema,
    AccionCrearRelacionSchema,
)
from app.modules.inteligencia_artificial.domain.exceptions import PlanIaInvalidoException


def test_planificador_ordena_clases_atributos_relaciones():
    acciones = [
        AccionCrearRelacionSchema(
            clase_origen_referencia="a",
            clase_destino_referencia="b",
            nombre="R",
        ),
        AccionCrearAtributoSchema(
            clase_referencia="a",
            nombre="nombre",
        ),
        AccionCrearClaseSchema(
            referencia="b",
            nombre="B",
        ),
        AccionCrearClaseSchema(
            referencia="a",
            nombre="A",
        ),
    ]

    ordenadas = PlanificadorAccionesIa.planificar(acciones)

    assert isinstance(ordenadas[0], AccionCrearClaseSchema)
    assert isinstance(ordenadas[1], AccionCrearClaseSchema)
    assert isinstance(ordenadas[2], AccionCrearAtributoSchema)
    assert isinstance(ordenadas[3], AccionCrearRelacionSchema)


def test_planificador_falla_si_atributo_referencia_clase_inexistente():
    acciones = [
        AccionCrearAtributoSchema(
            clase_referencia="desconocida",
            nombre="campo",
        )
    ]
    with pytest.raises(PlanIaInvalidoException):
        PlanificadorAccionesIa.planificar(acciones)


def test_planificador_falla_si_relacion_referencia_origen_inexistente():
    acciones = [
        AccionCrearClaseSchema(referencia="a", nombre="A"),
        AccionCrearRelacionSchema(
            clase_origen_referencia="a",
            clase_destino_referencia="no_existe",
        ),
    ]
    with pytest.raises(PlanIaInvalidoException):
        PlanificadorAccionesIa.planificar(acciones)


def test_planificador_acepta_clases_existentes_del_diagrama():
    id_existente = uuid4()
    clases_existentes = {"usuario": id_existente}

    acciones = [
        AccionCrearAtributoSchema(
            clase_referencia="usuario",
            nombre="telefono",
        )
    ]

    ordenadas = PlanificadorAccionesIa.planificar(acciones, clases_existentes=clases_existentes)
    assert len(ordenadas) == 1
    assert ordenadas[0].nombre == "telefono"
