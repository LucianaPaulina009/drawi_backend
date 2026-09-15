from uuid import UUID
from sqlmodel import Session

from app.core.security.auth import get_current_user
from app.main import app
from app.modules.gestion_proyectos.infrastructure.persistence.models.proyecto_model import (
    ProyectoModel,
)


def test_quickstart_escenario_completo(
    client, usuario_autenticado, usuario_secundario, session: Session
):
    """
    Ejecución secuencial de los 5 escenarios de validación definidos en quickstart.md.
    """
    # ── 1. Crear proyectos consecutivos ──────────────────────────────────────
    res1 = client.post("/api/proyectos/crear")
    assert res1.status_code == 201
    p1 = res1.json()
    assert p1 == {"slug": "nuevo-proyecto-0"}

    res2 = client.post("/api/proyectos/crear")
    assert res2.status_code == 201
    p2 = res2.json()
    assert p2 == {"slug": "nuevo-proyecto-1"}
    assert p1["slug"] != p2["slug"]

    # ── 2. Listar todos y solo favoritos ─────────────────────────────────────
    # Listado general
    res_list = client.get("/api/proyectos/listado")
    assert res_list.status_code == 200
    items_list = res_list.json()["items"]
    assert len(items_list) == 2

    id_1 = next(i["id"] for i in items_list if i["slug"] == p1["slug"])
    id_2 = next(i["id"] for i in items_list if i["slug"] == p2["slug"])

    # Marcar el primer proyecto como favorito
    res_fav = client.post(f"/api/proyectos/{id_1}/agregar_favorito")
    assert res_fav.status_code == 204

    # Listado filtrado con favoritos=true
    res_favs = client.get("/api/proyectos/listado?favoritos=true")
    assert res_favs.status_code == 200
    fav_items = res_favs.json()["items"]
    assert len(fav_items) == 1
    assert fav_items[0]["id"] == id_1
    assert fav_items[0]["es_favorito"] is True

    # Listado sin filtro
    res_todos = client.get("/api/proyectos/listado")
    assert len(res_todos.json()["items"]) == 2
    item_1 = next(i for i in res_todos.json()["items"] if i["id"] == id_1)
    item_2 = next(i for i in res_todos.json()["items"] if i["id"] == id_2)
    assert item_1["es_favorito"] is True
    assert item_2["es_favorito"] is False
    assert "page" not in res_todos.json()

    # ── 3. Actualizar y regenerar slug ───────────────────────────────────────
    res_patch = client.patch(
        f"/api/proyectos/{id_1}/actualizar",
        json={"nombre": "Plan Trimestral", "color": "verde", "icono": "estrella"},
    )
    assert res_patch.status_code == 204

    res_list_actualizado = client.get("/api/proyectos/listado")
    item_1_act = next(i for i in res_list_actualizado.json()["items"] if i["id"] == id_1)
    assert item_1_act["nombre"] == "Plan Trimestral"
    assert item_1_act["color"] == "verde"
    assert item_1_act["icono"] == "estrella"
    assert item_1_act["slug"] == "plan-trimestral"

    # Validar rechazos por nombre vacío y > 40 chars
    res_bad_empty = client.patch(f"/api/proyectos/{id_1}/actualizar", json={"nombre": ""})
    assert res_bad_empty.status_code == 400
    assert res_bad_empty.json()["error"]["code"] == "NOMBRE_PROYECTO_INVALIDO"

    res_bad_long = client.patch(f"/api/proyectos/{id_1}/actualizar", json={"nombre": "A" * 41})
    assert res_bad_long.status_code == 400
    assert res_bad_long.json()["error"]["code"] == "NOMBRE_PROYECTO_INVALIDO"

    # ── 4. Desmarcar y eliminar ──────────────────────────────────────────────
    res_unfav = client.post(f"/api/proyectos/{id_1}/desmarcar_favorito")
    assert res_unfav.status_code == 204

    # Verificar que el filtro de favoritos ya no contiene el proyecto y el total sí
    assert len(client.get("/api/proyectos/listado?favoritos=true").json()["items"]) == 0
    assert len(client.get("/api/proyectos/listado").json()["items"]) == 2

    # Eliminar proyecto
    res_del = client.delete(f"/api/proyectos/{id_1}/eliminar")
    assert res_del.status_code == 204

    # Ya no aparece en listado total ni en filtrado
    assert not any(i["id"] == id_1 for i in client.get("/api/proyectos/listado").json()["items"])
    assert not any(i["id"] == id_1 for i in client.get("/api/proyectos/listado?favoritos=true").json()["items"])

    # Verificación de borrado lógico en BD
    modelo = session.get(ProyectoModel, UUID(id_1))
    assert modelo is not None
    assert modelo.fecha_eliminacion is not None

    # ── 5. Aislamiento por usuario ───────────────────────────────────────────
    # Proyecto 2 pertenece a Usuario 1. Usuario 2 intenta mutarlo.
    app.dependency_overrides[get_current_user] = lambda: usuario_secundario

    res_patch_ajeno = client.patch(f"/api/proyectos/{id_2}/actualizar", json={"color": "azul"})
    assert res_patch_ajeno.status_code == 404
    assert res_patch_ajeno.json()["error"]["code"] == "PROYECTO_NO_ENCONTRADO"

    res_del_ajeno = client.delete(f"/api/proyectos/{id_2}/eliminar")
    assert res_del_ajeno.status_code == 404
    assert res_del_ajeno.json()["error"]["code"] == "PROYECTO_NO_ENCONTRADO"

    res_fav_ajeno = client.post(f"/api/proyectos/{id_2}/agregar_favorito")
    assert res_fav_ajeno.status_code == 404
    assert res_fav_ajeno.json()["error"]["code"] == "PROYECTO_NO_ENCONTRADO"

    res_unfav_ajeno = client.post(f"/api/proyectos/{id_2}/desmarcar_favorito")
    assert res_unfav_ajeno.status_code == 404
    assert res_unfav_ajeno.json()["error"]["code"] == "PROYECTO_NO_ENCONTRADO"

    # Restaurar override
    app.dependency_overrides[get_current_user] = lambda: usuario_autenticado
