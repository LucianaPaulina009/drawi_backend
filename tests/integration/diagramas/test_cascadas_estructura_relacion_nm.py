import uuid


def _crear_estructura_nm(client) -> dict[str, str]:
    assert client.post("/api/proyectos/crear").status_code == 201
    proyecto_id = client.get("/api/proyectos/listado").json()["items"][0]["id"]
    diagrama_id = client.get(
        f"/api/proyectos/{proyecto_id}/diagramas"
    ).json()["items"][0]["id"]

    clase_a = client.post(
        f"/api/diagramas/{diagrama_id}/clases",
        json={"nombre": "Estudiante", "posicion_x": 100, "posicion_y": 100, "ancho": 280},
    ).json()
    clase_b = client.post(
        f"/api/diagramas/{diagrama_id}/clases",
        json={"nombre": "Curso", "posicion_x": 700, "posicion_y": 100, "ancho": 280},
    ).json()

    ids = {
        "estructura": str(uuid.uuid4()),
        "intermedia": str(uuid.uuid4()),
        "pk_intermedia": str(uuid.uuid4()),
        "fk_origen": str(uuid.uuid4()),
        "fk_destino": str(uuid.uuid4()),
        "relacion_origen": str(uuid.uuid4()),
        "relacion_destino": str(uuid.uuid4()),
        "referencia_origen": str(uuid.uuid4()),
        "referencia_destino": str(uuid.uuid4()),
    }
    respuesta = client.post(
        f"/api/diagramas/{diagrama_id}/estructuras-nm",
        headers={"Idempotency-Key": str(uuid.uuid4())},
        json={
            "id_estructura": ids["estructura"],
            "id_clase_origen": clase_a["id"],
            "id_clase_destino": clase_b["id"],
            "id_clase_intermedia": ids["intermedia"],
            "id_atributo_inicial": ids["pk_intermedia"],
            "id_atributo_fk_origen": ids["fk_origen"],
            "id_atributo_fk_destino": ids["fk_destino"],
            "id_relacion_origen": ids["relacion_origen"],
            "id_relacion_destino": ids["relacion_destino"],
            "id_referencia_fk_origen": ids["referencia_origen"],
            "id_referencia_fk_destino": ids["referencia_destino"],
            "id_atributo_referenciado_origen": clase_a["atributos"][0]["id"],
            "id_atributo_referenciado_destino": clase_b["atributos"][0]["id"],
            "nombre_intermedia": "Estudiante_Curso",
            "posicion_x": 400,
            "posicion_y": 100,
            "ancho": 280,
        },
    )
    assert respuesta.status_code == 201
    return {
        "diagrama": diagrama_id,
        "clase_a": clase_a["id"],
        "clase_b": clase_b["id"],
        **ids,
    }


def _assert_estructura_nm_cerrada(client, recursos: dict[str, str]) -> None:
    diagrama_id = recursos["diagrama"]
    assert client.get(
        f"/api/diagramas/{diagrama_id}/clases/{recursos['intermedia']}"
    ).status_code == 404
    for relacion in ("relacion_origen", "relacion_destino"):
        assert client.get(
            f"/api/diagramas/{diagrama_id}/relaciones/{recursos[relacion]}"
        ).status_code == 404
    for relacion, referencia in (
        ("relacion_origen", "referencia_origen"),
        ("relacion_destino", "referencia_destino"),
    ):
        assert client.get(
            f"/api/relaciones/{recursos[relacion]}/referencias-fk/{recursos[referencia]}"
        ).status_code == 404


def test_eliminar_relacion_origen_cierra_estructura_nm_completa(client):
    recursos = _crear_estructura_nm(client)

    assert client.delete(
        f"/api/diagramas/{recursos['diagrama']}/relaciones/{recursos['relacion_origen']}"
    ).status_code == 204

    _assert_estructura_nm_cerrada(client, recursos)
    assert client.get(
        f"/api/diagramas/{recursos['diagrama']}/clases/{recursos['clase_a']}"
    ).status_code == 200
    assert client.get(
        f"/api/diagramas/{recursos['diagrama']}/clases/{recursos['clase_b']}"
    ).status_code == 200


def test_eliminar_relacion_destino_cierra_estructura_nm_completa(client):
    recursos = _crear_estructura_nm(client)

    assert client.delete(
        f"/api/diagramas/{recursos['diagrama']}/relaciones/{recursos['relacion_destino']}"
    ).status_code == 204

    _assert_estructura_nm_cerrada(client, recursos)
    assert client.get(
        f"/api/diagramas/{recursos['diagrama']}/clases/{recursos['clase_a']}"
    ).status_code == 200
    assert client.get(
        f"/api/diagramas/{recursos['diagrama']}/clases/{recursos['clase_b']}"
    ).status_code == 200


def test_eliminar_clase_origen_cierra_estructura_nm_y_conserva_destino(client):
    recursos = _crear_estructura_nm(client)

    assert client.delete(
        f"/api/diagramas/{recursos['diagrama']}/clases/{recursos['clase_a']}"
    ).status_code == 204

    _assert_estructura_nm_cerrada(client, recursos)
    assert client.get(
        f"/api/diagramas/{recursos['diagrama']}/clases/{recursos['clase_a']}"
    ).status_code == 404
    assert client.get(
        f"/api/diagramas/{recursos['diagrama']}/clases/{recursos['clase_b']}"
    ).status_code == 200


def test_eliminar_clase_destino_cierra_estructura_nm_y_conserva_origen(client):
    recursos = _crear_estructura_nm(client)

    assert client.delete(
        f"/api/diagramas/{recursos['diagrama']}/clases/{recursos['clase_b']}"
    ).status_code == 204

    _assert_estructura_nm_cerrada(client, recursos)
    assert client.get(
        f"/api/diagramas/{recursos['diagrama']}/clases/{recursos['clase_b']}"
    ).status_code == 404
    assert client.get(
        f"/api/diagramas/{recursos['diagrama']}/clases/{recursos['clase_a']}"
    ).status_code == 200


def test_eliminar_clase_intermedia_cierra_estructura_nm_y_conserva_extremos(client):
    recursos = _crear_estructura_nm(client)

    assert client.delete(
        f"/api/diagramas/{recursos['diagrama']}/clases/{recursos['intermedia']}"
    ).status_code == 204

    _assert_estructura_nm_cerrada(client, recursos)
    assert client.get(
        f"/api/diagramas/{recursos['diagrama']}/clases/{recursos['clase_a']}"
    ).status_code == 200
    assert client.get(
        f"/api/diagramas/{recursos['diagrama']}/clases/{recursos['clase_b']}"
    ).status_code == 200
