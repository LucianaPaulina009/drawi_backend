import uuid


def _crear_diagrama(client) -> tuple[str, str]:
    assert client.post("/api/proyectos/crear").status_code == 201
    proyecto_id = client.get("/api/proyectos/listado").json()["items"][0]["id"]
    diagrama_id = client.get(
        f"/api/proyectos/{proyecto_id}/diagramas"
    ).json()["items"][0]["id"]
    return proyecto_id, diagrama_id


def test_contrato_endpoints_relaciones(client):
    _, diagrama_id = _crear_diagrama(client)

    c1 = client.post(
        f"/api/diagramas/{diagrama_id}/clases",
        json={"nombre": "Usuario", "posicion_x": 100, "posicion_y": 100, "ancho": 280},
    ).json()
    c2 = client.post(
        f"/api/diagramas/{diagrama_id}/clases",
        json={"nombre": "Perfil", "posicion_x": 400, "posicion_y": 100, "ancho": 280},
    ).json()

    rel_id = str(uuid.uuid4())
    ref_id = str(uuid.uuid4())
    attr_fk_id = str(uuid.uuid4())
    pk_c2 = c2["atributos"][0]["id"]
    creado = client.post(
        f"/api/diagramas/{diagrama_id}/relaciones",
        json={
            "id_relacion": rel_id,
            "id_clase_origen": c1["id"],
            "id_clase_destino": c2["id"],
            "tipo_relacion": "dependencia",
            "cardinalidad_origen": "1",
            "cardinalidad_destino": "1",
            "conector_origen": "right",
            "conector_destino": "left",
            "materializacion_fk": [
                {
                    "id_referencia_fk": ref_id,
                    "id_clase_fk": c1["id"],
                    "id_atributo_referenciado": pk_c2,
                    "atributo_fk_nuevo": {
                        "id_atributo": attr_fk_id,
                        "nombre": "perfil_id",
                        "tipo_dato": "integer",
                        "permite_nulo": False,
                        "es_unico": True,
                    },
                    "on_delete": "RESTRICT",
                    "on_update": "RESTRICT",
                }
            ],
        },
    )
    assert creado.status_code == 201
    rel = creado.json()
    assert rel["id"] == rel_id
    assert rel["id_diagrama"] == diagrama_id
    assert rel["id_clase_origen"] == c1["id"]
    assert rel["id_clase_destino"] == c2["id"]
    assert rel["tipo_relacion"] == "dependencia"
    assert rel["cardinalidad_origen"] == "1"
    assert rel["cardinalidad_destino"] == "1"
    assert rel["conector_origen"] == "right"
    assert rel["conector_destino"] == "left"
    assert len(rel["referencias_fk"]) == 1
    assert rel["referencias_fk"][0]["id"] == ref_id

    listado = client.get(f"/api/diagramas/{diagrama_id}/relaciones")
    assert listado.status_code == 200
    assert listado.json()["items"][0]["id"] == rel_id

    detalle = client.get(f"/api/diagramas/{diagrama_id}/relaciones/{rel_id}")
    assert detalle.status_code == 200
    assert detalle.json()["id"] == rel_id
    assert len(detalle.json()["referencias_fk"]) == 1
    assert detalle.json()["referencias_fk"][0]["id"] == ref_id

    actualizado_invalido = client.patch(
        f"/api/diagramas/{diagrama_id}/relaciones/{rel_id}",
        json={"cardinalidad_destino": "0..1"},
    )
    assert actualizado_invalido.status_code in (400, 422)

    eliminado = client.delete(f"/api/diagramas/{diagrama_id}/relaciones/{rel_id}")
    assert eliminado.status_code == 204
    assert client.get(f"/api/diagramas/{diagrama_id}/relaciones/{rel_id}").status_code == 404


def test_contrato_relaciones_sin_autenticacion(unauthenticated_client):
    response = unauthenticated_client.get(
        f"/api/diagramas/{uuid.uuid4()}/relaciones"
    )
    assert response.status_code == 401
