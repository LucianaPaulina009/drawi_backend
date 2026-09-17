import uuid
import pytest


def _configurar_diagrama_con_elementos(client) -> tuple[str, str, dict, dict, dict, str]:
    assert client.post("/api/proyectos/crear").status_code == 201
    proyecto_id = client.get("/api/proyectos/listado").json()["items"][0]["id"]
    diagrama_id = client.get(
        f"/api/proyectos/{proyecto_id}/diagramas"
    ).json()["items"][0]["id"]

    c1 = client.post(
        f"/api/diagramas/{diagrama_id}/clases",
        json={"nombre": "Usuario", "posicion_x": 100, "posicion_y": 100, "ancho": 280},
    ).json()
    a1 = client.post(
        f"/api/clases/{c1['id']}/atributos",
        json={
            "tipo_dato": "integer",
            "nombre": "id",
            "es_llave_primaria": True,
            "permite_nulo": False,
            "es_unico": True,
            "orden_de_posicion": 1,
        },
    ).json()

    c2 = client.post(
        f"/api/diagramas/{diagrama_id}/clases",
        json={"nombre": "Perfil", "posicion_x": 400, "posicion_y": 100, "ancho": 280},
    ).json()
    a2 = client.post(
        f"/api/clases/{c2['id']}/atributos",
        json={
            "tipo_dato": "integer",
            "nombre": "usuario_id",
            "es_llave_primaria": False,
            "permite_nulo": True,
            "es_unico": False,
            "orden_de_posicion": 1,
        },
    ).json()

    rel_id = str(uuid.uuid4())
    rel = client.post(
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
    ).json()

    ref_id = str(uuid.uuid4())
    client.post(
        f"/api/relaciones/{rel_id}/referencias-fk",
        json={
            "id_referencia_fk": ref_id,
            "id_atributo_fk": a2["id"],
            "id_atributo_referenciado": a1["id"],
        },
    )

    return proyecto_id, diagrama_id, c1, c2, rel, ref_id


def test_cascada_eliminacion_clase_limpia_relaciones_y_fks(client):
    proyecto_id, diagrama_id, c1, c2, rel, ref_id = _configurar_diagrama_con_elementos(client)

    # Eliminar Clase 1 (Usuario)
    del_c1 = client.delete(f"/api/diagramas/{diagrama_id}/clases/{c1['id']}")
    assert del_c1.status_code == 204

    # La clase ya no existe
    assert client.get(f"/api/diagramas/{diagrama_id}/clases/{c1['id']}").status_code == 404

    # La relación que la involucraba ya no debe estar activa
    assert client.get(f"/api/diagramas/{diagrama_id}/relaciones/{rel['id']}").status_code == 404
    assert client.get(f"/api/diagramas/{diagrama_id}/relaciones").json()["items"] == []

    # La referencia FK dependiente ya no debe estar activa
    assert client.get(f"/api/relaciones/{rel['id']}/referencias-fk/{ref_id}").status_code == 404

    # La otra clase C2 sigue existiendo
    assert client.get(f"/api/diagramas/{diagrama_id}/clases/{c2['id']}").status_code == 200


def test_cascada_eliminacion_diagrama_limpia_todo(client):
    proyecto_id, diagrama_id, c1, c2, rel, ref_id = _configurar_diagrama_con_elementos(client)

    # Crear un segundo diagrama para permitir eliminar el primero
    diag2 = client.post(
        f"/api/proyectos/{proyecto_id}/diagramas",
        json={"nombre": "Diagrama 2"},
    ).json()

    # Eliminar el primer diagrama
    del_diag = client.delete(f"/api/proyectos/{proyecto_id}/diagramas/{diagrama_id}")
    assert del_diag.status_code == 204

    # El diagrama ya no existe
    assert client.get(f"/api/proyectos/{proyecto_id}/diagramas/{diagrama_id}").status_code == 404

    # Las relaciones y FKs del diagrama eliminado no están disponibles
    assert client.get(f"/api/diagramas/{diagrama_id}/relaciones").status_code == 404
