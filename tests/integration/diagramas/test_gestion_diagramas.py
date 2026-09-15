from app.core.security.auth import get_current_user
from app.main import app


def _crear_proyecto_y_obtener_id(client) -> str:
    client.post("/api/proyectos/crear")
    return client.get("/api/proyectos/listado").json()["items"][0]["id"]


def test_reutiliza_menor_numero_y_no_renumera(client):
    proyecto_id = _crear_proyecto_y_obtener_id(client)
    pagina_2 = client.post(f"/api/proyectos/{proyecto_id}/diagramas", json={}).json()
    pagina_3 = client.post(f"/api/proyectos/{proyecto_id}/diagramas", json={}).json()

    assert client.delete(
        f"/api/proyectos/{proyecto_id}/diagramas/{pagina_2['id']}"
    ).status_code == 204

    pagina_reutilizada = client.post(
        f"/api/proyectos/{proyecto_id}/diagramas", json={}
    ).json()
    numeros = [
        item["numero"]
        for item in client.get(f"/api/proyectos/{proyecto_id}/diagramas").json()["items"]
    ]

    assert pagina_3["numero"] == 3
    assert pagina_reutilizada["numero"] == 2
    assert numeros == [1, 2, 3]


def test_rechaza_eliminar_el_unico_diagrama(client):
    proyecto_id = _crear_proyecto_y_obtener_id(client)
    diagrama_id = client.get(f"/api/proyectos/{proyecto_id}/diagramas").json()["items"][0]["id"]

    response = client.delete(f"/api/proyectos/{proyecto_id}/diagramas/{diagrama_id}")

    assert response.status_code == 409
    assert len(client.get(f"/api/proyectos/{proyecto_id}/diagramas").json()["items"]) == 1


def test_no_permite_acceso_de_otro_usuario(client, usuario_secundario):
    proyecto_id = _crear_proyecto_y_obtener_id(client)
    app.dependency_overrides[get_current_user] = lambda: usuario_secundario

    response = client.get(f"/api/proyectos/{proyecto_id}/diagramas")

    assert response.status_code == 404
