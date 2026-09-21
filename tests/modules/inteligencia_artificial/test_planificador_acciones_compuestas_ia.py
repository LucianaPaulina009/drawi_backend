from uuid import uuid4
import pytest

from app.modules.inteligencia_artificial.application.services.planificador_acciones_ia import (
    PlanificadorAccionesIa,
)
from app.modules.inteligencia_artificial.application.services.validador_respuesta_ia import (
    AccionActualizarAtributoSchema,
    AccionActualizarClaseSchema,
    AccionCrearAtributoSchema,
    AccionCrearClaseSchema,
    AccionCrearRelacionSchema,
    AccionEliminarAtributoSchema,
    AccionEliminarClaseSchema,
    AccionEliminarRelacionSchema,
)
from app.modules.inteligencia_artificial.domain.exceptions import PlanIaInvalidoException


def test_planificador_ordena_creaciones_clase_atributo_relacion():
    acciones = [
        AccionCrearRelacionSchema(
            clase_origen_referencia="cliente",
            clase_destino_referencia="pedido",
            nombre="cliente_pedido",
        ),
        AccionCrearAtributoSchema(
            clase_referencia="cliente",
            nombre="email",
            tipo_dato="varchar",
        ),
        AccionCrearClaseSchema(
            referencia="pedido",
            nombre="Pedido",
        ),
        AccionCrearClaseSchema(
            referencia="cliente",
            nombre="Cliente",
        ),
    ]

    ordenadas = PlanificadorAccionesIa.planificar(acciones)
    assert len(ordenadas) == 4
    # Primeras 2 deben ser clases
    assert isinstance(ordenadas[0], AccionCrearClaseSchema)
    assert isinstance(ordenadas[1], AccionCrearClaseSchema)
    # Tercera debe ser atributo
    assert isinstance(ordenadas[2], AccionCrearAtributoSchema)
    # Cuarta debe ser relación
    assert isinstance(ordenadas[3], AccionCrearRelacionSchema)


def test_planificador_rechaza_referencia_a_clase_desconocida():
    acciones = [
        AccionActualizarAtributoSchema(
            clase_referencia="Inexistente",
            atributo_referencia="telefono",
            nuevo_nombre="celular",
        )
    ]
    with pytest.raises(PlanIaInvalidoException):
        PlanificadorAccionesIa.planificar(acciones, clases_existentes={})


def test_planificador_admite_clases_existentes():
    c_id = uuid4()
    clases_existentes = {"cliente": c_id}

    acciones = [
        AccionActualizarClaseSchema(
            clase_referencia="cliente",
            nuevo_nombre="ClienteVIP",
        ),
        AccionEliminarAtributoSchema(
            clase_referencia="cliente",
            atributo_referencia="fax",
        ),
    ]

    ordenadas = PlanificadorAccionesIa.planificar(acciones, clases_existentes=clases_existentes)
    assert len(ordenadas) == 2
