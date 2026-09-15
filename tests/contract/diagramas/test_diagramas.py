from uuid import UUID


def _crear_proyecto_y_obtener_id(client) -> UUID:
    assert client.post("/api/proyectos/crear").status_code == 201
    listado = client.get("/api/proyectos/listado")
    assert listado.status_code == 200
    return UUID(listado.json()["items"][0]["id"])


def test_contrato_endpoints_diagramas(client):
    proyecto_id = _crear_proyecto_y_obtener_id(client)

    listado = client.get(f"/api/proyectos/{proyecto_id}/diagramas")
    assert listado.status_code == 200
    assert listado.json()["items"][0]["numero"] == 1

    creado = client.post(f"/api/proyectos/{proyecto_id}/diagramas", json={})
    assert creado.status_code == 201
    diagrama = creado.json()
    assert diagrama["nombre"] == "Página 2"
    assert diagrama["numero"] == 2

    detalle = client.get(f"/api/proyectos/{proyecto_id}/diagramas/{diagrama['id']}")
    assert detalle.status_code == 200
    assert detalle.json()["clases"] == []

    actualizado = client.patch(
        f"/api/proyectos/{proyecto_id}/diagramas/{diagrama['id']}",
        json={"nombre": "Modelo ventas"},
    )
    assert actualizado.status_code == 200
    assert actualizado.json()["nombre"] == "Modelo ventas"

    eliminado = client.delete(f"/api/proyectos/{proyecto_id}/diagramas/{diagrama['id']}")
    assert eliminado.status_code == 204


def test_contrato_diagramas_sin_autenticacion(unauthenticated_client):
    response = unauthenticated_client.get(f"/api/proyectos/{UUID(int=1)}/diagramas")
    assert response.status_code == 401
