from uuid import uuid4


def _crear_diagrama(client) -> tuple[str, str]:
    assert client.post("/api/proyectos/crear").status_code == 201
    proyecto_id = client.get("/api/proyectos/listado").json()["items"][0]["id"]
    diagrama_id = client.get(
        f"/api/proyectos/{proyecto_id}/diagramas"
    ).json()["items"][0]["id"]
    return proyecto_id, diagrama_id


def test_operacion_diagrama_sin_autenticacion(unauthenticated_client):
    action_id = str(uuid4())
    diag_id = str(uuid4())
    res = unauthenticated_client.post(
        f"/api/diagramas/{diag_id}/operaciones",
        headers={"Idempotency-Key": action_id},
        json={"tipo": "CREAR_CLASE", "datos": {}},
    )
    assert res.status_code == 401


def test_operacion_diagrama_sin_idempotency_key(client):
    _, diagrama_id = _crear_diagrama(client)
    res = client.post(
        f"/api/diagramas/{diagrama_id}/operaciones",
        json={"tipo": "CREAR_CLASE", "datos": {}},
    )
    assert res.status_code in (400, 422)


def test_operacion_diagrama_tipo_desconocido(client):
    _, diagrama_id = _crear_diagrama(client)
    res = client.post(
        f"/api/diagramas/{diagrama_id}/operaciones",
        headers={"Idempotency-Key": str(uuid4())},
        json={"tipo": "TIPO_INVALIDO", "datos": {}},
    )
    assert res.status_code in (400, 422)


def test_operacion_crear_clase_contrato(client):
    _, diagrama_id = _crear_diagrama(client)
    action_id = str(uuid4())
    class_id = str(uuid4())
    attr_id = str(uuid4())

    payload = {
        "tipo": "CREAR_CLASE",
        "datos": {
            "id_clase": class_id,
            "id_atributo_inicial": attr_id,
            "nombre": "Cliente",
            "posicion_x": 100,
            "posicion_y": 150,
            "ancho": 220,
        },
    }

    res = client.post(
        f"/api/diagramas/{diagrama_id}/operaciones",
        headers={"Idempotency-Key": action_id},
        json=payload,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["action_id"] == action_id
    assert data["id_diagrama"] == diagrama_id
    assert data["tipo"] == "CREAR_CLASE"
    assert "efectos" in data
    efectos = data["efectos"]
    assert len(efectos["clases_actualizadas"]) == 1
    clase = efectos["clases_actualizadas"][0]
    assert clase["id"] == class_id
    assert clase["nombre"] == "Cliente"
    assert len(clase["atributos"]) == 1
    assert clase["atributos"][0]["id"] == attr_id
    assert clase["atributos"][0]["es_llave_primaria"] is True

    # Replay idempotente con mismo action_id y payload idéntico
    replay = client.post(
        f"/api/diagramas/{diagrama_id}/operaciones",
        headers={"Idempotency-Key": action_id},
        json=payload,
    )
    assert replay.status_code == 200
    assert replay.json() == data

    # Mismo action_id con payload diferente retorna 409 Conflicto
    conflicto = client.post(
        f"/api/diagramas/{diagrama_id}/operaciones",
        headers={"Idempotency-Key": action_id},
        json={"tipo": "CREAR_CLASE", "datos": {"nombre": "Otro"}},
    )
    assert conflicto.status_code == 409
