from uuid import uuid4
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.modules.diagramas.infrastructure.persistence.models.diagrama_model import DiagramaModel
from app.modules.gestion_proyectos.infrastructure.persistence.models.proyecto_model import ProyectoModel
from app.modules.inteligencia_artificial.application.ports.providers.proveedor_ia import (
    ProveedorIa,
    ResultadoProveedorIa,
)
from app.modules.inteligencia_artificial.infrastructure.api.routers.interaccion_ia_router import (
    set_proveedor_ia_override,
)
from app.shared.infrastructure.db.better_auth import BetterAuthUser


class FakeRouterProveedor(ProveedorIa):
    def generar_respuesta(
        self,
        *,
        modelo: str,
        prompt_sistema: str,
        mensaje_usuario: str,
        temperatura: float = 0.2,
    ) -> ResultadoProveedorIa:
        return ResultadoProveedorIa(
            texto_respuesta='{"respuesta_usuario": "Hola desde la API de DRAWI", "acciones": []}',
            modelo=modelo,
        )


def test_interacciones_ia_api_post_y_get(client: TestClient, session: Session):
    usuario = BetterAuthUser(id="usuario-propietario-1", name="Prop", email="propietario@drawi.com", email_verified=True)
    session.add(usuario)
    session.commit()

    proyecto = ProyectoModel(propietario_id=usuario.id, nombre="Proy API IA", color="azul", icono="caja", slug="proy-api-ia")
    session.add(proyecto)
    session.commit()

    diagrama = DiagramaModel(id_proyecto=proyecto.id, nombre="Pagina 1", numero=1)
    session.add(diagrama)
    session.commit()

    set_proveedor_ia_override(FakeRouterProveedor())

    clave = str(uuid4())
    # 1. POST para enviar mensaje
    res_post = client.post(
        f"/api/diagramas/{diagrama.id}/interacciones-ia",
        json={"texto": "¿Cómo normalizar esta tabla?", "claveIdempotencia": clave},
    )
    assert res_post.status_code == 201, res_post.text
    data_post = res_post.json()
    assert data_post["entradaUsuario"] == "¿Cómo normalizar esta tabla?"
    assert data_post["respuestaIa"] == "Hola desde la API de DRAWI"
    assert data_post["estado"] == "completado"
    assert data_post["creadoEn"] is not None
    t1_creado_en = data_post["creadoEn"]

    # 2. GET para listar historial en T2
    res_get = client.get(f"/api/diagramas/{diagrama.id}/interacciones-ia")
    assert res_get.status_code == 200, res_get.text
    data_get = res_get.json()
    assert len(data_get["items"]) >= 1
    assert data_get["items"][0]["id"] == data_post["id"]
    # Verificar que creadoEn persiste exactamente la fecha original de T1
    assert data_get["items"][0]["creadoEn"] == t1_creado_en

    set_proveedor_ia_override(None)


def test_creado_en_persiste_timestamp_original(client: TestClient, session: Session):
    usuario = BetterAuthUser(id="usuario-propietario-1", name="PropT1", email="t1@drawi.com", email_verified=True)
    session.add(usuario)
    session.commit()

    proyecto = ProyectoModel(propietario_id=usuario.id, nombre="Proy T1", color="azul", icono="caja", slug="proy-t1")
    session.add(proyecto)
    session.commit()

    diagrama = DiagramaModel(id_proyecto=proyecto.id, nombre="Pagina 1", numero=1)
    session.add(diagrama)
    session.commit()

    set_proveedor_ia_override(FakeRouterProveedor())

    # Crear interacción en T1
    res_crear = client.post(
        f"/api/diagramas/{diagrama.id}/interacciones-ia",
        json={"texto": "Consulta en T1", "claveIdempotencia": str(uuid4())},
    )
    assert res_crear.status_code == 201
    timestamp_t1 = res_crear.json()["creadoEn"]
    assert timestamp_t1 is not None

    # Consultar posteriormente en T2
    res_consultar = client.get(f"/api/diagramas/{diagrama.id}/interacciones-ia")
    assert res_consultar.status_code == 200
    items = res_consultar.json()["items"]
    assert len(items) == 1
    assert items[0]["creadoEn"] == timestamp_t1

    set_proveedor_ia_override(None)
