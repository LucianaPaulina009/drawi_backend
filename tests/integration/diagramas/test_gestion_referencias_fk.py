import uuid
import pytest
from app.core.security.auth import AuthUser, get_current_user
from app.main import app
from app.shared.infrastructure.db.better_auth import BetterAuthUser


def _crear_proyecto_diagrama_y_relacion(client) -> tuple[str, str, dict, dict, dict, str]:
    assert client.post("/api/proyectos/crear").status_code == 201
    proyecto_id = client.get("/api/proyectos/listado").json()["items"][0]["id"]
    diagrama_id = client.get(
        f"/api/proyectos/{proyecto_id}/diagramas"
    ).json()["items"][0]["id"]

    # Crear Clase 1 (Origen: Cliente) - ya viene con su PK "id"
    c1 = client.post(
        f"/api/diagramas/{diagrama_id}/clases",
        json={"nombre": "Cliente", "posicion_x": 10, "posicion_y": 20, "ancho": 280},
    ).json()

    # Crear Clase 2 (Destino: Pedido) con FK nullable
    c2 = client.post(
        f"/api/diagramas/{diagrama_id}/clases",
        json={"nombre": "Pedido", "posicion_x": 300, "posicion_y": 20, "ancho": 280},
    ).json()
    a2 = client.post(
        f"/api/clases/{c2['id']}/atributos",
        json={
            "tipo_dato": "integer",
            "nombre": "cliente_id",
            "es_llave_primaria": False,
            "permite_nulo": True,
            "es_unico": False,
            "orden_de_posicion": 2,
        },
    ).json()

    rel_id = str(uuid.uuid4())
    ref_id = str(uuid.uuid4())
    pk_c1 = c1["atributos"][0]["id"]
    rel = client.post(
        f"/api/diagramas/{diagrama_id}/relaciones",
        json={
            "id_relacion": rel_id,
            "id_clase_origen": c1["id"],
            "id_clase_destino": c2["id"],
            "tipo_relacion": "asociacion",
            "cardinalidad_origen": "1",
            "cardinalidad_destino": "0..*",
            "conector_origen": "right",
            "conector_destino": "left",
            "materializacion_fk": [
                {
                    "id_referencia_fk": ref_id,
                    "id_atributo_fk": a2["id"],
                    "id_atributo_referenciado": pk_c1,
                    "id_clase_fk": c2["id"],
                    "on_delete": "CASCADE",
                    "on_update": "RESTRICT",
                }
            ],
        },
    ).json()

    return proyecto_id, diagrama_id, c1, c2, rel, ref_id


def test_ciclo_de_vida_referencia_fk(client):
    proyecto_id, diagrama_id, c1, c2, rel, ref_fk_id = _crear_proyecto_diagrama_y_relacion(client)

    # Consultar detalle
    det_res = client.get(f"/api/relaciones/{rel['id']}/referencias-fk/{ref_fk_id}")
    assert det_res.status_code == 200
    assert det_res.json()["id"] == ref_fk_id

    # Listar referencias FK
    list_res = client.get(f"/api/relaciones/{rel['id']}/referencias-fk")
    assert list_res.status_code == 200
    items = list_res.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == ref_fk_id

    # Actualizar acción referencial es rechazado por ser inmutable
    patch_res = client.patch(
        f"/api/relaciones/{rel['id']}/referencias-fk/{ref_fk_id}",
        json={"on_delete": "SET_NULL"},
    )
    assert patch_res.status_code in (400, 422)

    # Eliminar
    del_res = client.delete(f"/api/relaciones/{rel['id']}/referencias-fk/{ref_fk_id}")
    assert del_res.status_code == 204

    # Verificar no encontrado
    assert client.get(f"/api/relaciones/{rel['id']}/referencias-fk/{ref_fk_id}").status_code == 404


def test_validaciones_semanticas_referencia_fk(client):
    proyecto_id, diagrama_id, c1, c2, rel, ref_fk_id = _crear_proyecto_diagrama_y_relacion(client)
    attrs_c1 = client.get(f"/api/clases/{c1['id']}/atributos").json()["items"]
    attrs_c2 = client.get(f"/api/clases/{c2['id']}/atributos").json()["items"]
    attr_ref = attrs_c1[0]
    attr_fk = [a for a in attrs_c2 if a["nombre"] == "cliente_id"][0]

    # 1. Atributo no referenciable (ni PK ni único)
    attr_no_pk = client.post(
        f"/api/clases/{c1['id']}/atributos",
        json={
            "tipo_dato": "varchar",
            "nombre": "descripcion",
            "es_llave_primaria": False,
            "permite_nulo": True,
            "es_unico": False,
            "orden_de_posicion": 2,
        },
    ).json()
    attr_fk_varchar = client.post(
        f"/api/clases/{c2['id']}/atributos",
        json={
            "tipo_dato": "varchar",
            "nombre": "desc_fk",
            "es_llave_primaria": False,
            "permite_nulo": True,
            "es_unico": False,
            "orden_de_posicion": 3,
        },
    ).json()

    res_no_ref = client.post(
        f"/api/relaciones/{rel['id']}/referencias-fk",
        json={
            "id_referencia_fk": str(uuid.uuid4()),
            "id_atributo_fk": attr_fk_varchar["id"],
            "id_atributo_referenciado": attr_no_pk["id"],
        },
    )
    assert res_no_ref.status_code == 400
    assert res_no_ref.json()["error"]["code"] == "ATRIBUTO_NO_REFERENCIABLE"

    # 2. Tipos incompatibles (integer vs varchar)
    res_incomp = client.post(
        f"/api/relaciones/{rel['id']}/referencias-fk",
        json={
            "id_referencia_fk": str(uuid.uuid4()),
            "id_atributo_fk": attr_fk_varchar["id"],
            "id_atributo_referenciado": attr_ref["id"],
        },
    )
    assert res_incomp.status_code == 400
    assert res_incomp.json()["error"]["code"] == "TIPO_ATRIBUTO_INCOMPATIBLE"

    # 3. Atributo fuera de clases participantes
    c3 = client.post(
        f"/api/diagramas/{diagrama_id}/clases",
        json={"nombre": "Tercera", "posicion_x": 10, "posicion_y": 100, "ancho": 200},
    ).json()
    # c3 ya nace con su PK 'id'
    attr_c3_pk = c3["atributos"][0]

    res_ajena = client.post(
        f"/api/relaciones/{rel['id']}/referencias-fk",
        json={
            "id_referencia_fk": str(uuid.uuid4()),
            "id_atributo_fk": attr_fk["id"],
            "id_atributo_referenciado": attr_c3_pk["id"],
        },
    )
    assert res_ajena.status_code == 400
    assert res_ajena.json()["error"]["code"] == "ATRIBUTO_NO_PERTENECE_A_CLASE_RELACION"

    # 4. SET_NULL sobre atributo no nulleable
    attr_fk_no_null = client.post(
        f"/api/clases/{c2['id']}/atributos",
        json={
            "tipo_dato": "integer",
            "nombre": "codigo_no_null",
            "es_llave_primaria": False,
            "permite_nulo": False,
            "es_unico": False,
            "orden_de_posicion": 4,
        },
    ).json()
    res_set_null_err = client.post(
        f"/api/relaciones/{rel['id']}/referencias-fk",
        json={
            "id_referencia_fk": str(uuid.uuid4()),
            "id_atributo_fk": attr_fk_no_null["id"],
            "id_atributo_referenciado": attr_ref["id"],
            "on_delete": "SET_NULL",
        },
    )
    assert res_set_null_err.status_code == 400
    assert res_set_null_err.json()["error"]["code"] == "CONFIGURACION_REFERENCIA_FK_INVALIDA"


def test_duplicidad_y_unicidad_referencia_fk(client):
    proyecto_id, diagrama_id, c1, c2, rel, ref_fk_id = _crear_proyecto_diagrama_y_relacion(client)
    attrs_c1 = client.get(f"/api/clases/{c1['id']}/atributos").json()["items"]
    attrs_c2 = client.get(f"/api/clases/{c2['id']}/atributos").json()["items"]
    attr_ref = attrs_c1[0]
    attr_fk = [a for a in attrs_c2 if a["nombre"] == "cliente_id"][0]

    # UUID duplicado usando el ref_fk_id ya creado
    res_dup_id = client.post(
        f"/api/relaciones/{rel['id']}/referencias-fk",
        json={
            "id_referencia_fk": ref_fk_id,
            "id_atributo_fk": attr_fk["id"],
            "id_atributo_referenciado": attr_ref["id"],
        },
    )
    assert res_dup_id.status_code == 409
    assert res_dup_id.json()["error"]["code"] == "REFERENCIA_FK_YA_EXISTE"

    # Mismo par con distinto UUID en la misma relación
    res_dup_par = client.post(
        f"/api/relaciones/{rel['id']}/referencias-fk",
        json={
            "id_referencia_fk": str(uuid.uuid4()),
            "id_atributo_fk": attr_fk["id"],
            "id_atributo_referenciado": attr_ref["id"],
        },
    )
    assert res_dup_par.status_code == 409
    assert res_dup_par.json()["error"]["code"] == "VINCULO_REFERENCIA_FK_DUPLICADO"


def test_cascada_eliminacion_atributo_limpia_referencia_fk(client):
    proyecto_id, diagrama_id, c1, c2, rel, ref_fk_id = _crear_proyecto_diagrama_y_relacion(client)
    attrs_c2 = client.get(f"/api/clases/{c2['id']}/atributos").json()["items"]
    attr_fk = [a for a in attrs_c2 if a["nombre"] == "cliente_id"][0]

    # Eliminar atributo FK
    del_attr_res = client.delete(f"/api/clases/{c2['id']}/atributos/{attr_fk['id']}")
    assert del_attr_res.status_code == 204

    # La referencia FK ya no debe estar disponible
    get_fk_res = client.get(f"/api/relaciones/{rel['id']}/referencias-fk/{ref_fk_id}")
    assert get_fk_res.status_code == 404


def test_purga_referencias_al_cambiar_clases_participantes_de_relacion(client):
    proyecto_id, diagrama_id, c1, c2, rel, ref_fk_id = _crear_proyecto_diagrama_y_relacion(client)

    # Crear una nueva clase C3
    c3 = client.post(
        f"/api/diagramas/{diagrama_id}/clases",
        json={"nombre": "NuevaClase", "posicion_x": 500, "posicion_y": 20, "ancho": 280},
    ).json()

    # Actualizar la relación cambiando id_clase_destino a c3 debe ser rechazado por inmutabilidad
    patch_rel = client.patch(
        f"/api/diagramas/{diagrama_id}/relaciones/{rel['id']}",
        json={"id_clase_destino": c3["id"]},
    )
    assert patch_rel.status_code in (400, 422)
