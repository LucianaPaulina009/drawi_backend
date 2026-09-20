from uuid import uuid4
import pytest


def _crear_diagrama(client) -> tuple[str, str]:
    assert client.post("/api/proyectos/crear").status_code == 201
    proyecto_id = client.get("/api/proyectos/listado").json()["items"][0]["id"]
    diagrama_id = client.get(
        f"/api/proyectos/{proyecto_id}/diagramas"
    ).json()["items"][0]["id"]
    return proyecto_id, diagrama_id


def test_invariante_pk_protegida(client):
    _, diagrama_id = _crear_diagrama(client)
    res = client.post(
        f"/api/diagramas/{diagrama_id}/clases",
        json={"nombre": "Orden", "posicion_x": 100, "posicion_y": 100, "ancho": 200},
    )
    assert res.status_code == 201
    clase = res.json()
    pk_attr = clase["atributos"][0]
    assert pk_attr["es_llave_primaria"] is True

    # Intento de eliminar directamente la PK inicial debe ser rechazado
    del_res = client.delete(
        f"/api/clases/{clase['id']}/atributos/{pk_attr['id']}"
    )
    assert del_res.status_code in (400, 422)

    # Intento de crear una segunda PK en la misma clase debe ser rechazado
    segunda_pk = client.post(
        f"/api/clases/{clase['id']}/atributos",
        json={
            "nombre": "codigo_alt",
            "tipo_dato": "varchar",
            "es_llave_primaria": True,
            "permite_nulo": False,
            "es_unico": True,
            "orden_de_posicion": 2,
        },
    )
    assert segunda_pk.status_code in (400, 422)

    # Renombrar la PK inicial es permitido
    renombrar_pk = client.patch(
        f"/api/clases/{clase['id']}/atributos/{pk_attr['id']}",
        json={"nombre": "id_orden"},
    )
    assert renombrar_pk.status_code == 200
    assert renombrar_pk.json()["nombre"] == "id_orden"


def test_invariante_relaciones_inmutables(client):
    _, diagrama_id = _crear_diagrama(client)
    c1 = client.post(
        f"/api/diagramas/{diagrama_id}/clases",
        json={"nombre": "A", "posicion_x": 0, "posicion_y": 0, "ancho": 200},
    ).json()
    c2 = client.post(
        f"/api/diagramas/{diagrama_id}/clases",
        json={"nombre": "B", "posicion_x": 300, "posicion_y": 0, "ancho": 200},
    ).json()

    pk_b = c2["atributos"][0]["id"]
    fk_attr_id = str(uuid4())
    rel_id = str(uuid4())
    ref_fk_id = str(uuid4())

    rel_res = client.post(
        f"/api/diagramas/{diagrama_id}/relaciones",
        json={
            "id_relacion": rel_id,
            "id_clase_origen": c1["id"],
            "id_clase_destino": c2["id"],
            "tipo_relacion": "asociacion",
            "cardinalidad_origen": "0..*",
            "cardinalidad_destino": "1",
            "conector_origen": "right",
            "conector_destino": "left",
            "materializacion_fk": [
                {
                    "id_referencia_fk": ref_fk_id,
                    "id_atributo_referenciado": pk_b,
                    "id_clase_fk": c1["id"],
                    "atributo_fk_nuevo": {
                        "id_atributo": fk_attr_id,
                        "nombre": "id_b",
                        "tipo_dato": "integer",
                        "permite_nulo": True,
                        "es_unico": False,
                    },
                }
            ],
        },
    )
    assert rel_res.status_code == 201

    # No se permite alterar cardinalidades o conectores una vez creada la relación
    patch_rel = client.patch(
        f"/api/diagramas/{diagrama_id}/relaciones/{rel_id}",
        json={"cardinalidad_origen": "1", "cardinalidad_destino": "1"},
    )
    assert patch_rel.status_code in (400, 422)
