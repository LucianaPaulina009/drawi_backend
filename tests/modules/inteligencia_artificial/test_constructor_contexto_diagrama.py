from uuid import uuid4
from sqlmodel import Session

from app.modules.diagramas.application.queries.diagrama.obtener_diagrama import (
    ObtenerDiagramaCompletoQueryHandler,
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


def test_constructor_contexto_diagrama_incluye_clases_e_historial(session: Session):
    usuario = BetterAuthUser(id="user-ctx-1", name="Ctx", email="ctx@drawi.com", email_verified=True)
    session.add(usuario)
    session.commit()

    proyecto = ProyectoModel(propietario_id=usuario.id, nombre="Proy Ctx", color="azul", icono="caja", slug="proy-ctx")
    session.add(proyecto)
    session.commit()

    diagrama = DiagramaModel(id_proyecto=proyecto.id, nombre="Página Central", numero=1)
    session.add(diagrama)
    session.commit()

    clase = ClaseModel(id_diagrama=diagrama.id, nombre="Factura", posicion_x=100.0, posicion_y=150.0, ancho=280.0)
    session.add(clase)
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

    # Interacción previa completada
    i = InteraccionIa.crear(id_usuario=usuario.id, id_diagrama=diagrama.id, clave_idempotencia=uuid4(), entrada_usuario="Crea Factura")
    i.completar(respuesta_ia="Factura creada exitosamente.", modelo_utilizado="gemini-3.7-flash")
    i_repo.guardar(i)
    session.commit()

    q_diag = ObtenerDiagramaCompletoQueryHandler(p_repo, d_repo, c_repo, a_repo, col_repo, r_repo, rfk_repo, nm_repo)
    constructor = ConstructorContextoDiagrama(q_diag, i_repo)

    prompt = constructor.construir_contexto(
        proyecto_id=proyecto.id,
        diagrama_id=diagrama.id,
        usuario_id=usuario.id,
    )

    assert "Factura" in prompt
    assert "Crea Factura" in prompt
    assert "Factura creada exitosamente." in prompt
    assert "ESTRUCTURA ACTUAL DEL DIAGRAMA:" in prompt
