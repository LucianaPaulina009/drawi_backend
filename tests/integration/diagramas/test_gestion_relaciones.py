import uuid
import pytest
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
    payload = {"nombre": "Tabla", "posicion_x": 10, "posicion_y": 20, "ancho": 280, **kwargs}
    response = client.post(
        f"/api/diagramas/{diagrama_id}/clases",
        json=payload,
    )
    assert response.status_code == 201
    return response.json()


def test_ciclo_de_vida_relacion_y_listado(client):
    _, diagrama_id = _crear_proyecto_y_diagrama(client)
    c1 = _crear_clase(client, diagrama_id, nombre="Cliente")
    c2 = _crear_clase(client, diagrama_id, nombre="Pedido")

    rel_id = str(uuid.uuid4())
    crear_res = client.post(
        f"/api/diagramas/{diagrama_id}/relaciones",
        json={
            "id_relacion": rel_id,
            "id_clase_origen": c1["id"],
            "id_clase_destino": c2["id"],
                "tipo_relacion": "dependencia",
            "cardinalidad_origen": "1",
            "cardinalidad_destino": "0..*",
            "conector_origen": "right",
            "conector_destino": "left",
        },
    )
    assert crear_res.status_code == 201
    data = crear_res.json()
    assert data["id"] == rel_id
    assert data["id_clase_origen"] == c1["id"]
    assert data["id_clase_destino"] == c2["id"]
    assert data["cardinalidad_origen"] == "1"
    assert data["cardinalidad_destino"] == "0..*"
    assert data["referencias_fk"] == []

    # Consultar detalle
    det_res = client.get(f"/api/diagramas/{diagrama_id}/relaciones/{rel_id}")
    assert det_res.status_code == 200
    assert det_res.json()["id"] == rel_id

    # Listar relaciones
    list_res = client.get(f"/api/diagramas/{diagrama_id}/relaciones")
    assert list_res.status_code == 200
    items = list_res.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == rel_id

    # Actualizar parcialmente
    patch_res = client.patch(
        f"/api/diagramas/{diagrama_id}/relaciones/{rel_id}",
        json={"cardinalidad_destino": "1..*", "conector_origen": "top"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["cardinalidad_destino"] == "1..*"
    assert patch_res.json()["conector_origen"] == "top"
    assert patch_res.json()["cardinalidad_origen"] == "1"

    # Eliminar
    del_res = client.delete(f"/api/diagramas/{diagrama_id}/relaciones/{rel_id}")
    assert del_res.status_code == 204

    # Verificar que ya no existe
    assert client.get(f"/api/diagramas/{diagrama_id}/relaciones/{rel_id}").status_code == 404
    assert client.get(f"/api/diagramas/{diagrama_id}/relaciones").json()["items"] == []


def test_rechaza_uuid_duplicado_en_relacion(client):
    _, diagrama_id = _crear_proyecto_y_diagrama(client)
    c1 = _crear_clase(client, diagrama_id)
    c2 = _crear_clase(client, diagrama_id)

    rel_id = str(uuid.uuid4())
    res1 = client.post(
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
    )
    assert res1.status_code == 201

    res2 = client.post(
        f"/api/diagramas/{diagrama_id}/relaciones",
        json={
            "id_relacion": rel_id,
            "id_clase_origen": c1["id"],
            "id_clase_destino": c2["id"],
            "tipo_relacion": "herencia",
            "cardinalidad_origen": "1",
            "cardinalidad_destino": "1",
            "conector_origen": "top",
            "conector_destino": "bottom",
        },
    )
    assert res2.status_code == 409


def test_relacion_recursiva(client):
    _, diagrama_id = _crear_proyecto_y_diagrama(client)
    c1 = _crear_clase(client, diagrama_id, nombre="Empleado")

    rel_id = str(uuid.uuid4())
    res = client.post(
        f"/api/diagramas/{diagrama_id}/relaciones",
        json={
            "id_relacion": rel_id,
            "id_clase_origen": c1["id"],
            "id_clase_destino": c1["id"],
                "tipo_relacion": "dependencia",
            "cardinalidad_origen": "0..1",
            "cardinalidad_destino": "0..*",
            "conector_origen": "top",
            "conector_destino": "right",
        },
    )
    assert res.status_code == 201
    assert res.json()["id_clase_origen"] == c1["id"]
    assert res.json()["id_clase_destino"] == c1["id"]


def test_validaciones_integridad_clases_y_catalogos(client):
    _, diagrama_id = _crear_proyecto_y_diagrama(client)
    c1 = _crear_clase(client, diagrama_id)

    # Clase inexistente
    res_err_clase = client.post(
        f"/api/diagramas/{diagrama_id}/relaciones",
        json={
            "id_relacion": str(uuid.uuid4()),
            "id_clase_origen": c1["id"],
            "id_clase_destino": str(uuid.uuid4()),
                "tipo_relacion": "dependencia",
            "cardinalidad_origen": "1",
            "cardinalidad_destino": "1",
            "conector_origen": "right",
            "conector_destino": "left",
        },
    )
    assert res_err_clase.status_code == 404

    # Tipo invalido
    res_err_tipo = client.post(
        f"/api/diagramas/{diagrama_id}/relaciones",
        json={
            "id_relacion": str(uuid.uuid4()),
            "id_clase_origen": c1["id"],
            "id_clase_destino": c1["id"],
            "tipo_relacion": "tipo_inexistente",
            "cardinalidad_origen": "1",
            "cardinalidad_destino": "1",
            "conector_origen": "right",
            "conector_destino": "left",
        },
    )
    assert res_err_tipo.status_code == 400

    # Cardinalidad invalida
    res_err_card = client.post(
        f"/api/diagramas/{diagrama_id}/relaciones",
        json={
            "id_relacion": str(uuid.uuid4()),
            "id_clase_origen": c1["id"],
            "id_clase_destino": c1["id"],
                "tipo_relacion": "dependencia",
            "cardinalidad_origen": "N..M",
            "cardinalidad_destino": "1",
            "conector_origen": "right",
            "conector_destino": "left",
        },
    )
    assert res_err_card.status_code == 400

    # Conector invalido
    res_err_con = client.post(
        f"/api/diagramas/{diagrama_id}/relaciones",
        json={
            "id_relacion": str(uuid.uuid4()),
            "id_clase_origen": c1["id"],
            "id_clase_destino": c1["id"],
            "tipo_relacion": "asociacion",
            "cardinalidad_origen": "1",
            "cardinalidad_destino": "1",
            "conector_origen": "centro",
            "conector_destino": "left",
        },
    )
    assert res_err_con.status_code == 400


def test_permisos_por_rol_relaciones(
    client, session, usuario_autenticado: AuthUser, usuario_secundario: AuthUser
):
    session.add(BetterAuthUser(id=usuario_autenticado.user_id, name="Owner", email=usuario_autenticado.email, emailVerified=True))
    session.add(BetterAuthUser(id=usuario_secundario.user_id, name="Colab", email=usuario_secundario.email, emailVerified=True))
    session.commit()

    proyecto_id, diagrama_id = _crear_proyecto_y_diagrama(client)
    c1 = _crear_clase(client, diagrama_id)
    c2 = _crear_clase(client, diagrama_id)

    inv_res = client.post(f"/api/proyectos/{proyecto_id}/invitacion")
    codigo = inv_res.json()["codigo_acceso"]

    app.dependency_overrides[get_current_user] = lambda: usuario_secundario
    client.post(f"/api/invitaciones/{codigo}/unirse")

    # Lector no puede mutar
    rel_id = str(uuid.uuid4())
    res_crear = client.post(
        f"/api/diagramas/{diagrama_id}/relaciones",
        json={
            "id_relacion": rel_id,
            "id_clase_origen": c1["id"],
            "id_clase_destino": c2["id"],
            "tipo_relacion": "asociacion",
            "cardinalidad_origen": "1",
            "cardinalidad_destino": "1",
            "conector_origen": "right",
            "conector_destino": "left",
        },
    )
    assert res_crear.status_code == 403

    # Cambiar rol a editor
    app.dependency_overrides[get_current_user] = lambda: usuario_autenticado
    miembros = client.get(f"/api/proyectos/{proyecto_id}/miembros").json()["items"]
    colab_id = next(m["id"] for m in miembros if not m["es_propietario"])
    client.patch(f"/api/proyectos/{proyecto_id}/miembros/{colab_id}/rol", json={"rol": "editor"})

    # Editor puede crear una relación que no requiere materialización FK.
    app.dependency_overrides[get_current_user] = lambda: usuario_secundario
    res_crear_ok = client.post(
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
    )
    assert res_crear_ok.status_code == 201


def test_asociacion_uno_a_muchos_requiere_y_confirma_fk_atomica(client):
    _, diagrama_id = _crear_proyecto_y_diagrama(client)
    origen = _crear_clase(client, diagrama_id, nombre="Cliente")
    destino = _crear_clase(client, diagrama_id, nombre="Pedido")

    payload = {
        "id_relacion": str(uuid.uuid4()),
        "id_clase_origen": origen["id"],
        "id_clase_destino": destino["id"],
        "tipo_relacion": "asociacion",
        "cardinalidad_origen": "1",
        "cardinalidad_destino": "0..*",
        "conector_origen": "right",
        "conector_destino": "left",
    }
    assert client.post(f"/api/diagramas/{diagrama_id}/relaciones", json=payload).status_code == 400

    atributo_origen = client.get(f"/api/clases/{origen['id']}/atributos").json()["items"][0]
    atributo_destino = client.get(f"/api/clases/{destino['id']}/atributos").json()["items"][0]
    payload["materializacion_fk"] = [{
        "id_referencia_fk": str(uuid.uuid4()),
        "id_atributo_fk": atributo_destino["id"],
        "id_atributo_referenciado": atributo_origen["id"],
    }]
    respuesta = client.post(f"/api/diagramas/{diagrama_id}/relaciones", json=payload)
    assert respuesta.status_code == 201
    assert len(respuesta.json()["referencias_fk"]) == 1


def test_materializacion_multiple_uno_a_uno_y_nm_sin_fk_directa(client):
    _, diagrama_id = _crear_proyecto_y_diagrama(client)
    origen = _crear_clase(client, diagrama_id, nombre="Cuenta")
    destino = _crear_clase(client, diagrama_id, nombre="Perfil")
    atributo_origen = client.get(f"/api/clases/{origen['id']}/atributos").json()["items"][0]
    atributo_destino = client.get(f"/api/clases/{destino['id']}/atributos").json()["items"][0]

    # N:M conserva el vínculo UML sin una FK directa ni tabla intermedia.
    nm = client.post(
        f"/api/diagramas/{diagrama_id}/relaciones",
        json={
            "id_relacion": str(uuid.uuid4()),
            "id_clase_origen": origen["id"],
            "id_clase_destino": destino["id"],
            "tipo_relacion": "asociacion",
            "cardinalidad_origen": "0..*",
            "cardinalidad_destino": "0..*",
            "conector_origen": "right",
            "conector_destino": "left",
        },
    )
    assert nm.status_code == 201
    assert nm.json()["referencias_fk"] == []

    relacion_id = str(uuid.uuid4())
    uno_a_uno = {
        "id_relacion": relacion_id,
        "id_clase_origen": origen["id"],
        "id_clase_destino": destino["id"],
        "tipo_relacion": "asociacion",
        "cardinalidad_origen": "1",
        "cardinalidad_destino": "1",
        "conector_origen": "right",
        "conector_destino": "left",
    }
    assert client.post(f"/api/diagramas/{diagrama_id}/relaciones", json=uno_a_uno).status_code == 400

    atributo_fk_nuevo_id = str(uuid.uuid4())
    uno_a_uno["materializacion_fk"] = [
        {
            "id_referencia_fk": str(uuid.uuid4()),
            "id_atributo_referenciado": atributo_origen["id"],
            "id_clase_fk": destino["id"],
            "atributo_fk_nuevo": {
                "id_atributo": atributo_fk_nuevo_id,
                "nombre": "cuenta_id",
                "tipo_dato": "integer",
                "permite_nulo": False,
            },
        },
        {
            "id_referencia_fk": str(uuid.uuid4()),
            "id_atributo_fk": atributo_destino["id"],
            "id_atributo_referenciado": atributo_origen["id"],
        },
    ]
    creada = client.post(f"/api/diagramas/{diagrama_id}/relaciones", json=uno_a_uno)
    assert creada.status_code == 201
    assert len(creada.json()["referencias_fk"]) == 2
    atributos_destino = client.get(f"/api/clases/{destino['id']}/atributos").json()["items"]
    assert next(item for item in atributos_destino if item["id"] == atributo_fk_nuevo_id)["procedencia"] == "sistema_fk"
