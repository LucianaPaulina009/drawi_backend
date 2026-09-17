import uuid
from app.core.security.auth import AuthUser, get_current_user
from app.main import app
from app.shared.infrastructure.db.better_auth import BetterAuthUser


def _crear_proyecto_diagrama_y_clase(client) -> tuple[str, str, str]:
    assert client.post("/api/proyectos/crear").status_code == 201
    proyecto_id = client.get("/api/proyectos/listado").json()["items"][0]["id"]
    diagrama_id = client.get(
        f"/api/proyectos/{proyecto_id}/diagramas"
    ).json()["items"][0]["id"]
    clase = client.post(
        f"/api/diagramas/{diagrama_id}/clases",
        json={"nombre": "Usuario", "posicion_x": 10, "posicion_y": 20, "ancho": 300},
    )
    assert clase.status_code == 201
    return proyecto_id, diagrama_id, clase.json()["id"]


def _crear_atributo(client, clase_id: str, nombre: str, **datos) -> dict:
    respuesta = client.post(
        f"/api/clases/{clase_id}/atributos",
        json={"tipo_dato": "varchar", "nombre": nombre, "longitud": 80, **datos},
    )
    assert respuesta.status_code == 201
    return respuesta.json()


def test_creacion_reordenamiento_y_detalle_compuesto(client):
    proyecto_id, diagrama_id, clase_id = _crear_proyecto_diagrama_y_clase(client)
    # Note: clase already has "id" at order 1
    primero = _crear_atributo(client, clase_id, "nombre")  # order 2
    segundo = _crear_atributo(client, clase_id, "correo")  # order 3

    respuesta = client.patch(
        f"/api/clases/{clase_id}/atributos/{segundo['id']}",
        json={"orden_de_posicion": 1},
    )
    coordenadas = client.patch(
        f"/api/diagramas/{diagrama_id}/clases/{clase_id}",
        json={"posicion_x": 45, "posicion_y": 60},
    )
    listado = client.get(f"/api/clases/{clase_id}/atributos")
    detalle = client.get(f"/api/proyectos/{proyecto_id}/diagramas/{diagrama_id}")

    assert respuesta.status_code == 200
    assert coordenadas.status_code == 200
    items = listado.json()["items"]
    assert items[0]["id"] == segundo["id"]
    assert items[0]["orden_de_posicion"] == 1
    assert [item["orden_de_posicion"] for item in items] == [1, 2, 3]
    assert [item["nombre"] for item in detalle.json()["clases"][0]["atributos"]][:2] == ["correo", "id"]
    assert (
        detalle.json()["clases"][0]["posicion_x"],
        detalle.json()["clases"][0]["posicion_y"],
    ) == (45, 60)


def test_creacion_con_uuid_personalizado_y_colision(client):
    _, _, clase_id = _crear_proyecto_diagrama_y_clase(client)
    custom_id = str(uuid.uuid4())

    attr = _crear_atributo(client, clase_id, "slug", id_atributo=custom_id)
    assert attr["id"] == custom_id

    # Colisión con el mismo UUID
    res_colision = client.post(
        f"/api/clases/{clase_id}/atributos",
        json={"id_atributo": custom_id, "tipo_dato": "varchar", "nombre": "slug2", "longitud": 50},
    )
    assert res_colision.status_code == 409


def test_actualizacion_parcial_limpia_configuracion_no_aplicable(client):
    _, _, clase_id = _crear_proyecto_diagrama_y_clase(client)
    atributo = _crear_atributo(client, clase_id, "codigo")

    respuesta = client.patch(
        f"/api/clases/{clase_id}/atributos/{atributo['id']}",
        json={"tipo_dato": "numeric", "precision": 12, "escala": 2},
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["longitud"] is None
    assert (respuesta.json()["precision"], respuesta.json()["escala"]) == (12, 2)


def test_eliminacion_logica_y_acceso_ajeno(client, usuario_secundario):
    _, _, clase_id = _crear_proyecto_diagrama_y_clase(client)
    atributo = _crear_atributo(client, clase_id, "correo")

    assert client.delete(f"/api/clases/{clase_id}/atributos/{atributo['id']}").status_code == 204
    # The initial 'id' attribute is still there
    items = client.get(f"/api/clases/{clase_id}/atributos").json()["items"]
    assert not any(i["id"] == atributo["id"] for i in items)
    assert len(items) == 1

    app.dependency_overrides[get_current_user] = lambda: usuario_secundario
    assert client.get(f"/api/clases/{clase_id}/atributos").status_code == 404


def test_rechaza_atributo_bajo_otra_clase_del_mismo_diagrama(client):
    _, diagrama_id, clase_id = _crear_proyecto_diagrama_y_clase(client)
    atributo = _crear_atributo(client, clase_id, "correo")
    segunda_clase = client.post(
        f"/api/diagramas/{diagrama_id}/clases",
        json={"nombre": "Perfil", "posicion_x": 50, "posicion_y": 50, "ancho": 250},
    )
    assert segunda_clase.status_code == 201

    respuesta = client.get(
        f"/api/clases/{segunda_clase.json()['id']}/atributos/{atributo['id']}"
    )

    assert respuesta.status_code == 404
    assert client.get(f"/api/clases/{clase_id}/atributos/{atributo['id']}").status_code == 200


def test_permisos_por_rol_para_mutaciones_atributo(
    client, session, usuario_autenticado: AuthUser, usuario_secundario: AuthUser
):
    session.add(BetterAuthUser(id=usuario_autenticado.user_id, name="Owner", email=usuario_autenticado.email, emailVerified=True))
    session.add(BetterAuthUser(id=usuario_secundario.user_id, name="Colab", email=usuario_secundario.email, emailVerified=True))
    session.commit()

    proyecto_id, diagrama_id, clase_id = _crear_proyecto_diagrama_y_clase(client)
    attr = _crear_atributo(client, clase_id, "titulo")

    # Invite and join as 'ver'
    inv_res = client.post(f"/api/proyectos/{proyecto_id}/invitacion")
    codigo = inv_res.json()["codigo_acceso"]
    app.dependency_overrides[get_current_user] = lambda: usuario_secundario
    client.post(f"/api/invitaciones/{codigo}/unirse")

    # Reader ('ver') can read, but gets 403 on mutate
    assert client.get(f"/api/clases/{clase_id}/atributos").status_code == 200
    res_crear = client.post(f"/api/clases/{clase_id}/atributos", json={"tipo_dato": "varchar", "nombre": "extra"})
    assert res_crear.status_code == 403
    res_patch = client.patch(f"/api/clases/{clase_id}/atributos/{attr['id']}", json={"nombre": "modificado"})
    assert res_patch.status_code == 403
    res_del = client.delete(f"/api/clases/{clase_id}/atributos/{attr['id']}")
    assert res_del.status_code == 403

    # Upgrade to editor
    app.dependency_overrides[get_current_user] = lambda: usuario_autenticado
    miembros = client.get(f"/api/proyectos/{proyecto_id}/miembros").json()["items"]
    colab_id = next(m["id"] for m in miembros if not m["es_propietario"])
    client.patch(f"/api/proyectos/{proyecto_id}/miembros/{colab_id}/rol", json={"rol": "editor"})

    # Editor can mutate
    app.dependency_overrides[get_current_user] = lambda: usuario_secundario
    res_crear_ed = client.post(f"/api/clases/{clase_id}/atributos", json={"tipo_dato": "varchar", "nombre": "extra"})
    assert res_crear_ed.status_code == 201
    res_patch_ed = client.patch(f"/api/clases/{clase_id}/atributos/{attr['id']}", json={"nombre": "modificado"})
    assert res_patch_ed.status_code == 200

