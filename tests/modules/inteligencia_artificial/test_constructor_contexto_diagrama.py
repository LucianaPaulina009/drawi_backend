from uuid import uuid4
from sqlmodel import Session

from app.modules.diagramas.application.queries.diagrama.obtener_diagrama import (
    ObtenerDiagramaCompletoQueryHandler,
)
from app.modules.diagramas.infrastructure.persistence.models.atributo_model import (
    AtributoModel,
)
from app.modules.diagramas.infrastructure.persistence.models.clase_model import (
    ClaseModel,
)
from app.modules.diagramas.infrastructure.persistence.models.diagrama_model import (
    DiagramaModel,
)
from app.modules.diagramas.infrastructure.persistence.repositories.sqlmodel_atributo_repository import (
    SQLModelAtributoRepository,
)
from app.modules.diagramas.infrastructure.persistence.repositories.sqlmodel_clase_repository import (
    SQLModelClaseRepository,
)
from app.modules.diagramas.infrastructure.persistence.repositories.sqlmodel_diagrama_repository import (
    SQLModelDiagramaRepository,
)
from app.modules.diagramas.infrastructure.persistence.repositories.sqlmodel_estructura_relacion_nm_repository import (
    SQLModelEstructuraRelacionNmRepository,
)
from app.modules.diagramas.infrastructure.persistence.repositories.sqlmodel_referencia_fk_repository import (
    SQLModelReferenciaFKRepository,
)
from app.modules.diagramas.infrastructure.persistence.repositories.sqlmodel_relacion_repository import (
    SQLModelRelacionRepository,
)
from app.modules.gestion_colaboradores.infrastructure.persistence.repositories.sqlmodel_colaborador_proyecto_repository import (
    SQLModelColaboradorProyectoRepository,
)
from app.modules.gestion_proyectos.infrastructure.persistence.models.proyecto_model import (
    ProyectoModel,
)
from app.modules.gestion_proyectos.infrastructure.persistence.repositories.sqlmodel_proyecto_repository import (
    SQLModelProyectoRepository,
)
from app.modules.inteligencia_artificial.application.services.constructor_contexto_diagrama import (
    ConstructorContextoDiagrama,
)
from app.modules.inteligencia_artificial.domain.entities.interaccion_ia import (
    InteraccionIa,
)
from app.modules.inteligencia_artificial.infrastructure.persistence.repositories.sqlmodel_interaccion_ia_repository import (
    SQLModelInteraccionIaRepository,
)
from app.shared.infrastructure.db.better_auth import BetterAuthUser


def _configurar_fixture(session: Session):
    usuario = BetterAuthUser(id=f"user-ctx-{uuid4().hex[:6]}", name="Ctx", email=f"ctx_{uuid4().hex[:6]}@drawi.com", email_verified=True)
    session.add(usuario)
    session.commit()

    proyecto = ProyectoModel(propietario_id=usuario.id, nombre="Proy Ctx", color="azul", icono="caja", slug=f"proy-ctx-{uuid4().hex[:6]}")
    session.add(proyecto)
    session.commit()

    diagrama = DiagramaModel(id_proyecto=proyecto.id, nombre="Página Central", numero=1)
    session.add(diagrama)
    session.commit()

    c1 = ClaseModel(id_diagrama=diagrama.id, nombre="Cliente", posicion_x=100.0, posicion_y=150.0, ancho=280.0)
    c2 = ClaseModel(id_diagrama=diagrama.id, nombre="Factura", posicion_x=400.0, posicion_y=150.0, ancho=280.0)
    c3 = ClaseModel(id_diagrama=diagrama.id, nombre="Producto", posicion_x=700.0, posicion_y=150.0, ancho=280.0)
    session.add(c1)
    session.add(c2)
    session.add(c3)
    session.commit()

    a1 = AtributoModel(id_clase=c1.id, nombre="nombre", tipo_dato="varchar", orden_de_posicion=1, es_llave_primaria=False, permite_nulo=True, es_unico=False)
    session.add(a1)
    session.commit()

    p_repo = SQLModelProyectoRepository(session)
    d_repo = SQLModelDiagramaRepository(session)
    i_repo = SQLModelInteraccionIaRepository(session)
    c_repo = SQLModelClaseRepository(session)
    a_repo = SQLModelAtributoRepository(session)
    r_repo = SQLModelRelacionRepository(session)
    rfk_repo = SQLModelReferenciaFKRepository(session)
    nm_repo = SQLModelEstructuraRelacionNmRepository(session)
    col_repo = SQLModelColaboradorProyectoRepository(session)

    q_diag = ObtenerDiagramaCompletoQueryHandler(p_repo, d_repo, c_repo, a_repo, col_repo, r_repo, rfk_repo, nm_repo)
    constructor = ConstructorContextoDiagrama(q_diag, i_repo)

    return usuario, proyecto, diagrama, constructor, i_repo, c_repo


# Caso 9: Contexto Nivel 1 para creación de clase independiente o preguntas generales
def test_caso_9_contexto_nivel_1_creacion_independiente_o_saludo(session: Session):
    usuario, proyecto, diagrama, constructor, _, _ = _configurar_fixture(session)

    prompt, nivel = constructor.construir_contexto_con_metadatos(
        proyecto_id=proyecto.id,
        diagrama_id=diagrama.id,
        usuario_id=usuario.id,
        mensaje_usuario="Crea una clase Proveedor con atributo ruc",
    )

    assert nivel == 1
    assert "1_resumen_compacto" in prompt
    assert "Cliente" in prompt
    assert "Factura" in prompt
    assert "Producto" in prompt
    assert '"nivel_contexto": "1_resumen_compacto"' in prompt
    assert '"clases_existentes"' in prompt
    assert '"relaciones_existentes"' in prompt


# Caso 10: Contexto Nivel 2 para modificación de clases específicas involucradas
def test_caso_10_contexto_nivel_2_modificacion_clase_especifica(session: Session):
    usuario, proyecto, diagrama, constructor, _, _ = _configurar_fixture(session)

    prompt, nivel = constructor.construir_contexto_con_metadatos(
        proyecto_id=proyecto.id,
        diagrama_id=diagrama.id,
        usuario_id=usuario.id,
        mensaje_usuario="Agrega el atributo telefono a Cliente",
    )

    assert nivel == 2
    assert "2_detalle_relevante" in prompt
    assert "Cliente" in prompt
    assert "Factura" in prompt
    # Cliente debe estar en clases_relevantes con sus atributos
    assert '"nombre": "nombre"' in prompt


# Caso 10b: Contexto Nivel 2 mediante resolución de referencias anafóricas en historial
def test_caso_10b_contexto_nivel_2_resolucion_referencia_historial(session: Session):
    usuario, proyecto, diagrama, constructor, i_repo, _ = _configurar_fixture(session)

    # Interacción previa donde se creó o habló únicamente de "Cliente"
    interaccion_previa = InteraccionIa.crear(
        id_usuario=usuario.id,
        id_diagrama=diagrama.id,
        clave_idempotencia=uuid4(),
        entrada_usuario="Crea la tabla Cliente",
    )
    interaccion_previa.completar(
        respuesta_ia="He creado la tabla Cliente exitosamente.",
        modelo_utilizado="gemini-3.6-flash",
    )
    i_repo.guardar(interaccion_previa)
    session.commit()

    # Usuario responde elípticamente: "agrégale teléfono"
    prompt, nivel = constructor.construir_contexto_con_metadatos(
        proyecto_id=proyecto.id,
        diagrama_id=diagrama.id,
        usuario_id=usuario.id,
        mensaje_usuario="agrégale teléfono",
    )

    assert nivel == 2
    assert "2_detalle_relevante" in prompt
    assert "Cliente" in prompt


# Caso 11: Contexto Nivel 3 para análisis global del diagrama
def test_caso_11_contexto_nivel_3_analisis_global(session: Session):
    usuario, proyecto, diagrama, constructor, _, _ = _configurar_fixture(session)

    prompt, nivel = constructor.construir_contexto_con_metadatos(
        proyecto_id=proyecto.id,
        diagrama_id=diagrama.id,
        usuario_id=usuario.id,
        mensaje_usuario="Analiza el diagrama y busca redundancias y mejoras",
    )

    assert nivel == 3
    assert "3_diagrama_completo" in prompt


# Caso 12: Ventana de historial conversacional limitada exactamente a IA_HISTORIAL_LIMITE (5)
def test_caso_12_historial_conversacional_acotado(session: Session):
    usuario, proyecto, diagrama, constructor, i_repo, _ = _configurar_fixture(session)

    # Insertar 7 interacciones completadas
    for idx in range(1, 8):
        interaccion = InteraccionIa.crear(
            id_usuario=usuario.id,
            id_diagrama=diagrama.id,
            clave_idempotencia=uuid4(),
            entrada_usuario=f"Mensaje {idx}",
        )
        interaccion.completar(respuesta_ia=f"Respuesta {idx}", modelo_utilizado="gemini-3.6-flash")
        i_repo.guardar(interaccion)
    session.commit()

    prompt, _ = constructor.construir_contexto_con_metadatos(
        proyecto_id=proyecto.id,
        diagrama_id=diagrama.id,
        usuario_id=usuario.id,
        mensaje_usuario="Hola",
        limite_historial=5,
    )

    # Solo las 5 más recientes deben estar presentes
    assert "Mensaje 7" in prompt
    assert "Mensaje 6" in prompt
    assert "Mensaje 5" in prompt
    assert "Mensaje 4" in prompt
    assert "Mensaje 3" in prompt
    assert "Mensaje 1" not in prompt  # Las más antiguas quedan fuera de la ventana


# Caso 13: Diagrama fresco obtenido desde BD en cada ejecución (cero caché obsoleto)
def test_caso_13_diagrama_fresco_desde_base_de_datos(session: Session):
    usuario, proyecto, diagrama, constructor, _, c_repo = _configurar_fixture(session)

    # Primera llamada
    prompt_1, _ = constructor.construir_contexto_con_metadatos(
        proyecto_id=proyecto.id,
        diagrama_id=diagrama.id,
        usuario_id=usuario.id,
        mensaje_usuario="Hola",
    )
    assert "Proveedor" not in prompt_1

    # Crear una nueva clase en BD directamente
    nueva_clase = ClaseModel(id_diagrama=diagrama.id, nombre="Proveedor", posicion_x=200.0, posicion_y=200.0, ancho=280.0)
    session.add(nueva_clase)
    session.commit()

    # Segunda llamada debe reflejar la clase recién agregada inmediatamente
    prompt_2, _ = constructor.construir_contexto_con_metadatos(
        proyecto_id=proyecto.id,
        diagrama_id=diagrama.id,
        usuario_id=usuario.id,
        mensaje_usuario="Hola",
    )
    assert "Proveedor" in prompt_2
