import uuid
import pytest


def test_quickstart_escenario_1_ciclo_de_vida_relacion(client):
    # 1. Crear Proyecto y Diagrama D1
    assert client.post("/api/proyectos/crear").status_code == 201
    proyecto_id = client.get("/api/proyectos/listado").json()["items"][0]["id"]
    diagrama_id = client.get(f"/api/proyectos/{proyecto_id}/diagramas").json()["items"][0]["id"]

    # 2. Crear dos clases C1 ("Cliente") y C2 ("Pedido")
    c1_id = str(uuid.uuid4())
    c2_id = str(uuid.uuid4())
    res_c1 = client.post(
        f"/api/diagramas/{diagrama_id}/clases",
        json={"id_clase": c1_id, "nombre": "Cliente", "posicion_x": 100, "posicion_y": 100, "ancho": 280},
    )
    assert res_c1.status_code == 201
    res_c2 = client.post(
        f"/api/diagramas/{diagrama_id}/clases",
        json={"id_clase": c2_id, "nombre": "Pedido", "posicion_x": 400, "posicion_y": 100, "ancho": 280},
    )
    assert res_c2.status_code == 201

    # 3. Crear relación R1
    r1_id = str(uuid.uuid4())
    res_r1 = client.post(
        f"/api/diagramas/{diagrama_id}/relaciones",
        json={
            "id_relacion": r1_id,
            "id_clase_origen": c1_id,
            "id_clase_destino": c2_id,
            "tipo_relacion": "dependencia",
            "cardinalidad_origen": "1",
            "cardinalidad_destino": "0..*",
            "conector_origen": "right",
            "conector_destino": "left",
        },
    )
    assert res_r1.status_code == 201
    assert res_r1.json()["id"] == r1_id

    # 4. Listar y Consultar
    list_res = client.get(f"/api/diagramas/{diagrama_id}/relaciones")
    assert list_res.status_code == 200
    assert any(item["id"] == r1_id for item in list_res.json()["items"])

    det_res = client.get(f"/api/diagramas/{diagrama_id}/relaciones/{r1_id}")
    assert det_res.status_code == 200
    assert det_res.json()["id"] == r1_id

    # 5. Actualizar parcialmente (PATCH)
    patch_res = client.patch(
        f"/api/diagramas/{diagrama_id}/relaciones/{r1_id}",
        json={"cardinalidad_destino": "1..*"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["cardinalidad_destino"] == "1..*"


def test_quickstart_escenario_2_relacion_recursiva(client):
    assert client.post("/api/proyectos/crear").status_code == 201
    proyecto_id = client.get("/api/proyectos/listado").json()["items"][0]["id"]
    diagrama_id = client.get(f"/api/proyectos/{proyecto_id}/diagramas").json()["items"][0]["id"]

    c1_id = str(uuid.uuid4())
    client.post(
        f"/api/diagramas/{diagrama_id}/clases",
        json={"id_clase": c1_id, "nombre": "Empleado", "posicion_x": 100, "posicion_y": 100, "ancho": 280},
    )

    r_rec_id = str(uuid.uuid4())
    res_rec = client.post(
        f"/api/diagramas/{diagrama_id}/relaciones",
        json={
            "id_relacion": r_rec_id,
            "id_clase_origen": c1_id,
            "id_clase_destino": c1_id,
            "tipo_relacion": "dependencia",
            "cardinalidad_origen": "0..1",
            "cardinalidad_destino": "0..*",
            "conector_origen": "top",
            "conector_destino": "right",
        },
    )
    assert res_rec.status_code == 201
    assert res_rec.json()["id_clase_origen"] == c1_id
    assert res_rec.json()["id_clase_destino"] == c1_id


def test_quickstart_escenario_3_referencias_fk_e_integridad(client):
    assert client.post("/api/proyectos/crear").status_code == 201
    proyecto_id = client.get("/api/proyectos/listado").json()["items"][0]["id"]
    diagrama_id = client.get(f"/api/proyectos/{proyecto_id}/diagramas").json()["items"][0]["id"]

    c1_id = str(uuid.uuid4())
    client.post(
        f"/api/diagramas/{diagrama_id}/clases",
        json={"id_clase": c1_id, "nombre": "Cliente", "posicion_x": 100, "posicion_y": 100, "ancho": 280},
    )
    a1 = client.post(
        f"/api/clases/{c1_id}/atributos",
        json={
            "tipo_dato": "integer",
            "nombre": "id_cliente",
            "es_llave_primaria": True,
            "permite_nulo": False,
            "es_unico": True,
            "orden_de_posicion": 1,
        },
    ).json()

    c2_id = str(uuid.uuid4())
    client.post(
        f"/api/diagramas/{diagrama_id}/clases",
        json={"id_clase": c2_id, "nombre": "Pedido", "posicion_x": 400, "posicion_y": 100, "ancho": 280},
    )
    a2 = client.post(
        f"/api/clases/{c2_id}/atributos",
        json={
            "tipo_dato": "integer",
            "nombre": "cliente_id",
            "es_llave_primaria": False,
            "permite_nulo": True,
            "es_unico": False,
            "orden_de_posicion": 1,
        },
    ).json()

    r1_id = str(uuid.uuid4())
    client.post(
        f"/api/diagramas/{diagrama_id}/relaciones",
        json={
            "id_relacion": r1_id,
            "id_clase_origen": c1_id,
            "id_clase_destino": c2_id,
            "tipo_relacion": "dependencia",
            "cardinalidad_origen": "1",
            "cardinalidad_destino": "0..*",
            "conector_origen": "right",
            "conector_destino": "left",
        },
    )

    # 1. Crear Referencia FK Válida
    fk1_id = str(uuid.uuid4())
    res_fk1 = client.post(
        f"/api/relaciones/{r1_id}/referencias-fk",
        json={
            "id_referencia_fk": fk1_id,
            "id_atributo_fk": a2["id"],
            "id_atributo_referenciado": a1["id"],
            "on_delete": "SET_NULL",
            "on_update": "CASCADE",
        },
    )
    assert res_fk1.status_code == 201
    assert res_fk1.json()["id"] == fk1_id

    # 2. Actualizar Referencia FK sin conflicto consigo misma
    res_patch = client.patch(
        f"/api/relaciones/{r1_id}/referencias-fk/{fk1_id}",
        json={"on_delete": "CASCADE"},
    )
    assert res_patch.status_code == 200
    assert res_patch.json()["on_delete"] == "CASCADE"

    # 3. Rechazo por incompatibilidad de tipo
    a_str = client.post(
        f"/api/clases/{c2_id}/atributos",
        json={
            "tipo_dato": "varchar",
            "nombre": "codigo_str",
            "es_llave_primaria": False,
            "permite_nulo": True,
            "es_unico": False,
            "orden_de_posicion": 2,
        },
    ).json()
    res_incomp = client.post(
        f"/api/relaciones/{r1_id}/referencias-fk",
        json={
            "id_referencia_fk": str(uuid.uuid4()),
            "id_atributo_fk": a_str["id"],
            "id_atributo_referenciado": a1["id"],
        },
    )
    assert res_incomp.status_code == 400
    assert res_incomp.json()["error"]["code"] == "TIPO_ATRIBUTO_INCOMPATIBLE"

    # 4. Rechazo por atributo no elegible (no PK ni unique)
    a_no_pk = client.post(
        f"/api/clases/{c1_id}/atributos",
        json={
            "tipo_dato": "integer",
            "nombre": "edad",
            "es_llave_primaria": False,
            "permite_nulo": True,
            "es_unico": False,
            "orden_de_posicion": 2,
        },
    ).json()
    res_no_ref = client.post(
        f"/api/relaciones/{r1_id}/referencias-fk",
        json={
            "id_referencia_fk": str(uuid.uuid4()),
            "id_atributo_fk": a2["id"],
            "id_atributo_referenciado": a_no_pk["id"],
        },
    )
    assert res_no_ref.status_code == 400
    assert res_no_ref.json()["error"]["code"] == "ATRIBUTO_NO_REFERENCIABLE"

    # 5. Rechazo por SET_NULL en atributo no nulleable
    a_no_null = client.post(
        f"/api/clases/{c2_id}/atributos",
        json={
            "tipo_dato": "integer",
            "nombre": "cliente_id_no_null",
            "es_llave_primaria": False,
            "permite_nulo": False,
            "es_unico": False,
            "orden_de_posicion": 3,
        },
    ).json()
    res_set_null = client.post(
        f"/api/relaciones/{r1_id}/referencias-fk",
        json={
            "id_referencia_fk": str(uuid.uuid4()),
            "id_atributo_fk": a_no_null["id"],
            "id_atributo_referenciado": a1["id"],
            "on_delete": "SET_NULL",
        },
    )
    assert res_set_null.status_code == 400
    assert res_set_null.json()["error"]["code"] == "CONFIGURACION_REFERENCIA_FK_INVALIDA"

    # 6. Rechazo de par duplicado
    res_dup = client.post(
        f"/api/relaciones/{r1_id}/referencias-fk",
        json={
            "id_referencia_fk": str(uuid.uuid4()),
            "id_atributo_fk": a2["id"],
            "id_atributo_referenciado": a1["id"],
        },
    )
    assert res_dup.status_code == 409
    assert res_dup.json()["error"]["code"] == "VINCULO_REFERENCIA_FK_DUPLICADO"

    # 7. Consultar detalle de diagrama
    diag_det = client.get(f"/api/proyectos/{proyecto_id}/diagramas/{diagrama_id}")
    assert diag_det.status_code == 200
    d_data = diag_det.json()
    assert len(d_data["clases"]) == 2
    assert len(d_data["relaciones"]) == 1
    assert len(d_data["relaciones"][0]["referencias_fk"]) == 1


def test_quickstart_escenario_4_integridad_purga_y_cascada(client):
    assert client.post("/api/proyectos/crear").status_code == 201
    proyecto_id = client.get("/api/proyectos/listado").json()["items"][0]["id"]
    diagrama_id = client.get(f"/api/proyectos/{proyecto_id}/diagramas").json()["items"][0]["id"]

    c1_id = str(uuid.uuid4())
    client.post(
        f"/api/diagramas/{diagrama_id}/clases",
        json={"id_clase": c1_id, "nombre": "Cliente", "posicion_x": 100, "posicion_y": 100, "ancho": 280},
    )
    a1 = client.post(
        f"/api/clases/{c1_id}/atributos",
        json={
            "tipo_dato": "integer",
            "nombre": "id_cliente",
            "es_llave_primaria": True,
            "permite_nulo": False,
            "es_unico": True,
            "orden_de_posicion": 1,
        },
    ).json()

    c2_id = str(uuid.uuid4())
    client.post(
        f"/api/diagramas/{diagrama_id}/clases",
        json={"id_clase": c2_id, "nombre": "Pedido", "posicion_x": 400, "posicion_y": 100, "ancho": 280},
    )
    a2 = client.post(
        f"/api/clases/{c2_id}/atributos",
        json={
            "tipo_dato": "integer",
            "nombre": "cliente_id",
            "es_llave_primaria": False,
            "permite_nulo": True,
            "es_unico": False,
            "orden_de_posicion": 1,
        },
    ).json()

    r1_id = str(uuid.uuid4())
    client.post(
        f"/api/diagramas/{diagrama_id}/relaciones",
        json={
            "id_relacion": r1_id,
            "id_clase_origen": c1_id,
            "id_clase_destino": c2_id,
            "tipo_relacion": "dependencia",
            "cardinalidad_origen": "1",
            "cardinalidad_destino": "0..*",
            "conector_origen": "right",
            "conector_destino": "left",
        },
    )

    fk1_id = str(uuid.uuid4())
    client.post(
        f"/api/relaciones/{r1_id}/referencias-fk",
        json={
            "id_referencia_fk": fk1_id,
            "id_atributo_fk": a2["id"],
            "id_atributo_referenciado": a1["id"],
        },
    )

    # 1. Eliminar atributo cliente_id y verificar cascada sobre FK1
    del_a2 = client.delete(f"/api/clases/{c2_id}/atributos/{a2['id']}")
    assert del_a2.status_code == 204
    assert client.get(f"/api/relaciones/{r1_id}/referencias-fk/{fk1_id}").status_code == 404

    # 2. Crear nuevo atributo FK en C2 y nueva referencia FK2
    a2_nuevo = client.post(
        f"/api/clases/{c2_id}/atributos",
        json={
            "tipo_dato": "integer",
            "nombre": "cliente_id_v2",
            "es_llave_primaria": False,
            "permite_nulo": True,
            "es_unico": False,
            "orden_de_posicion": 1,
        },
    ).json()
    fk2_id = str(uuid.uuid4())
    client.post(
        f"/api/relaciones/{r1_id}/referencias-fk",
        json={
            "id_referencia_fk": fk2_id,
            "id_atributo_fk": a2_nuevo["id"],
            "id_atributo_referenciado": a1["id"],
        },
    )
    # Crear clase C3 y cambiar destino de R1 a C3
    c3_id = str(uuid.uuid4())
    client.post(
        f"/api/diagramas/{diagrama_id}/clases",
        json={"id_clase": c3_id, "nombre": "Factura", "posicion_x": 700, "posicion_y": 100, "ancho": 280},
    )
    patch_r1 = client.patch(
        f"/api/diagramas/{diagrama_id}/relaciones/{r1_id}",
        json={"id_clase_destino": c3_id},
    )
    assert patch_r1.status_code == 200
    assert client.get(f"/api/relaciones/{r1_id}/referencias-fk/{fk2_id}").status_code == 404

    # 3. Eliminar relación R1
    del_r1 = client.delete(f"/api/diagramas/{diagrama_id}/relaciones/{r1_id}")
    assert del_r1.status_code == 204
    assert client.get(f"/api/diagramas/{diagrama_id}/relaciones/{r1_id}").status_code == 404

    # 4. Eliminar clase C2 y verificar cascada sobre nueva relación R2
    r2_id = str(uuid.uuid4())
    client.post(
        f"/api/diagramas/{diagrama_id}/relaciones",
        json={
            "id_relacion": r2_id,
            "id_clase_origen": c1_id,
            "id_clase_destino": c2_id,
            "tipo_relacion": "dependencia",
            "cardinalidad_origen": "1",
            "cardinalidad_destino": "1",
            "conector_origen": "right",
            "conector_destino": "left",
        },
    )
    del_c2 = client.delete(f"/api/diagramas/{diagrama_id}/clases/{c2_id}")
    assert del_c2.status_code == 204
    assert client.get(f"/api/diagramas/{diagrama_id}/relaciones/{r2_id}").status_code == 404
