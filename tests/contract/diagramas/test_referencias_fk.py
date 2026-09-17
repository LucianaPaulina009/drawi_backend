import uuid


def _crear_diagrama_clases_y_relacion(client) -> tuple[str, str, dict, dict, dict]:
    assert client.post("/api/proyectos/crear").status_code == 201
    proyecto_id = client.get("/api/proyectos/listado").json()["items"][0]["id"]
    diagrama_id = client.get(
        f"/api/proyectos/{proyecto_id}/diagramas"
    ).json()["items"][0]["id"]

    c1 = client.post(
        f"/api/diagramas/{diagrama_id}/clases",
        json={"nombre": "Usuario", "posicion_x": 100, "posicion_y": 100, "ancho": 280},
    ).json()
    a1 = client.post(
        f"/api/clases/{c1['id']}/atributos",
        json={
            "tipo_dato": "integer",
            "nombre": "id",
            "es_llave_primaria": True,
            "permite_nulo": False,
            "es_unico": True,
            "orden_de_posicion": 1,
        },
    ).json()

    c2 = client.post(
        f"/api/diagramas/{diagrama_id}/clases",
        json={"nombre": "Perfil", "posicion_x": 400, "posicion_y": 100, "ancho": 280},
    ).json()
    a2 = client.post(
        f"/api/clases/{c2['id']}/atributos",
        json={
            "tipo_dato": "integer",
            "nombre": "usuario_id",
            "es_llave_primaria": False,
            "permite_nulo": True,
            "es_unico": False,
            "orden_de_posicion": 1,
        },
    ).json()

    rel_id = str(uuid.uuid4())
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
        },
    ).json()

    return proyecto_id, diagrama_id, c1, c2, rel


def test_contrato_endpoints_referencias_fk(client):
    _, _, c1, c2, rel = _crear_diagrama_clases_y_relacion(client)
    attrs_c1 = client.get(f"/api/clases/{c1['id']}/atributos").json()["items"]
    attrs_c2 = client.get(f"/api/clases/{c2['id']}/atributos").json()["items"]
    attr_ref = attrs_c1[0]
    attr_fk = attrs_c2[0]

    ref_id = str(uuid.uuid4())
    creado = client.post(
        f"/api/relaciones/{rel['id']}/referencias-fk",
        json={
            "id_referencia_fk": ref_id,
            "id_atributo_fk": attr_fk["id"],
            "id_atributo_referenciado": attr_ref["id"],
            "on_delete": "CASCADE",
            "on_update": "RESTRICT",
        },
    )
    assert creado.status_code == 201
    rfk = creado.json()
    assert rfk["id"] == ref_id
    assert rfk["id_relacion"] == rel["id"]
    assert rfk["id_atributo_fk"] == attr_fk["id"]
    assert rfk["id_atributo_referenciado"] == attr_ref["id"]
    assert rfk["on_delete"] == "CASCADE"
    assert rfk["on_update"] == "RESTRICT"

    listado = client.get(f"/api/relaciones/{rel['id']}/referencias-fk")
    assert listado.status_code == 200
    assert listado.json()["items"][0]["id"] == ref_id

    detalle = client.get(f"/api/relaciones/{rel['id']}/referencias-fk/{ref_id}")
    assert detalle.status_code == 200
    assert detalle.json()["id"] == ref_id

    actualizado = client.patch(
        f"/api/relaciones/{rel['id']}/referencias-fk/{ref_id}",
        json={"on_delete": "SET_NULL"},
    )
    assert actualizado.status_code == 200
    assert actualizado.json()["on_delete"] == "SET_NULL"

    eliminado = client.delete(f"/api/relaciones/{rel['id']}/referencias-fk/{ref_id}")
    assert eliminado.status_code == 204
    assert client.get(f"/api/relaciones/{rel['id']}/referencias-fk/{ref_id}").status_code == 404


def test_contrato_referencias_fk_sin_autenticacion(unauthenticated_client):
    response = unauthenticated_client.get(
        f"/api/relaciones/{uuid.uuid4()}/referencias-fk"
    )
    assert response.status_code == 401
