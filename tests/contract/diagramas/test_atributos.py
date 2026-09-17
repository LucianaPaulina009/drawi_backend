def _crear_clase(client) -> str:
    assert client.post("/api/proyectos/crear").status_code == 201
    proyecto_id = client.get("/api/proyectos/listado").json()["items"][0]["id"]
    diagrama_id = client.get(
        f"/api/proyectos/{proyecto_id}/diagramas"
    ).json()["items"][0]["id"]
    clase = client.post(
        f"/api/diagramas/{diagrama_id}/clases",
        json={"nombre": "Usuario", "posicion_x": 0, "posicion_y": 0, "ancho": 250},
    )
    assert clase.status_code == 201
    return clase.json()["id"]


def test_contrato_endpoints_atributos(client):
    clase_id = _crear_clase(client)
    creado = client.post(
        f"/api/clases/{clase_id}/atributos",
        json={"tipo_dato": "varchar", "nombre": "correo", "longitud": 120},
    )
    assert creado.status_code == 201
    atributo = creado.json()
    assert atributo["id_clase"] == clase_id
    assert atributo["orden_de_posicion"] == 2

    listado = client.get(f"/api/clases/{clase_id}/atributos")
    assert listado.status_code == 200
    assert any(item["id"] == atributo["id"] for item in listado.json()["items"])

    detalle = client.get(f"/api/clases/{clase_id}/atributos/{atributo['id']}")
    assert detalle.status_code == 200

    actualizado = client.patch(
        f"/api/clases/{clase_id}/atributos/{atributo['id']}",
        json={"nombre": "email", "es_unico": True},
    )
    assert actualizado.status_code == 200
    assert actualizado.json()["nombre"] == "email"
    assert actualizado.json()["es_unico"] is True

    eliminado = client.delete(f"/api/clases/{clase_id}/atributos/{atributo['id']}")
    assert eliminado.status_code == 204
    assert client.get(f"/api/clases/{clase_id}/atributos/{atributo['id']}").status_code == 404


def test_contrato_atributos_sin_autenticacion(unauthenticated_client):
    respuesta = unauthenticated_client.get(
        "/api/clases/00000000-0000-0000-0000-000000000001/atributos"
    )
    assert respuesta.status_code == 401


def test_contrato_rechaza_orden_atributo_fuera_de_secuencia(client):
    clase_id = _crear_clase(client)
    respuesta = client.post(
        f"/api/clases/{clase_id}/atributos",
        json={"tipo_dato": "varchar", "nombre": "correo", "longitud": 120, "orden_de_posicion": 5},
    )

    assert respuesta.status_code == 409
    assert respuesta.json()["error"]["code"] == "ORDEN_ATRIBUTO_FUERA_DE_SECUENCIA"


def test_contrato_openapi_tipa_atributos_anidados(client):
    esquema = client.get("/openapi.json").json()["components"]["schemas"]

    assert esquema["ClaseDetalleRead"]["properties"]["atributos"]["items"]["$ref"].endswith("/AtributoRead")
    assert esquema["ClaseEnDiagramaRead"]["properties"]["atributos"]["items"]["$ref"].endswith("/AtributoRead")
