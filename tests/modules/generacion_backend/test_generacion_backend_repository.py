from datetime import datetime, timezone
from uuid import uuid4
import pytest
from sqlmodel import Session

from app.modules.diagramas.infrastructure.persistence.models.diagrama_model import DiagramaModel
from app.modules.gestion_proyectos.infrastructure.persistence.models.proyecto_model import ProyectoModel
from app.modules.generacion_backend.domain.entities.generacion_backend import GeneracionBackend
from app.modules.generacion_backend.domain.value_objects.estado_generacion_backend import (
    EstadoGeneracionBackend,
)
from app.modules.generacion_backend.infrastructure.persistence.models.generacion_backend_model import (
    GeneracionBackendModel,
)
from app.modules.generacion_backend.infrastructure.persistence.repositories.sqlmodel_generacion_backend_repository import (
    SQLModelGeneracionBackendRepository,
)
from app.shared.infrastructure.db.better_auth import BetterAuthUser


def test_estado_generacion_backend_enum_y_validacion():
    assert EstadoGeneracionBackend.validar("validando") == EstadoGeneracionBackend.VALIDANDO
    assert EstadoGeneracionBackend.validar("generando") == EstadoGeneracionBackend.GENERANDO
    assert EstadoGeneracionBackend.validar("empaquetando") == EstadoGeneracionBackend.EMPAQUETANDO
    assert EstadoGeneracionBackend.validar("completado") == EstadoGeneracionBackend.COMPLETADO
    assert EstadoGeneracionBackend.validar("error") == EstadoGeneracionBackend.ERROR
    with pytest.raises(ValueError):
        EstadoGeneracionBackend.validar("desconocido")


def test_entidad_generacion_backend_flujo_estados():
    id_diag = uuid4()
    gen = GeneracionBackend.iniciar(
        id_diagrama=id_diag,
        id_usuario="user-test-1",
        version_plantilla="1.0.0",
    )
    assert gen.estado == EstadoGeneracionBackend.VALIDANDO
    assert gen.detalle_error is None
    assert gen.id_diagrama == id_diag
    assert gen.id_usuario == "user-test-1"
    assert gen.version_plantilla == "1.0.0"
    assert isinstance(gen.fecha_generacion, datetime)

    # Transición a generando
    gen.iniciar_generacion()
    assert gen.estado == EstadoGeneracionBackend.GENERANDO

    # Transición a empaquetando
    gen.iniciar_empaquetado()
    assert gen.estado == EstadoGeneracionBackend.EMPAQUETANDO

    # Transición a completado
    gen.completar()
    assert gen.estado == EstadoGeneracionBackend.COMPLETADO
    assert gen.detalle_error is None


def test_entidad_generacion_backend_flujo_error():
    id_diag = uuid4()
    gen = GeneracionBackend.iniciar(
        id_diagrama=id_diag,
        id_usuario="user-test-1",
    )
    assert gen.estado == EstadoGeneracionBackend.VALIDANDO

    # Marcar error durante validación
    gen.marcar_error("Diagrama sin clases válidas.")
    assert gen.estado == EstadoGeneracionBackend.ERROR
    assert gen.detalle_error == "Diagrama sin clases válidas."


def test_repositorio_generacion_backend_guardar_y_obtener(session: Session):
    usuario_id = "user_repo_test"
    usuario = BetterAuthUser(
        id=usuario_id,
        name="Test User",
        email="test_gen@example.com",
        email_verified=True,
    )
    proyecto = ProyectoModel(
        nombre="Proyecto Gen",
        slug="proyecto-gen",
        propietario_id=usuario_id,
    )
    session.add(usuario)
    session.add(proyecto)
    session.flush()

    diagrama = DiagramaModel(
        nombre="Diagrama Principal",
        id_proyecto=proyecto.id,
        numero=1,
    )
    session.add(diagrama)
    session.commit()

    repo = SQLModelGeneracionBackendRepository(session)
    gen = GeneracionBackend.iniciar(
        id_diagrama=diagrama.id,
        id_usuario=usuario_id,
        version_plantilla="1.0.0",
    )

    guardado = repo.guardar(gen)
    assert guardado.id == gen.id
    assert guardado.estado == EstadoGeneracionBackend.VALIDANDO

    recuperado = repo.obtener_por_id(gen.id)
    assert recuperado is not None
    assert recuperado.id == gen.id
    assert recuperado.id_diagrama == diagrama.id
    assert recuperado.id_usuario == usuario_id
    assert recuperado.estado == EstadoGeneracionBackend.VALIDANDO

    # Actualizar estado a error
    recuperado.marcar_error("Error de validación")
    repo.guardar(recuperado)

    actualizado = repo.obtener_por_id(gen.id)
    assert actualizado is not None
    assert actualizado.estado == EstadoGeneracionBackend.ERROR
    assert actualizado.detalle_error == "Error de validación"

    # Listar por diagrama
    lista = repo.listar_por_diagrama(diagrama.id)
    assert len(lista) == 1
    assert lista[0].id == gen.id
