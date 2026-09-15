from uuid import uuid4


def test_contrato_actualizar_proyecto_exitoso(client):
    client.post("/api/proyectos/crear")
    proyecto_id = client.get("/api/proyectos/listado").json()["items"][0]["id"]

    res_patch = client.patch(
        f"/api/proyectos/{proyecto_id}/actualizar",
        json={"nombre": "Plan trimestral", "color": "verde", "icono": "estrella"},
    )
    assert res_patch.status_code == 204
    assert res_patch.content == b""


def test_contrato_actualizar_proyecto_cuerpo_vacio_400(client):
    client.post("/api/proyectos/crear")
    proyecto_id = client.get("/api/proyectos/listado").json()["items"][0]["id"]

    res_patch = client.patch(
        f"/api/proyectos/{proyecto_id}/actualizar",
        json={},
    )
    assert res_patch.status_code == 400
    assert res_patch.json()["error"]["code"] == "ACTUALIZACION_PROYECTO_VACIA"


def test_contrato_actualizar_proyecto_nombre_invalido_400(client):
    client.post("/api/proyectos/crear")
    proyecto_id = client.get("/api/proyectos/listado").json()["items"][0]["id"]

    res_patch = client.patch(
        f"/api/proyectos/{proyecto_id}/actualizar",
        json={"nombre": "   "},
    )
    assert res_patch.status_code == 400
    assert res_patch.json()["error"]["code"] == "NOMBRE_PROYECTO_INVALIDO"


def test_contrato_actualizar_proyecto_no_encontrado_404(client):
    random_id = uuid4()
    res_patch = client.patch(
        f"/api/proyectos/{random_id}/actualizar",
        json={"color": "azul"},
    )
    assert res_patch.status_code == 404
    assert res_patch.json()["error"]["code"] == "PROYECTO_NO_ENCONTRADO"


def test_contrato_actualizar_proyecto_uuid_invalido_422(client):
    res = client.patch(
        "/api/proyectos/no-uuid/actualizar",
        json={"color": "azul"},
    )
    assert res.status_code == 422


def test_contrato_actualizar_proyecto_enum_invalido_422(client):
    client.post("/api/proyectos/crear")
    proyecto_id = client.get("/api/proyectos/listado").json()["items"][0]["id"]

    res = client.patch(
        f"/api/proyectos/{proyecto_id}/actualizar",
        json={"color": "color_inexistente"},
    )
    assert res.status_code == 422


def test_contrato_actualizar_proyecto_sin_autenticacion(unauthenticated_client):
    res = unauthenticated_client.patch(
        f"/api/proyectos/{uuid4()}/actualizar",
        json={"color": "azul"},
    )
    assert res.status_code == 401


def test_contrato_eliminar_proyecto_exitoso(client):
    client.post("/api/proyectos/crear")
    proyecto_id = client.get("/api/proyectos/listado").json()["items"][0]["id"]

    res_del = client.delete(f"/api/proyectos/{proyecto_id}/eliminar")
    assert res_del.status_code == 204
    assert res_del.content == b""


def test_contrato_eliminar_proyecto_no_encontrado_404(client):
    random_id = uuid4()
    res = client.delete(f"/api/proyectos/{random_id}/eliminar")
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "PROYECTO_NO_ENCONTRADO"


def test_contrato_eliminar_proyecto_uuid_invalido_422(client):
    res = client.delete("/api/proyectos/no-uuid/eliminar")
    assert res.status_code == 422


def test_contrato_eliminar_proyecto_sin_autenticacion(unauthenticated_client):
    res = unauthenticated_client.delete(f"/api/proyectos/{uuid4()}/eliminar")
    assert res.status_code == 401
