def _crear_diagrama(client) -> tuple[str, str]:
    assert client.post("/api/proyectos/crear").status_code == 201
    proyecto_id = client.get("/api/proyectos/listado").json()["items"][0]["id"]
    diagrama_id = client.get(
        f"/api/proyectos/{proyecto_id}/diagramas"
    ).json()["items"][0]["id"]
    return proyecto_id, diagrama_id


def test_contrato_endpoints_clases(client):
    proyecto_id, diagrama_id = _crear_diagrama(client)

    creado = client.post(
        f"/api/diagramas/{diagrama_id}/clases",
        json={"nombre": "Usuario", "posicion_x": 120, "posicion_y": 80, "ancho": 260},
    )
    assert creado.status_code == 201
    clase = creado.json()
    assert clase["id_diagrama"] == diagrama_id

    listado = client.get(f"/api/diagramas/{diagrama_id}/clases")
    assert listado.status_code == 200
    assert listado.json()["items"][0]["id"] == clase["id"]

    detalle = client.get(f"/api/diagramas/{diagrama_id}/clases/{clase['id']}")
    assert detalle.status_code == 200
    assert detalle.json()["atributos"] == []

    actualizado = client.patch(
        f"/api/diagramas/{diagrama_id}/clases/{clase['id']}",
        json={"posicion_x": 240},
    )
    assert actualizado.status_code == 200
    assert actualizado.json()["posicion_x"] == 240
    assert actualizado.json()["ancho"] == 260

    eliminado = client.delete(f"/api/diagramas/{diagrama_id}/clases/{clase['id']}")
    assert eliminado.status_code == 204
    assert client.get(f"/api/diagramas/{diagrama_id}/clases/{clase['id']}").status_code == 404


def test_contrato_clases_sin_autenticacion(unauthenticated_client):
    response = unauthenticated_client.get("/api/diagramas/00000000-0000-0000-0000-000000000001/clases")
    assert response.status_code == 401
