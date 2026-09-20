import uuid


def test_contrato_diagrama_detalle_completo_con_relaciones_y_fks(client):
    # 1. Crear proyecto y obtener primer diagrama
    assert client.post("/api/proyectos/crear").status_code == 201
    proyecto_id = client.get("/api/proyectos/listado").json()["items"][0]["id"]
    diagrama_id = client.get(
        f"/api/proyectos/{proyecto_id}/diagramas"
    ).json()["items"][0]["id"]

    # 2. Crear Clases y Atributos
    c1 = client.post(
        f"/api/diagramas/{diagrama_id}/clases",
        json={"nombre": "Autor", "posicion_x": 50, "posicion_y": 50, "ancho": 260},
    ).json()
    a1 = c1["atributos"][0]

    c2 = client.post(
        f"/api/diagramas/{diagrama_id}/clases",
        json={"nombre": "Libro", "posicion_x": 400, "posicion_y": 50, "ancho": 260},
    ).json()

    # 3. Crear Relación con Materialización FK
    rel_id = str(uuid.uuid4())
    ref_id = str(uuid.uuid4())
    a2_id = str(uuid.uuid4())
    rel = client.post(
        f"/api/diagramas/{diagrama_id}/relaciones",
        json={
            "id_relacion": rel_id,
            "id_clase_origen": c2["id"],
            "id_clase_destino": c1["id"],
            "tipo_relacion": "dependencia",
            "cardinalidad_origen": "1",
            "cardinalidad_destino": "0..*",
            "conector_origen": "right",
            "conector_destino": "left",
            "materializacion_fk": [
                {
                    "id_referencia_fk": ref_id,
                    "id_clase_fk": c2["id"],
                    "id_atributo_referenciado": a1["id"],
                    "atributo_fk_nuevo": {
                        "id_atributo": a2_id,
                        "nombre": "autor_id",
                        "tipo_dato": "integer",
                        "permite_nulo": True,
                    },
                    "on_delete": "CASCADE",
                    "on_update": "RESTRICT",
                }
            ],
        },
    ).json()

    # 5. Consultar Detalle Completo del Diagrama
    res = client.get(f"/api/proyectos/{proyecto_id}/diagramas/{diagrama_id}")
    assert res.status_code == 200
    detalle = res.json()

    assert detalle["id"] == diagrama_id
    assert detalle["id_proyecto"] == proyecto_id
    assert isinstance(detalle["clases"], list)
    assert len(detalle["clases"]) == 2

    assert isinstance(detalle["relaciones"], list)
    assert len(detalle["relaciones"]) == 1
    rel_data = detalle["relaciones"][0]
    assert rel_data["id"] == rel_id
    assert rel_data["id_clase_origen"] == c2["id"]
    assert rel_data["id_clase_destino"] == c1["id"]
    assert rel_data["tipo_relacion"] == "dependencia"
    assert rel_data["cardinalidad_origen"] == "1"
    assert rel_data["cardinalidad_destino"] == "0..*"
    assert rel_data["conector_origen"] == "right"
    assert rel_data["conector_destino"] == "left"

    assert isinstance(rel_data["referencias_fk"], list)
    assert len(rel_data["referencias_fk"]) == 1
    fk_data = rel_data["referencias_fk"][0]
    assert fk_data["id"] == ref_id
    assert fk_data["id_relacion"] == rel_id
    assert fk_data["id_atributo_fk"] == a2_id
    assert fk_data["id_atributo_referenciado"] == a1["id"]
    assert fk_data["on_delete"] == "CASCADE"
    assert fk_data["on_update"] == "RESTRICT"
