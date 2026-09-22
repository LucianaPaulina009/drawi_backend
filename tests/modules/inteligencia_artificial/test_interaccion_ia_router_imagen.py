from __future__ import annotations

import io
import json
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.modules.diagramas.infrastructure.persistence.models.diagrama_model import (
    DiagramaModel,
)
from app.modules.gestion_colaboradores.domain.value_objects.rol_colaborador import (
    RolColaborador,
)
from app.modules.gestion_colaboradores.infrastructure.persistence.models.colaborador_proyecto_model import (
    ColaboradorProyectoModel,
)
from app.modules.gestion_proyectos.infrastructure.persistence.models.proyecto_model import (
    ProyectoModel,
)
from app.modules.inteligencia_artificial.infrastructure.api.routers.interaccion_ia_router import (
    set_proveedor_ia_override,
)
from app.shared.infrastructure.db.better_auth import BetterAuthUser
from tests.modules.inteligencia_artificial.fixtures.imagen_ia_fixtures import (
    FakeProveedorIaImagen,
    PNG_VALIDO_BYTES,
)


def test_interaccion_ia_api_imagen_exito(client: TestClient, session: Session):
    usuario = BetterAuthUser(
        id="usuario-propietario-1",
        name="PropImg",
        email="propietario@drawi.com",
        email_verified=True,
    )
    session.add(usuario)
    session.commit()

    proyecto = ProyectoModel(
        propietario_id=usuario.id,
        nombre="Proy Img API",
        color="azul",
        icono="caja",
        slug="proy-img-api",
    )
    session.add(proyecto)
    session.commit()

    diagrama = DiagramaModel(id_proyecto=proyecto.id, nombre="Página 1", numero=1)
    session.add(diagrama)
    session.commit()

    json_respuesta = json.dumps({
        "clases": [
            {
                "referencia_semantica": "ref_1",
                "nombre": "Producto",
                "atributos": [
                    {"nombre": "id", "tipo_detectado": "integer", "es_pk": True},
                    {"nombre": "precio", "tipo_detectado": "decimal", "es_pk": False},
                ],
            }
        ],
        "relaciones": [],
        "advertencias": [],
    })

    fake_prov = FakeProveedorIaImagen(respuesta_json_imagen=json_respuesta)
    set_proveedor_ia_override(fake_prov)

    clave = str(uuid4())
    archivos = {
        "imagen": ("diagrama.png", io.BytesIO(PNG_VALIDO_BYTES), "image/png"),
    }
    datos = {
        "clave_idempotencia": clave,
    }

    res = client.post(
        f"/api/diagramas/{diagrama.id}/interacciones-ia/imagen",
        files=archivos,
        data=datos,
    )

    assert res.status_code == 201, res.text
    data = res.json()
    assert data["tipoInteraccion"] == "imagen"
    assert data["estado"] == "completado"
    assert "Producto" in data["respuestaIa"]
    assert len(fake_prov.llamadas_imagen) == 1


def test_interaccion_ia_api_imagen_vacia_rechaza(client: TestClient, session: Session):
    usuario = BetterAuthUser(
        id="usuario-propietario-1",
        name="PropVacio",
        email="propietario@drawi.com",
        email_verified=True,
    )
    session.add(usuario)
    session.commit()

    proyecto = ProyectoModel(
        propietario_id=usuario.id,
        nombre="Proy Vacio",
        color="azul",
        icono="caja",
        slug="proy-vacio",
    )
    session.add(proyecto)
    session.commit()

    diagrama = DiagramaModel(id_proyecto=proyecto.id, nombre="Página 1", numero=1)
    session.add(diagrama)
    session.commit()

    clave = str(uuid4())
    archivos = {
        "imagen": ("vacio.png", io.BytesIO(b""), "image/png"),
    }
    datos = {
        "clave_idempotencia": clave,
    }

    res = client.post(
        f"/api/diagramas/{diagrama.id}/interacciones-ia/imagen",
        files=archivos,
        data=datos,
    )

    assert res.status_code in (400, 422)


def test_interaccion_ia_api_imagen_permiso_lector_rechazado(
    client: TestClient, session: Session
):
    propietario = BetterAuthUser(
        id="usuario-otro-propietario",
        name="PropOtro",
        email="otroprop@drawi.com",
        email_verified=True,
    )
    lector = BetterAuthUser(
        id="usuario-propietario-1",
        name="LectorPerm",
        email="propietario@drawi.com",
        email_verified=True,
    )
    session.add(propietario)
    session.add(lector)
    session.commit()

    proyecto = ProyectoModel(
        propietario_id=propietario.id,
        nombre="Proy Perm",
        color="azul",
        icono="caja",
        slug="proy-perm",
    )
    session.add(proyecto)
    session.commit()

    colaborador = ColaboradorProyectoModel(
        id_proyecto=proyecto.id,
        id_usuario=lector.id,
        rol=RolColaborador.VER.value,
    )
    session.add(colaborador)
    session.commit()

    diagrama = DiagramaModel(id_proyecto=proyecto.id, nombre="Página 1", numero=1)
    session.add(diagrama)
    session.commit()

    clave = str(uuid4())
    archivos = {
        "imagen": ("diagrama.png", io.BytesIO(PNG_VALIDO_BYTES), "image/png"),
    }
    datos = {
        "clave_idempotencia": clave,
    }

    res = client.post(
        f"/api/diagramas/{diagrama.id}/interacciones-ia/imagen",
        files=archivos,
        data=datos,
    )

    assert res.status_code in (403, 404)


def test_interaccion_ia_api_imagen_error_gemini_503_retorna_http_503(
    client: TestClient, session: Session
):
    usuario = BetterAuthUser(
        id="usuario-propietario-1",
        name="Prop503",
        email="propietario@drawi.com",
        email_verified=True,
    )
    session.add(usuario)
    session.commit()

    proyecto = ProyectoModel(
        propietario_id=usuario.id,
        nombre="Proy 503",
        color="azul",
        icono="caja",
        slug="proy-503",
    )
    session.add(proyecto)
    session.commit()

    diagrama = DiagramaModel(id_proyecto=proyecto.id, nombre="Página 1", numero=1)
    session.add(diagrama)
    session.commit()

    fake_prov = FakeProveedorIaImagen()
    fake_prov.debe_fallar_imagen = True  # Lanza ProveedorIaRecuperableException
    set_proveedor_ia_override(fake_prov)

    clave = str(uuid4())
    archivos = {
        "imagen": ("diagrama.png", io.BytesIO(PNG_VALIDO_BYTES), "image/png"),
    }
    datos = {
        "clave_idempotencia": clave,
    }

    res = client.post(
        f"/api/diagramas/{diagrama.id}/interacciones-ia/imagen",
        files=archivos,
        data=datos,
    )

    # El error técnico recuperable de Gemini DEBE retornar HTTP 503, nunca HTTP 400
    assert res.status_code == 503, res.text
    data = res.json()
    assert data["error"]["code"] == "ERROR_RECUPERABLE_PROVEEDOR_IA"

