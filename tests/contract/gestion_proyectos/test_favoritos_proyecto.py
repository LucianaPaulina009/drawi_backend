from uuid import uuid4


def test_contrato_agregar_favorito_exitoso(client):
    client.post("/api/proyectos/crear")
    proyecto_id = client.get("/api/proyectos/listado").json()["items"][0]["id"]

    res_fav = client.post(f"/api/proyectos/{proyecto_id}/agregar_favorito")
    assert res_fav.status_code == 204
    assert res_fav.content == b""


def test_contrato_agregar_favorito_id_invalido(client):
    res = client.post("/api/proyectos/no-es-uuid/agregar_favorito")
    assert res.status_code == 422


def test_contrato_agregar_favorito_no_encontrado(client):
    random_id = uuid4()
    res = client.post(f"/api/proyectos/{random_id}/agregar_favorito")
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "PROYECTO_NO_ENCONTRADO"


def test_contrato_agregar_favorito_sin_autenticacion(unauthenticated_client):
    res = unauthenticated_client.post(f"/api/proyectos/{uuid4()}/agregar_favorito")
    assert res.status_code == 401


def test_contrato_desmarcar_favorito_exitoso(client):
    client.post("/api/proyectos/crear")
    proyecto_id = client.get("/api/proyectos/listado").json()["items"][0]["id"]
    client.post(f"/api/proyectos/{proyecto_id}/agregar_favorito")

    res_desmarcar = client.post(f"/api/proyectos/{proyecto_id}/desmarcar_favorito")
    assert res_desmarcar.status_code == 204
    assert res_desmarcar.content == b""


def test_contrato_desmarcar_favorito_id_invalido(client):
    res = client.post("/api/proyectos/invalido-uuid/desmarcar_favorito")
    assert res.status_code == 422


def test_contrato_desmarcar_favorito_no_encontrado(client):
    random_id = uuid4()
    res = client.post(f"/api/proyectos/{random_id}/desmarcar_favorito")
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "PROYECTO_NO_ENCONTRADO"


def test_contrato_listar_con_filtro_favoritos_true(client):
    res = client.get("/api/proyectos/listado?favoritos=true")
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    for item in data["items"]:
        assert item["es_favorito"] is True
