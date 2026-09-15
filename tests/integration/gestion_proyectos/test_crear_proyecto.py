import pytest
from sqlmodel import Session, select

from app.core.security.auth import get_current_user
from app.main import app
from app.modules.gestion_proyectos.infrastructure.persistence.models.proyecto_model import (
    ProyectoModel,
)
from app.modules.diagramas.infrastructure.persistence.models.diagrama_model import (
    DiagramaModel,
)
from app.modules.gestion_proyectos.infrastructure.api.routers import proyecto_router


def test_creacion_proyectos_consecutivos_y_persistencia(client, session: Session):
    # Primer proyecto
    res1 = client.post("/api/proyectos/crear")
    assert res1.status_code == 201
    p1 = res1.json()
    assert p1 == {"slug": "nuevo-proyecto-0"}

    # Segundo proyecto
    res2 = client.post("/api/proyectos/crear")
    assert res2.status_code == 201
    p2 = res2.json()
    assert p2 == {"slug": "nuevo-proyecto-1"}

    # Verificar persistencia en base de datos
    proyectos_bd = session.exec(select(ProyectoModel)).all()
    assert len(proyectos_bd) == 2
    assert {p.nombre for p in proyectos_bd} == {"Nuevo Proyecto 0", "Nuevo Proyecto 1"}
    diagramas_bd = session.exec(select(DiagramaModel)).all()
    assert len(diagramas_bd) == 2
    assert all(diagrama.nombre == "Página 1" for diagrama in diagramas_bd)
    assert all(diagrama.numero == 1 for diagrama in diagramas_bd)


def test_creacion_aislamiento_por_usuario(client, usuario_secundario, session: Session):
    # Usuario 1 crea su primer proyecto
    res1 = client.post("/api/proyectos/crear")
    assert res1.status_code == 201
    assert res1.json() == {"slug": "nuevo-proyecto-0"}

    # Cambiar a usuario secundario
    app.dependency_overrides[get_current_user] = lambda: usuario_secundario

    res2 = client.post("/api/proyectos/crear")
    assert res2.status_code == 201
    # Debe comenzar en 0 para el nuevo usuario
    assert res2.json() == {"slug": "nuevo-proyecto-0"}

    # Verificar que en BD hay 2 proyectos con distintos propietarios
    p_user1 = session.exec(
        select(ProyectoModel).where(ProyectoModel.propietario_id == "usuario-propietario-1")
    ).all()
    p_user2 = session.exec(
        select(ProyectoModel).where(ProyectoModel.propietario_id == usuario_secundario.user_id)
    ).all()

    assert len(p_user1) == 1
    assert len(p_user2) == 1


def test_fallo_al_crear_pagina_inicial_revierte_el_proyecto(
    client,
    session: Session,
    monkeypatch,
):
    def fallar_guardado_diagrama(self, diagrama) -> None:
        raise RuntimeError("fallo de persistencia simulado")

    monkeypatch.setattr(
        proyecto_router.SQLModelDiagramaRepository,
        "guardar",
        fallar_guardado_diagrama,
    )

    with pytest.raises(RuntimeError, match="fallo de persistencia simulado"):
        client.post("/api/proyectos/crear")

    session.expire_all()
    assert session.exec(select(ProyectoModel)).all() == []
    assert session.exec(select(DiagramaModel)).all() == []
