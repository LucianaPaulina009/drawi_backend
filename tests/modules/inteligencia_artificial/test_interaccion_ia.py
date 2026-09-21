from uuid import UUID, uuid4
import pytest
from sqlmodel import Session

from app.modules.diagramas.infrastructure.persistence.models.clase_model import ClaseModel
from app.modules.diagramas.infrastructure.persistence.models.diagrama_model import DiagramaModel
from app.modules.gestion_proyectos.infrastructure.persistence.models.proyecto_model import ProyectoModel
from app.modules.inteligencia_artificial.domain.entities.interaccion_ia import InteraccionIa
from app.modules.inteligencia_artificial.domain.exceptions import (
    EntradaUsuarioInvalidaException,
    EstadoInteraccionIaInvalidoException,
    TipoInteraccionIaInvalidoException,
)
from app.modules.inteligencia_artificial.domain.value_objects.estado_interaccion_ia import EstadoInteraccionIa
from app.modules.inteligencia_artificial.domain.value_objects.tipo_interaccion_ia import TipoInteraccionIa
from app.modules.inteligencia_artificial.infrastructure.persistence.repositories.sqlmodel_interaccion_ia_repository import (
    SQLModelInteraccionIaRepository,
)
from app.shared.infrastructure.db.better_auth import BetterAuthUser


def test_tipo_interaccion_ia_enum_y_validacion():
    assert TipoInteraccionIa.validar("texto") == TipoInteraccionIa.TEXTO
    assert TipoInteraccionIa.validar("AUDIO") == TipoInteraccionIa.AUDIO
    assert TipoInteraccionIa.validar(TipoInteraccionIa.IMAGEN) == TipoInteraccionIa.IMAGEN
    assert TipoInteraccionIa.validar("generacion_backend") == TipoInteraccionIa.GENERACION_BACKEND
    with pytest.raises(TipoInteraccionIaInvalidoException):
        TipoInteraccionIa.validar("desconocido")


def test_estado_interaccion_ia_enum_y_validacion():
    assert EstadoInteraccionIa.validar("pendiente") == EstadoInteraccionIa.PENDIENTE
    assert EstadoInteraccionIa.validar("PROCESANDO") == EstadoInteraccionIa.PROCESANDO
    assert EstadoInteraccionIa.validar("completado") == EstadoInteraccionIa.COMPLETADO
    assert EstadoInteraccionIa.validar(EstadoInteraccionIa.ERROR) == EstadoInteraccionIa.ERROR
    with pytest.raises(EstadoInteraccionIaInvalidoException):
        EstadoInteraccionIa.validar("cancelado")


def test_creacion_interaccion_ia_valida_y_transiciones():
    id_diag = uuid4()
    clave = uuid4()
    interaccion = InteraccionIa.crear(
        id_usuario="user-1",
        id_diagrama=id_diag,
        clave_idempotencia=clave,
        entrada_usuario="  Crea la clase Usuario  ",
    )

    assert interaccion.id_usuario == "user-1"
    assert interaccion.id_diagrama == id_diag
    assert interaccion.clave_idempotencia == clave
    assert interaccion.entrada_usuario == "Crea la clase Usuario"
    assert interaccion.tipo_interaccion == TipoInteraccionIa.TEXTO
    assert interaccion.estado == EstadoInteraccionIa.PENDIENTE

    interaccion.marcar_procesando()
    assert interaccion.estado == EstadoInteraccionIa.PROCESANDO

    interaccion.completar(
        respuesta_ia="Clase Usuario creada exitosamente.",
        modelo_utilizado="gemini-3.7-flash",
        detalle_ejecucion={"acciones": 1},
    )
    assert interaccion.estado == EstadoInteraccionIa.COMPLETADO
    assert interaccion.respuesta_ia == "Clase Usuario creada exitosamente."
    assert interaccion.modelo_utilizado == "gemini-3.7-flash"
    assert interaccion.detalle_ejecucion == {"acciones": 1}


def test_creacion_interaccion_ia_texto_vacio_falla():
    with pytest.raises(EntradaUsuarioInvalidaException):
        InteraccionIa.crear(
            id_usuario="user-1",
            id_diagrama=uuid4(),
            clave_idempotencia=uuid4(),
            entrada_usuario="   ",
        )


def _crear_diagrama_base(session: Session) -> DiagramaModel:
    usuario = BetterAuthUser(
        id="user-ia-1",
        name="User IA",
        email="ia@drawi.com",
        email_verified=True,
    )
    session.add(usuario)
    session.commit()

    proyecto = ProyectoModel(
        propietario_id=usuario.id,
        nombre="Proyecto IA",
        color="azul",
        icono="caja",
        slug="proyecto-ia",
    )
    session.add(proyecto)
    session.commit()

    diagrama = DiagramaModel(
        id_proyecto=proyecto.id,
        nombre="Página 1",
        numero=1,
    )
    session.add(diagrama)
    session.commit()
    return diagrama


def test_repositorio_interaccion_ia_crud_e_idempotencia(session: Session):
    diag = _crear_diagrama_base(session)
    repo = SQLModelInteraccionIaRepository(session)

    clave_1 = uuid4()
    interaccion = InteraccionIa.crear(
        id_usuario="user-ia-1",
        id_diagrama=diag.id,
        clave_idempotencia=clave_1,
        entrada_usuario="Hola DRAWI",
    )
    repo.guardar(interaccion)
    session.commit()

    # Recuperar por ID
    recuperada = repo.obtener_por_id(interaccion.id)
    assert recuperada is not None
    assert recuperada.id == interaccion.id
    assert recuperada.entrada_usuario == "Hola DRAWI"
    assert recuperada.estado == EstadoInteraccionIa.PENDIENTE

    # Recuperar por idempotencia
    idempotente = repo.obtener_por_idempotencia("user-ia-1", diag.id, clave_1)
    assert idempotente is not None
    assert idempotente.id == interaccion.id

    # Actualizar estado a completado
    interaccion.completar(
        respuesta_ia="¡Hola! ¿En qué puedo ayudarte?",
        modelo_utilizado="gemini-3.7-flash",
    )
    repo.guardar(interaccion)
    session.commit()

    actualizada = repo.obtener_por_id(interaccion.id)
    assert actualizada is not None
    assert actualizada.estado == EstadoInteraccionIa.COMPLETADO
    assert actualizada.respuesta_ia == "¡Hola! ¿En qué puedo ayudarte?"

    # Listar por diagrama
    lista = repo.listar_por_diagrama(diag.id)
    assert len(lista) == 1
    assert lista[0].id == interaccion.id
