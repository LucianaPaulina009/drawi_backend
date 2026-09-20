import uuid


def _crear_diagrama_clases_y_relacion(client) -> tuple[str, str, dict, dict, dict, str]:
    assert client.post("/api/proyectos/crear").status_code == 201
    proyecto_id = client.get("/api/proyectos/listado").json()["items"][0]["id"]
    diagrama_id = client.get(
        f"/api/proyectos/{proyecto_id}/diagramas"
    ).json()["items"][0]["id"]

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
    fk_attr_id = str(uuid.uuid4())
    pk_c2 = c2["atributos"][0]["id"]

    rel = client.post(
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
                    "id_atributo_referenciado": pk_c2,
                    "id_clase_fk": c1["id"],
                    "atributo_fk_nuevo": {
                        "id_atributo": fk_attr_id,
                        "nombre": "id_perfil",
                        "tipo_dato": "integer",
                        "permite_nulo": False,
                        "es_unico": True,
                    },
                    "on_delete": "CASCADE",
                    "on_update": "RESTRICT",
                }
            ],
        },
    ).json()

    return proyecto_id, diagrama_id, c1, c2, rel, ref_id


def test_contrato_endpoints_referencias_fk(client):
    _, _, c1, c2, rel, ref_id = _crear_diagrama_clases_y_relacion(client)

    listado = client.get(f"/api/relaciones/{rel['id']}/referencias-fk")
    assert listado.status_code == 200
    assert listado.json()["items"][0]["id"] == ref_id

    detalle = client.get(f"/api/relaciones/{rel['id']}/referencias-fk/{ref_id}")
    assert detalle.status_code == 200
    assert detalle.json()["id"] == ref_id
    assert detalle.json()["on_delete"] == "CASCADE"

    # Actualizar acción referencial debe ser rechazado por ser inmutable
    actualizado = client.patch(
        f"/api/relaciones/{rel['id']}/referencias-fk/{ref_id}",
        json={"on_delete": "SET_NULL"},
    )
    assert actualizado.status_code in (400, 422)

    eliminado = client.delete(f"/api/relaciones/{rel['id']}/referencias-fk/{ref_id}")
    assert eliminado.status_code == 204
    assert client.get(f"/api/relaciones/{rel['id']}/referencias-fk/{ref_id}").status_code == 404


def test_contrato_referencias_fk_sin_autenticacion(unauthenticated_client):
    response = unauthenticated_client.get(
        f"/api/relaciones/{uuid.uuid4()}/referencias-fk"
    )
    assert response.status_code == 401
