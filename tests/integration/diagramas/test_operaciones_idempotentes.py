import uuid
import pytest


def _crear_diagrama(client) -> tuple[str, str]:
    assert client.post("/api/proyectos/crear").status_code == 201
    proyecto_id = client.get("/api/proyectos/listado").json()["items"][0]["id"]
    diagrama_id = client.get(
        f"/api/proyectos/{proyecto_id}/diagramas"
    ).json()["items"][0]["id"]
    return proyecto_id, diagrama_id


def test_operaciones_idempotencia_replay_y_conflicto(client):
    _, diagrama_id = _crear_diagrama(client)
    action_id = str(uuid.uuid4())
    clase_id = str(uuid.uuid4())
    attr_id = str(uuid.uuid4())

    payload = {
        "tipo": "CREAR_CLASE",
        "datos": {
            "id_clase": clase_id,
            "id_atributo_inicial": attr_id,
            "nombre": "Articulo",
            "posicion_x": 50,
            "posicion_y": 80,
            "ancho": 240,
        },
    }

    # 1. Creación inicial
    res1 = client.post(
        f"/api/diagramas/{diagrama_id}/operaciones",
        headers={"Idempotency-Key": action_id},
        json=payload,
    )
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["action_id"] == action_id
    assert len(data1["efectos"]["clases_actualizadas"]) == 1

    # 2. Replay idéntico -> 200 con mismo recibo
    res2 = client.post(
        f"/api/diagramas/{diagrama_id}/operaciones",
        headers={"Idempotency-Key": action_id},
        json=payload,
    )
    assert res2.status_code == 200
    assert res2.json() == data1

    # 3. Mismo action_id con distinta huella -> 409
    res3 = client.post(
        f"/api/diagramas/{diagrama_id}/operaciones",
        headers={"Idempotency-Key": action_id},
        json={"tipo": "CREAR_CLASE", "datos": {"nombre": "Modificado"}},
    )
    assert res3.status_code == 409


def test_operaciones_catalogo_completo(client):
    _, diagrama_id = _crear_diagrama(client)

    # 1. CREAR_CLASE C1 y C2
    c1_id = str(uuid.uuid4())
    c1_pk = str(uuid.uuid4())
    client.post(
        f"/api/diagramas/{diagrama_id}/operaciones",
        headers={"Idempotency-Key": str(uuid.uuid4())},
        json={
            "tipo": "CREAR_CLASE",
            "datos": {
                "id_clase": c1_id,
                "id_atributo_inicial": c1_pk,
                "nombre": "Empresa",
                "posicion_x": 100,
                "posicion_y": 100,
            },
        },
    )

    c2_id = str(uuid.uuid4())
    c2_pk = str(uuid.uuid4())
    client.post(
        f"/api/diagramas/{diagrama_id}/operaciones",
        headers={"Idempotency-Key": str(uuid.uuid4())},
        json={
            "tipo": "CREAR_CLASE",
            "datos": {
                "id_clase": c2_id,
                "id_atributo_inicial": c2_pk,
                "nombre": "Empleado",
                "posicion_x": 400,
                "posicion_y": 100,
            },
        },
    )

    # 2. ACTUALIZAR_CLASE C1
    res_upd = client.post(
        f"/api/diagramas/{diagrama_id}/operaciones",
        headers={"Idempotency-Key": str(uuid.uuid4())},
        json={
            "tipo": "ACTUALIZAR_CLASE",
            "datos": {"id_clase": c1_id, "nombre": "EmpresaCorp", "posicion_x": 120},
        },
    )
    assert res_upd.status_code == 200
    assert res_upd.json()["efectos"]["clases_actualizadas"][0]["nombre"] == "EmpresaCorp"

    # 3. CREAR_ATRIBUTO en C1
    a_extra_id = str(uuid.uuid4())
    res_attr = client.post(
        f"/api/diagramas/{diagrama_id}/operaciones",
        headers={"Idempotency-Key": str(uuid.uuid4())},
        json={
            "tipo": "CREAR_ATRIBUTO",
            "datos": {
                "id_atributo": a_extra_id,
                "id_clase": c1_id,
                "nombre": "razon_social",
                "tipo_dato": "varchar",
                "longitud": 150,
            },
        },
    )
    assert res_attr.status_code == 200
    assert len(res_attr.json()["efectos"]["clases_actualizadas"][0]["atributos"]) == 2

    # 4. ACTUALIZAR_ATRIBUTO
    res_attr_upd = client.post(
        f"/api/diagramas/{diagrama_id}/operaciones",
        headers={"Idempotency-Key": str(uuid.uuid4())},
        json={
            "tipo": "ACTUALIZAR_ATRIBUTO",
            "datos": {
                "id_clase": c1_id,
                "id_atributo": a_extra_id,
                "nombre": "razon_social_editada",
            },
        },
    )
    assert res_attr_upd.status_code == 200

    # 5. CREAR_RELACION
    rel_id = str(uuid.uuid4())
    ref_id = str(uuid.uuid4())
    fk_attr_id = str(uuid.uuid4())
    res_rel = client.post(
        f"/api/diagramas/{diagrama_id}/operaciones",
        headers={"Idempotency-Key": str(uuid.uuid4())},
        json={
            "tipo": "CREAR_RELACION",
            "datos": {
                "id_relacion": rel_id,
                "id_clase_origen": c1_id,
                "id_clase_destino": c2_id,
                "tipo_relacion": "asociacion",
                "cardinalidad_origen": "1",
                "cardinalidad_destino": "0..*",
                "conector_origen": "right",
                "conector_destino": "left",
                "nombre": "Emplea",
                "materializacion_fk": [
                    {
                        "id_referencia_fk": ref_id,
                        "id_clase_fk": c2_id,
                        "id_atributo_referenciado": c1_pk,
                        "atributo_fk_nuevo": {
                            "id_atributo": fk_attr_id,
                            "nombre": "empresa_id",
                            "tipo_dato": "integer",
                            "permite_nulo": False,
                        },
                        "on_delete": "RESTRICT",
                        "on_update": "RESTRICT",
                    }
                ],
            },
        },
    )
    assert res_rel.status_code == 200
    assert len(res_rel.json()["efectos"]["relaciones_actualizadas"]) == 1

    # 6. RENOMBRAR_RELACION
    res_renom = client.post(
        f"/api/diagramas/{diagrama_id}/operaciones",
        headers={"Idempotency-Key": str(uuid.uuid4())},
        json={
            "tipo": "RENOMBRAR_RELACION",
            "datos": {"id_relacion": rel_id, "nombre": "Contrata"},
        },
    )
    assert res_renom.status_code == 200
    assert res_renom.json()["efectos"]["relaciones_actualizadas"][0]["nombre"] == "Contrata"

    # 7. ELIMINAR_RELACION
    res_del_rel = client.post(
        f"/api/diagramas/{diagrama_id}/operaciones",
        headers={"Idempotency-Key": str(uuid.uuid4())},
        json={
            "tipo": "ELIMINAR_RELACION",
            "datos": {"id_relacion": rel_id},
        },
    )
    assert res_del_rel.status_code == 200
    assert rel_id in res_del_rel.json()["efectos"]["relaciones_eliminadas"]

    # 8. ELIMINAR_ATRIBUTO
    res_del_attr = client.post(
        f"/api/diagramas/{diagrama_id}/operaciones",
        headers={"Idempotency-Key": str(uuid.uuid4())},
        json={
            "tipo": "ELIMINAR_ATRIBUTO",
            "datos": {"id_clase": c1_id, "id_atributo": a_extra_id},
        },
    )
    assert res_del_attr.status_code == 200

    # 9. ELIMINAR_CLASE con replay idempotente
    action_del_c = str(uuid.uuid4())
    res_del_c = client.post(
        f"/api/diagramas/{diagrama_id}/operaciones",
        headers={"Idempotency-Key": action_del_c},
        json={"tipo": "ELIMINAR_CLASE", "datos": {"id_clase": c1_id}},
    )
    assert res_del_c.status_code == 200
    assert c1_id in res_del_c.json()["efectos"]["clases_eliminadas"]

    # Replay de eliminación retorna recibo previo (200), no 404
    res_del_c_replay = client.post(
        f"/api/diagramas/{diagrama_id}/operaciones",
        headers={"Idempotency-Key": action_del_c},
        json={"tipo": "ELIMINAR_CLASE", "datos": {"id_clase": c1_id}},
    )
    assert res_del_c_replay.status_code == 200
    assert res_del_c_replay.json() == res_del_c.json()


def test_operacion_falla_atomica_sin_residuos(client):
    _, diagrama_id = _crear_diagrama(client)
    c1_id = str(uuid.uuid4())
    c1_pk = str(uuid.uuid4())
    client.post(
        f"/api/diagramas/{diagrama_id}/operaciones",
        headers={"Idempotency-Key": str(uuid.uuid4())},
        json={
            "tipo": "CREAR_CLASE",
            "datos": {
                "id_clase": c1_id,
                "id_atributo_inicial": c1_pk,
                "nombre": "PruebaFalla",
            },
        },
    )

    # Intentar eliminar la PK inicial a través de ELIMINAR_ATRIBUTO debe fallar
    action_fallo = str(uuid.uuid4())
    res_fallo = client.post(
        f"/api/diagramas/{diagrama_id}/operaciones",
        headers={"Idempotency-Key": action_fallo},
        json={
            "tipo": "ELIMINAR_ATRIBUTO",
            "datos": {"id_clase": c1_id, "id_atributo": c1_pk},
        },
    )
    assert res_fallo.status_code == 400
    assert res_fallo.json()["error"]["code"] == "LLAVE_PRIMARIA_PROTEGIDA"

    # La acción fallida no generó confirmación previa
    # La PK sigue intacta
    clase_check = client.get(f"/api/diagramas/{diagrama_id}/clases/{c1_id}").json()
    assert len(clase_check["atributos"]) == 1
    assert clase_check["atributos"][0]["id"] == c1_pk
