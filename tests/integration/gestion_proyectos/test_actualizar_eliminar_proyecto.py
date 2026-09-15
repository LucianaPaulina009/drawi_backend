from uuid import UUID
from sqlmodel import Session

from app.core.security.auth import get_current_user
from app.main import app
from app.modules.gestion_proyectos.infrastructure.persistence.models.proyecto_model import (
    ProyectoModel,
)


def test_actualizacion_e_impacto_en_listado(client):
    client.post("/api/proyectos/crear")
    proyecto_id = client.get("/api/proyectos/listado").json()["items"][0]["id"]

    res_patch = client.patch(
        f"/api/proyectos/{proyecto_id}/actualizar",
        json={"nombre": "Rediseño Web", "color": "azul", "icono": "estrella"},
    )
    assert res_patch.status_code == 204

    # Verificar que el listado refleja los cambios
    res_list = client.get("/api/proyectos/listado")
    item = next(i for i in res_list.json()["items"] if i["id"] == proyecto_id)
    assert item["nombre"] == "Rediseño Web"
    assert item["color"] == "azul"
    assert item["icono"] == "estrella"
    assert item["slug"] == "rediseno-web"


def test_eliminacion_logica_y_desaparicion_de_listados(client, session: Session):
    client.post("/api/proyectos/crear")
    proyecto_id = client.get("/api/proyectos/listado").json()["items"][0]["id"]

    # Marcar como favorito
    client.post(f"/api/proyectos/{proyecto_id}/agregar_favorito")

    # Eliminar proyecto
    res_del = client.delete(f"/api/proyectos/{proyecto_id}/eliminar")
    assert res_del.status_code == 204

    # No debe aparecer en listado general
    res_list = client.get("/api/proyectos/listado")
    assert not any(i["id"] == proyecto_id for i in res_list.json()["items"])

    # No debe aparecer en listado de favoritos
    res_favs = client.get("/api/proyectos/listado?favoritos=true")
    assert not any(i["id"] == proyecto_id for i in res_favs.json()["items"])

    # En la base de datos sigue existiendo con fecha_eliminacion
    modelo = session.get(ProyectoModel, UUID(proyecto_id))
    assert modelo is not None
    assert modelo.fecha_eliminacion is not None

    # Intentar actualizar o eliminar de nuevo debe devolver 404
    res_patch_del = client.patch(
        f"/api/proyectos/{proyecto_id}/actualizar",
        json={"color": "rojo"},
    )
    assert res_patch_del.status_code == 404

    res_del_del = client.delete(f"/api/proyectos/{proyecto_id}/eliminar")
    assert res_del_del.status_code == 404


def test_actualizar_eliminar_aislamiento_entre_usuarios(
    client, usuario_autenticado, usuario_secundario
):
    # Usuario 1 crea un proyecto
    client.post("/api/proyectos/crear")
    proyecto_id = client.get("/api/proyectos/listado").json()["items"][0]["id"]

    # Usuario 2 intenta actualizar el proyecto de Usuario 1
    app.dependency_overrides[get_current_user] = lambda: usuario_secundario
    res_patch = client.patch(
        f"/api/proyectos/{proyecto_id}/actualizar",
        json={"color": "verde"},
    )
    assert res_patch.status_code == 404
    assert res_patch.json()["error"]["code"] == "PROYECTO_NO_ENCONTRADO"

    # Usuario 2 intenta eliminar el proyecto de Usuario 1
    res_del = client.delete(f"/api/proyectos/{proyecto_id}/eliminar")
    assert res_del.status_code == 404
    assert res_del.json()["error"]["code"] == "PROYECTO_NO_ENCONTRADO"

    # Restaurar usuario 1
    app.dependency_overrides[get_current_user] = lambda: usuario_autenticado
