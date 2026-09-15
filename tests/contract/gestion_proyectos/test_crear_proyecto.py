def test_contrato_crear_proyecto_autenticado(client):
    response = client.post("/api/proyectos/crear")

    assert response.status_code == 201
    data = response.json()

    # El contrato de creación ahora expone exclusivamente el slug
    assert "slug" in data
    assert data["slug"] == "nuevo-proyecto-0"
    assert "id" not in data
    assert "nombre" not in data
    assert "color" not in data


def test_contrato_crear_proyecto_sin_autenticacion(unauthenticated_client):
    response = unauthenticated_client.post("/api/proyectos/crear")
    assert response.status_code == 401
