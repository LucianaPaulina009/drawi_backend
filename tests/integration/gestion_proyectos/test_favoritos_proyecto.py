from uuid import UUID
from sqlmodel import Session, select

from app.core.security.auth import get_current_user
from app.main import app
from app.modules.gestion_proyectos.infrastructure.persistence.models.proyecto_favorito_model import (
    ProyectoFavoritoModel,
)


def test_ciclo_favoritos_completo(client, session: Session):
    # 1. Crear dos proyectos
    res_a = client.post("/api/proyectos/crear")
    slug_a = res_a.json()["slug"]
    res_b = client.post("/api/proyectos/crear")
    slug_b = res_b.json()["slug"]

    items = client.get("/api/proyectos/listado").json()["items"]
    id_a = next(i["id"] for i in items if i["slug"] == slug_a)
    id_b = next(i["id"] for i in items if i["slug"] == slug_b)

    # 2. Inicialmente no hay favoritos
    res_favs = client.get("/api/proyectos/listado?favoritos=true")
    assert res_favs.status_code == 200
    assert len(res_favs.json()["items"]) == 0

    # 3. Marcar A como favorito
    res_add = client.post(f"/api/proyectos/{id_a}/agregar_favorito")
    assert res_add.status_code == 204

    # 4. Listado con favoritos=true contiene A
    res_favs = client.get("/api/proyectos/listado?favoritos=true")
    assert len(res_favs.json()["items"]) == 1
    assert res_favs.json()["items"][0]["id"] == id_a

    # 5. Marcar A nuevamente (idempotencia)
    res_add_again = client.post(f"/api/proyectos/{id_a}/agregar_favorito")
    assert res_add_again.status_code == 204

    # Verificar que solo hay 1 fila en la tabla de favoritos
    filas_fav = session.exec(
        select(ProyectoFavoritoModel).where(
            ProyectoFavoritoModel.proyecto_id == UUID(id_a)
        )
    ).all()
    assert len(filas_fav) == 1

    # 6. Desmarcar A
    res_unfav = client.post(f"/api/proyectos/{id_a}/desmarcar_favorito")
    assert res_unfav.status_code == 204

    # Listado filtrado ahora está vacío
    res_favs_empty = client.get("/api/proyectos/listado?favoritos=true")
    assert len(res_favs_empty.json()["items"]) == 0

    # Listado general aún tiene A y B, pero ambos con es_favorito=False
    res_todos = client.get("/api/proyectos/listado")
    assert len(res_todos.json()["items"]) == 2
    for item in res_todos.json()["items"]:
        assert item["es_favorito"] is False

    # 7. Volver a marcar A (debe restaurar sin duplicar filas en BD)
    res_add_restaurar = client.post(f"/api/proyectos/{id_a}/agregar_favorito")
    assert res_add_restaurar.status_code == 204

    filas_fav_despues = session.exec(
        select(ProyectoFavoritoModel).where(
            ProyectoFavoritoModel.proyecto_id == UUID(id_a)
        )
    ).all()
    assert len(filas_fav_despues) == 1
    assert filas_fav_despues[0].fecha_eliminacion is None

    # Listado filtrado vuelve a tener A
    res_favs_restaurado = client.get("/api/proyectos/listado?favoritos=true")
    assert len(res_favs_restaurado.json()["items"]) == 1
    assert res_favs_restaurado.json()["items"][0]["id"] == id_a


def test_favoritos_aislamiento_y_propiedad(client, usuario_autenticado, usuario_secundario):
    # Usuario 2 crea un proyecto
    app.dependency_overrides[get_current_user] = lambda: usuario_secundario
    client.post("/api/proyectos/crear")
    proyecto_id_user2 = client.get("/api/proyectos/listado").json()["items"][0]["id"]

    # Usuario 1 intenta marcar como favorito el proyecto de Usuario 2
    app.dependency_overrides[get_current_user] = lambda: usuario_autenticado
    res_ajeno = client.post(f"/api/proyectos/{proyecto_id_user2}/agregar_favorito")
    assert res_ajeno.status_code == 404
    assert res_ajeno.json()["error"]["code"] == "PROYECTO_NO_ENCONTRADO"

    # Usuario 1 intenta desmarcar el proyecto de Usuario 2
    res_desmarcar_ajeno = client.post(f"/api/proyectos/{proyecto_id_user2}/desmarcar_favorito")
    assert res_desmarcar_ajeno.status_code == 404
    assert res_desmarcar_ajeno.json()["error"]["code"] == "PROYECTO_NO_ENCONTRADO"
