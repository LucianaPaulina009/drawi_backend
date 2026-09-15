from app.core.security.auth import get_current_user
from app.main import app


def _crear_proyecto_y_diagrama(client) -> tuple[str, str]:
    assert client.post("/api/proyectos/crear").status_code == 201
    proyecto_id = client.get("/api/proyectos/listado").json()["items"][0]["id"]
    diagrama_id = client.get(
        f"/api/proyectos/{proyecto_id}/diagramas"
    ).json()["items"][0]["id"]
    return proyecto_id, diagrama_id


def _crear_clase(client, diagrama_id: str) -> dict:
    response = client.post(
        f"/api/diagramas/{diagrama_id}/clases",
        json={"nombre": "Usuario", "posicion_x": 10, "posicion_y": 20, "ancho": 300},
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
    assert clase_detalle["atributos"] == []


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
