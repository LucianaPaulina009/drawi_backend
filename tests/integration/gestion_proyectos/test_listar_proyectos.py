from uuid import UUID
from sqlmodel import Session

from app.core.security.auth import get_current_user
from app.main import app
from app.modules.gestion_proyectos.infrastructure.persistence.models.proyecto_favorito_model import (
    ProyectoFavoritoModel,
)
from app.modules.gestion_proyectos.infrastructure.persistence.models.proyecto_model import (
    ProyectoModel,
)


def test_listado_aislamiento_por_usuario(client, usuario_autenticado, usuario_secundario, session: Session):
    # Usuario 1 crea 2 proyectos
    client.post("/api/proyectos/crear")
    client.post("/api/proyectos/crear")

    # Usuario 2 crea 1 proyecto
    app.dependency_overrides[get_current_user] = lambda: usuario_secundario
    client.post("/api/proyectos/crear")

    # Listado para usuario 2 debe tener solo 1 proyecto
    res_user2 = client.get("/api/proyectos/listado")
    assert res_user2.status_code == 200
    assert len(res_user2.json()["items"]) == 1

    # Regresar a usuario 1
    app.dependency_overrides[get_current_user] = lambda: usuario_autenticado
    res_user1 = client.get("/api/proyectos/listado")
    assert res_user1.status_code == 200
    assert len(res_user1.json()["items"]) == 2


def test_listado_excluye_proyectos_eliminados_logicamente(client, session: Session):
    client.post("/api/proyectos/crear")
    proyecto_id = client.get("/api/proyectos/listado").json()["items"][0]["id"]

    # Eliminar lógicamente en BD
    modelo = session.get(ProyectoModel, UUID(proyecto_id))
    assert modelo is not None
    modelo.eliminar_logicamente()
    session.add(modelo)
    session.commit()

    res_list = client.get("/api/proyectos/listado")
    assert res_list.status_code == 200
    assert len(res_list.json()["items"]) == 0


def test_listado_proyeccion_es_favorito(client, session: Session):
    res1 = client.post("/api/proyectos/crear")
    slug1 = res1.json()["slug"]
    res2 = client.post("/api/proyectos/crear")
    slug2 = res2.json()["slug"]

    items_init = client.get("/api/proyectos/listado").json()["items"]
    id1 = next(i["id"] for i in items_init if i["slug"] == slug1)
    id2 = next(i["id"] for i in items_init if i["slug"] == slug2)

    # Marcar proyecto 1 como favorito directamente en BD
    fav = ProyectoFavoritoModel(
        usuario_id="usuario-propietario-1",
        proyecto_id=UUID(id1),
    )
    session.add(fav)
    session.commit()

    res_list = client.get("/api/proyectos/listado")
    assert res_list.status_code == 200
    items = res_list.json()["items"]
    assert len(items) == 2

    # Encontrar los items
    item_fav = next(i for i in items if i["id"] == id1)
    item_no_fav = next(i for i in items if i["id"] == id2)

    assert item_fav["es_favorito"] is True
    assert item_no_fav["es_favorito"] is False

    # Si se elimina lógicamente el favorito, vuelve a ser False
    fav.eliminar_logicamente()
    session.add(fav)
    session.commit()

    res_list_despues = client.get("/api/proyectos/listado")
    item_fav_despues = next(i for i in res_list_despues.json()["items"] if i["id"] == id1)
    assert item_fav_despues["es_favorito"] is False
