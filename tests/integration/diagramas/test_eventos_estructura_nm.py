import uuid
import pytest


def _crear_diagrama(client) -> tuple[str, str]:
    assert client.post("/api/proyectos/crear").status_code == 201
    proyecto_id = client.get("/api/proyectos/listado").json()["items"][0]["id"]
    diagrama_id = client.get(
        f"/api/proyectos/{proyecto_id}/diagramas"
    ).json()["items"][0]["id"]
    return proyecto_id, diagrama_id


def _crear_clase(client, diagrama_id: str, nombre: str, pos_x: float = 0, pos_y: float = 0) -> tuple[str, str]:
    clase_id = str(uuid.uuid4())
    pk_id = str(uuid.uuid4())
    res = client.post(
        f"/api/diagramas/{diagrama_id}/operaciones",
        headers={"Idempotency-Key": str(uuid.uuid4())},
        json={
            "tipo": "CREAR_CLASE",
            "datos": {
                "id_clase": clase_id,
                "id_atributo_inicial": pk_id,
                "nombre": nombre,
                "posicion_x": pos_x,
                "posicion_y": pos_y,
                "ancho": 220,
            },
        },
    )
    assert res.status_code == 200
    return clase_id, pk_id


def test_crear_estructura_nm_unidad_atomica_y_replay(client):
    _, diagrama_id = _crear_diagrama(client)
    c1_id, c1_pk = _crear_clase(client, diagrama_id, "Estudiante", 100, 100)
    c2_id, c2_pk = _crear_clase(client, diagrama_id, "Curso", 600, 100)

    nm_id = str(uuid.uuid4())
    intermedia_id = str(uuid.uuid4())
    intermedia_pk = str(uuid.uuid4())
    fk_origen_id = str(uuid.uuid4())
    fk_destino_id = str(uuid.uuid4())
    rel_origen_id = str(uuid.uuid4())
    rel_destino_id = str(uuid.uuid4())
    ref_origen_id = str(uuid.uuid4())
    ref_destino_id = str(uuid.uuid4())
    action_nm = str(uuid.uuid4())

    payload_nm = {
        "tipo": "CREAR_ESTRUCTURA_NM",
        "datos": {
            "id_estructura": nm_id,
            "id_clase_origen": c1_id,
            "id_clase_destino": c2_id,
            "id_clase_intermedia": intermedia_id,
            "id_atributo_inicial": intermedia_pk,
            "id_atributo_fk_origen": fk_origen_id,
            "id_atributo_fk_destino": fk_destino_id,
            "id_relacion_origen": rel_origen_id,
            "id_relacion_destino": rel_destino_id,
            "id_referencia_fk_origen": ref_origen_id,
            "id_referencia_fk_destino": ref_destino_id,
            "id_atributo_referenciado_origen": c1_pk,
            "id_atributo_referenciado_destino": c2_pk,
            "nombre_intermedia": "Inscripcion",
            "posicion_x": 350,
            "posicion_y": 100,
            "ancho": 260,
        },
    }

    # 1. Creación atómica
    res = client.post(
        f"/api/diagramas/{diagrama_id}/operaciones",
        headers={"Idempotency-Key": action_nm},
        json=payload_nm,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["action_id"] == action_nm
    assert len(data["efectos"]["clases_actualizadas"]) == 1
    assert data["efectos"]["clases_actualizadas"][0]["id"] == intermedia_id
    assert len(data["efectos"]["relaciones_actualizadas"]) == 2
    assert len(data["efectos"]["estructuras_nm_actualizadas"]) == 1

    # Verificar que la clase intermedia tiene su PK única y 2 FKs de sistema
    intermedia = client.get(f"/api/diagramas/{diagrama_id}/clases/{intermedia_id}").json()
    assert intermedia["nombre"] == "Inscripcion"
    assert len(intermedia["atributos"]) == 3
    pk_attr = next(a for a in intermedia["atributos"] if a["es_llave_primaria"])
    assert pk_attr["id"] == intermedia_pk
    assert pk_attr["procedencia"] == "sistema_clase"

    fks = [a for a in intermedia["atributos"] if not a["es_llave_primaria"]]
    assert len(fks) == 2
    for fk in fks:
      assert fk["procedencia"] == "sistema_fk"

    # 2. Replay idempotente con mismo action_id y payload
    res_replay = client.post(
        f"/api/diagramas/{diagrama_id}/operaciones",
        headers={"Idempotency-Key": action_nm},
        json=payload_nm,
    )
    assert res_replay.status_code == 200
    assert res_replay.json() == data

    # 3. Mismo action_id con payload alterado devuelve 409
    payload_alterado = dict(payload_nm)
    payload_alterado["datos"] = dict(payload_nm["datos"])
    payload_alterado["datos"]["nombre_intermedia"] = "MatriculaDistinta"
    res_conflicto = client.post(
        f"/api/diagramas/{diagrama_id}/operaciones",
        headers={"Idempotency-Key": action_nm},
        json=payload_alterado,
    )
    assert res_conflicto.status_code == 409


def test_eliminar_estructura_nm_cascada_limpia(client):
    _, diagrama_id = _crear_diagrama(client)
    c1_id, c1_pk = _crear_clase(client, diagrama_id, "Medico")
    c2_id, c2_pk = _crear_clase(client, diagrama_id, "Paciente")

    nm_id = str(uuid.uuid4())
    intermedia_id = str(uuid.uuid4())

    client.post(
        f"/api/diagramas/{diagrama_id}/operaciones",
        headers={"Idempotency-Key": str(uuid.uuid4())},
        json={
            "tipo": "CREAR_ESTRUCTURA_NM",
            "datos": {
                "id_estructura": nm_id,
                "id_clase_origen": c1_id,
                "id_clase_destino": c2_id,
                "id_clase_intermedia": intermedia_id,
                "id_atributo_inicial": str(uuid.uuid4()),
                "id_atributo_fk_origen": str(uuid.uuid4()),
                "id_atributo_fk_destino": str(uuid.uuid4()),
                "id_relacion_origen": str(uuid.uuid4()),
                "id_relacion_destino": str(uuid.uuid4()),
                "id_referencia_fk_origen": str(uuid.uuid4()),
                "id_referencia_fk_destino": str(uuid.uuid4()),
                "id_atributo_referenciado_origen": c1_pk,
                "id_atributo_referenciado_destino": c2_pk,
                "nombre_intermedia": "Cita",
            },
        },
    )

    # Eliminar estructura N:M
    action_del = str(uuid.uuid4())
    res_del = client.post(
        f"/api/diagramas/{diagrama_id}/operaciones",
        headers={"Idempotency-Key": action_del},
        json={
            "tipo": "ELIMINAR_ESTRUCTURA_NM",
            "datos": {"id_estructura": nm_id},
        },
    )
    assert res_del.status_code == 200
    efectos = res_del.json()["efectos"]
    assert nm_id in efectos["estructuras_nm_eliminadas"]
    assert intermedia_id in efectos["clases_eliminadas"]
    assert len(efectos["relaciones_eliminadas"]) == 2

    # Clases originales sobreviven intactas
    assert client.get(f"/api/diagramas/{diagrama_id}/clases/{c1_id}").status_code == 200
    assert client.get(f"/api/diagramas/{diagrama_id}/clases/{c2_id}").status_code == 200

    # Clase intermedia eliminada
    assert client.get(f"/api/diagramas/{diagrama_id}/clases/{intermedia_id}").status_code == 404

    # Replay de eliminación retorna recibo previo (200)
    res_replay_del = client.post(
        f"/api/diagramas/{diagrama_id}/operaciones",
        headers={"Idempotency-Key": action_del},
        json={
            "tipo": "ELIMINAR_ESTRUCTURA_NM",
            "datos": {"id_estructura": nm_id},
        },
    )
    assert res_replay_del.status_code == 200
    assert res_replay_del.json() == res_del.json()


def test_auto_estructura_nm_recursiva(client):
    _, diagrama_id = _crear_diagrama(client)
    c1_id, c1_pk = _crear_clase(client, diagrama_id, "Persona")

    nm_id = str(uuid.uuid4())
    intermedia_id = str(uuid.uuid4())

    res = client.post(
        f"/api/diagramas/{diagrama_id}/operaciones",
        headers={"Idempotency-Key": str(uuid.uuid4())},
        json={
            "tipo": "CREAR_ESTRUCTURA_NM",
            "datos": {
                "id_estructura": nm_id,
                "id_clase_origen": c1_id,
                "id_clase_destino": c1_id,
                "id_clase_intermedia": intermedia_id,
                "id_atributo_inicial": str(uuid.uuid4()),
                "id_atributo_fk_origen": str(uuid.uuid4()),
                "id_atributo_fk_destino": str(uuid.uuid4()),
                "id_relacion_origen": str(uuid.uuid4()),
                "id_relacion_destino": str(uuid.uuid4()),
                "id_referencia_fk_origen": str(uuid.uuid4()),
                "id_referencia_fk_destino": str(uuid.uuid4()),
                "id_atributo_referenciado_origen": c1_pk,
                "id_atributo_referenciado_destino": c1_pk,
                "nombre_intermedia": "Parentesco",
            },
        },
    )
    assert res.status_code == 200
    intermedia = client.get(f"/api/diagramas/{diagrama_id}/clases/{intermedia_id}").json()
    assert intermedia["nombre"] == "Parentesco"
    assert len(intermedia["atributos"]) == 3


def test_intermedia_atributos_manuales_eliminados_solo_con_contenedor(client):
    _, diagrama_id = _crear_diagrama(client)
    c1_id, c1_pk = _crear_clase(client, diagrama_id, "Autor")
    c2_id, c2_pk = _crear_clase(client, diagrama_id, "Libro")

    intermedia_id = str(uuid.uuid4())
    client.post(
        f"/api/diagramas/{diagrama_id}/operaciones",
        headers={"Idempotency-Key": str(uuid.uuid4())},
        json={
            "tipo": "CREAR_ESTRUCTURA_NM",
            "datos": {
                "id_estructura": str(uuid.uuid4()),
                "id_clase_origen": c1_id,
                "id_clase_destino": c2_id,
                "id_clase_intermedia": intermedia_id,
                "id_atributo_inicial": str(uuid.uuid4()),
                "id_atributo_fk_origen": str(uuid.uuid4()),
                "id_atributo_fk_destino": str(uuid.uuid4()),
                "id_relacion_origen": str(uuid.uuid4()),
                "id_relacion_destino": str(uuid.uuid4()),
                "id_referencia_fk_origen": str(uuid.uuid4()),
                "id_referencia_fk_destino": str(uuid.uuid4()),
                "id_atributo_referenciado_origen": c1_pk,
                "id_atributo_referenciado_destino": c2_pk,
                "nombre_intermedia": "Autoria",
            },
        },
    )

    # Agregar atributo manual normal a la intermedia
    attr_manual_id = str(uuid.uuid4())
    res_attr = client.post(
        f"/api/diagramas/{diagrama_id}/operaciones",
        headers={"Idempotency-Key": str(uuid.uuid4())},
        json={
            "tipo": "CREAR_ATRIBUTO",
            "datos": {
                "id_clase": intermedia_id,
                "id_atributo": attr_manual_id,
                "nombre": "porcentaje_regalias",
                "tipo_dato": "decimal",
            },
        },
    )
    assert res_attr.status_code == 200

    intermedia = client.get(f"/api/diagramas/{diagrama_id}/clases/{intermedia_id}").json()
    assert len(intermedia["atributos"]) == 4

    # Eliminar solo el atributo manual
    res_del_attr = client.post(
        f"/api/diagramas/{diagrama_id}/operaciones",
        headers={"Idempotency-Key": str(uuid.uuid4())},
        json={
            "tipo": "ELIMINAR_ATRIBUTO",
            "datos": {
                "id_clase": intermedia_id,
                "id_atributo": attr_manual_id,
            },
        },
    )
    assert res_del_attr.status_code == 200

    # La intermedia sigue existiendo con sus 3 atributos estructurales
    intermedia_post = client.get(f"/api/diagramas/{diagrama_id}/clases/{intermedia_id}").json()
    assert len(intermedia_post["atributos"]) == 3


def test_falla_parcial_no_deja_residuos(client):
    _, diagrama_id = _crear_diagrama(client)
    c1_id, c1_pk = _crear_clase(client, diagrama_id, "A")

    id_destino_inexistente = str(uuid.uuid4())
    intermedia_id = str(uuid.uuid4())

    res = client.post(
        f"/api/diagramas/{diagrama_id}/operaciones",
        headers={"Idempotency-Key": str(uuid.uuid4())},
        json={
            "tipo": "CREAR_ESTRUCTURA_NM",
            "datos": {
                "id_estructura": str(uuid.uuid4()),
                "id_clase_origen": c1_id,
                "id_clase_destino": id_destino_inexistente,
                "id_clase_intermedia": intermedia_id,
                "id_atributo_inicial": str(uuid.uuid4()),
                "id_atributo_fk_origen": str(uuid.uuid4()),
                "id_atributo_fk_destino": str(uuid.uuid4()),
                "id_relacion_origen": str(uuid.uuid4()),
                "id_relacion_destino": str(uuid.uuid4()),
                "id_referencia_fk_origen": str(uuid.uuid4()),
                "id_referencia_fk_destino": str(uuid.uuid4()),
                "id_atributo_referenciado_origen": c1_pk,
                "id_atributo_referenciado_destino": str(uuid.uuid4()),
                "nombre_intermedia": "IntermediaFallida",
            },
        },
    )
    assert res.status_code in [400, 404]

    # No se creó la clase intermedia ni se generaron residuos
    assert client.get(f"/api/diagramas/{diagrama_id}/clases/{intermedia_id}").status_code == 404
