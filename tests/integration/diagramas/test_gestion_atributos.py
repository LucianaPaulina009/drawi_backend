from app.core.security.auth import get_current_user
from app.main import app


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
    primero = _crear_atributo(client, clase_id, "nombre")
    segundo = _crear_atributo(client, clase_id, "correo")

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
    assert [item["id"] for item in listado.json()["items"]] == [segundo["id"], primero["id"]]
    assert [item["orden_de_posicion"] for item in listado.json()["items"]] == [1, 2]
    assert [item["nombre"] for item in detalle.json()["clases"][0]["atributos"]] == ["correo", "nombre"]
    assert (
        detalle.json()["clases"][0]["posicion_x"],
        detalle.json()["clases"][0]["posicion_y"],
    ) == (45, 60)


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
    assert client.get(f"/api/clases/{clase_id}/atributos").json()["items"] == []

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
