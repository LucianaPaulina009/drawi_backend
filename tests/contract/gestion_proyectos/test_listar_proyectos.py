from uuid import UUID


def test_contrato_listar_proyectos_autenticado_vacio(client):
    response = client.get("/api/proyectos/listado")

    assert response.status_code == 200
    data = response.json()

    assert "items" in data
    assert isinstance(data["items"], list)
    # Sin campos de paginación
    assert "page" not in data
    assert "limit" not in data
    assert "total" not in data


def test_contrato_listar_proyectos_autenticado_con_campos(client):
    # Crear un proyecto primero
    client.post("/api/proyectos/crear")

    response = client.get("/api/proyectos/listado")
    assert response.status_code == 200
    data = response.json()

    assert len(data["items"]) >= 1
    primer_item = data["items"][0]

    # Verificar los 7 campos obligatorios
    assert "id" in primer_item
    UUID(primer_item["id"])
    assert "nombre" in primer_item
    assert "color" in primer_item
    assert "icono" in primer_item
    assert "fecha_actualizacion" in primer_item
    assert "es_favorito" in primer_item
    assert isinstance(primer_item["es_favorito"], bool)
    assert "slug" in primer_item


def test_contrato_listar_proyectos_sin_autenticacion(unauthenticated_client):
    response = unauthenticated_client.get("/api/proyectos/listado")
    assert response.status_code == 401


def test_contrato_listar_proyectos_parametro_favoritos_invalido(client):
    response = client.get("/api/proyectos/listado?favoritos=invalido")
    assert response.status_code == 422
