import uuid
from app.core.security.auth import AuthUser, get_current_user
from app.main import app
from app.shared.infrastructure.db.better_auth import BetterAuthUser


def _crear_proyecto_y_diagrama(client) -> tuple[str, str]:
    assert client.post("/api/proyectos/crear").status_code == 201
    proyecto_id = client.get("/api/proyectos/listado").json()["items"][0]["id"]
    diagrama_id = client.get(
        f"/api/proyectos/{proyecto_id}/diagramas"
    ).json()["items"][0]["id"]
    return proyecto_id, diagrama_id


def _crear_clase(client, diagrama_id: str, **kwargs) -> dict:
    payload = {"nombre": "Usuario", "posicion_x": 10, "posicion_y": 20, "ancho": 300, **kwargs}
    response = client.post(
        f"/api/diagramas/{diagrama_id}/clases",
        json=payload,
    )
    assert response.status_code == 201
    return response.json()


def test_actualiza_coordenadas_y_detalle_diagrama_incluye_clases(client):
    proyecto_id, diagrama_id = _crear_proyecto_y_diagrama(client)
    clase = _crear_clase(client, diagrama_id)

    respuesta = client.patch(
        f"/api/diagramas/{diagrama_id}/clases/{clase['id']}",
        json={"posicion_x": 99, "posicion_y": 101},
    )
    detalle_diagrama = client.get(f"/api/proyectos/{proyecto_id}/diagramas/{diagrama_id}")

    assert respuesta.status_code == 200
    assert detalle_diagrama.status_code == 200
    clase_detalle = detalle_diagrama.json()["clases"][0]
    assert (clase_detalle["posicion_x"], clase_detalle["posicion_y"], clase_detalle["ancho"]) == (99, 101, 300)
    assert len(clase_detalle["atributos"]) == 1
    assert clase_detalle["atributos"][0]["nombre"] == "id"
    assert clase_detalle["atributos"][0]["tipo_dato"] == "integer"
    assert clase_detalle["atributos"][0]["es_llave_primaria"] is True


def test_creacion_con_uuids_personalizados_y_defaults(client):
    _, diagrama_id = _crear_proyecto_y_diagrama(client)
    custom_class_id = str(uuid.uuid4())
    custom_attr_id = str(uuid.uuid4())

    res = client.post(
        f"/api/diagramas/{diagrama_id}/clases",
        json={
            "id_clase": custom_class_id,
            "id_atributo_inicial": custom_attr_id,
            "posicion_x": 50,
            "posicion_y": 50,
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["id"] == custom_class_id
    assert data["nombre"] == "Tabla"
    assert data["ancho"] == 280.0
    assert len(data["atributos"]) == 1
    assert data["atributos"][0]["id"] == custom_attr_id
    assert data["atributos"][0]["nombre"] == "id"


def test_rechaza_colision_uuid_en_creacion_clase(client):
    _, diagrama_id = _crear_proyecto_y_diagrama(client)
    custom_class_id = str(uuid.uuid4())
    custom_attr_id = str(uuid.uuid4())

    res1 = client.post(
        f"/api/diagramas/{diagrama_id}/clases",
        json={
            "id_clase": custom_class_id,
            "id_atributo_inicial": custom_attr_id,
            "posicion_x": 0,
            "posicion_y": 0,
        },
    )
    assert res1.status_code == 201

    # Colisión de id_clase
    res2 = client.post(
        f"/api/diagramas/{diagrama_id}/clases",
        json={
            "id_clase": custom_class_id,
            "id_atributo_inicial": str(uuid.uuid4()),
            "posicion_x": 10,
            "posicion_y": 10,
        },
    )
    assert res2.status_code == 409


def test_rechaza_clase_bajo_diagrama_distinto(client):
    _, diagrama_id = _crear_proyecto_y_diagrama(client)
    clase = _crear_clase(client, diagrama_id)
    segundo_diagrama = client.post(
        f"/api/proyectos/{client.get('/api/proyectos/listado').json()['items'][0]['id']}/diagramas",
        json={"nombre": "Otra página"},
    ).json()

    response = client.get(f"/api/diagramas/{segundo_diagrama['id']}/clases/{clase['id']}")

    assert response.status_code == 404


def test_eliminacion_logica_y_acceso_ajeno(client, usuario_secundario):
    _, diagrama_id = _crear_proyecto_y_diagrama(client)
    clase = _crear_clase(client, diagrama_id)

    assert client.delete(f"/api/diagramas/{diagrama_id}/clases/{clase['id']}").status_code == 204
    assert client.get(f"/api/diagramas/{diagrama_id}/clases").json()["items"] == []

    app.dependency_overrides[get_current_user] = lambda: usuario_secundario
    assert client.get(f"/api/diagramas/{diagrama_id}/clases").status_code == 404


def test_permisos_por_rol_para_mutaciones_clase(
    client, session, usuario_autenticado: AuthUser, usuario_secundario: AuthUser
):
    # Setup users in db
    session.add(BetterAuthUser(id=usuario_autenticado.user_id, name="Owner", email=usuario_autenticado.email, emailVerified=True))
    session.add(BetterAuthUser(id=usuario_secundario.user_id, name="Colab", email=usuario_secundario.email, emailVerified=True))
    session.commit()

    # Owner creates project & diagram & class
    proyecto_id, diagrama_id = _crear_proyecto_y_diagrama(client)
    clase = _crear_clase(client, diagrama_id)

    # Owner invites secondary user
    inv_res = client.post(f"/api/proyectos/{proyecto_id}/invitacion")
    codigo = inv_res.json()["codigo_acceso"]

    # Secondary user joins (default role: 'ver')
    app.dependency_overrides[get_current_user] = lambda: usuario_secundario
    client.post(f"/api/invitaciones/{codigo}/unirse")

    # Reader ('ver') can read, but gets 403 on mutate
    assert client.get(f"/api/diagramas/{diagrama_id}/clases").status_code == 200
    res_crear = client.post(f"/api/diagramas/{diagrama_id}/clases", json={"posicion_x": 0, "posicion_y": 0})
    assert res_crear.status_code == 403
    res_patch = client.patch(f"/api/diagramas/{diagrama_id}/clases/{clase['id']}", json={"posicion_x": 100})
    assert res_patch.status_code == 403
    res_del = client.delete(f"/api/diagramas/{diagrama_id}/clases/{clase['id']}")
    assert res_del.status_code == 403

    # Owner upgrades secondary user to 'editor'
    app.dependency_overrides[get_current_user] = lambda: usuario_autenticado
    miembros = client.get(f"/api/proyectos/{proyecto_id}/miembros").json()["items"]
    colab_id = next(m["id"] for m in miembros if not m["es_propietario"])
    client.patch(f"/api/proyectos/{proyecto_id}/miembros/{colab_id}/rol", json={"rol": "editor"})

    # Editor can mutate
    app.dependency_overrides[get_current_user] = lambda: usuario_secundario
    res_crear_ed = client.post(f"/api/diagramas/{diagrama_id}/clases", json={"posicion_x": 200, "posicion_y": 200})
    assert res_crear_ed.status_code == 201
    res_patch_ed = client.patch(f"/api/diagramas/{diagrama_id}/clases/{clase['id']}", json={"posicion_x": 150})
    assert res_patch_ed.status_code == 200

