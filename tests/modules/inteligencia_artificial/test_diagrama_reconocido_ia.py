from __future__ import annotations

import pytest
from pydantic import ValidationError
from app.modules.inteligencia_artificial.application.schemas.diagrama_reconocido_ia import (
    AtributoReconocidoIa,
    ClaseReconocidaIa,
    DiagramaReconocidoIa,
    RelacionReconocidaIa,
)


def test_schema_diagrama_reconocido_ia_valida_json_correcto():
    data = {
        "clases": [
            {
                "referencia_semantica": "ref_cliente",
                "nombre": "Cliente",
                "atributos": [
                    {
                        "nombre": "id",
                        "tipo_detectado": "integer",
                        "es_pk": True,
                        "es_fk": False,
                        "permite_nulo": False,
                    },
                    {
                        "nombre": "nombre",
                        "tipo_detectado": "varchar",
                        "es_pk": False,
                        "es_fk": False,
                        "permite_nulo": False,
                    },
                ],
                "posicion_relativa_x": 0.2,
                "posicion_relativa_y": 0.3,
            },
            {
                "referencia_semantica": "ref_pedido",
                "nombre": "Pedido",
                "atributos": [
                    {
                        "nombre": "id",
                        "tipo_detectado": "integer",
                        "es_pk": True,
                        "es_fk": False,
                        "permite_nulo": False,
                    },
                    {
                        "nombre": "id_cliente",
                        "tipo_detectado": "integer",
                        "es_pk": False,
                        "es_fk": True,
                        "permite_nulo": False,
                    },
                ],
                "posicion_relativa_x": 0.7,
                "posicion_relativa_y": 0.3,
            },
        ],
        "relaciones": [
            {
                "origen_ref": "ref_cliente",
                "destino_ref": "ref_pedido",
                "tipo": "asociacion",
                "cardinalidad_origen": "1",
                "cardinalidad_destino": "0..*",
                "nombre": "Realiza",
                "es_nm": False,
                "es_recursiva": False,
            }
        ],
        "advertencias": [],
    }

    diagrama = DiagramaReconocidoIa.model_validate(data)
    assert len(diagrama.clases) == 2
    assert diagrama.clases[0].nombre == "Cliente"
    assert diagrama.clases[0].atributos[0].es_pk is True
    assert len(diagrama.relaciones) == 1
    assert diagrama.relaciones[0].cardinalidad_destino == "0..*"


def test_schema_diagrama_reconocido_ia_con_defaults_y_listas_vacias():
    diagrama = DiagramaReconocidoIa()
    assert diagrama.clases == []
    assert diagrama.relaciones == []
    assert diagrama.advertencias == []


def test_schema_diagrama_reconocido_ia_falla_si_falta_campo_obligatorio():
    with pytest.raises(ValidationError):
        # Falta referencia_semantica en clase
        ClaseReconocidaIa.model_validate({"nombre": "Factura"})
