from uuid import uuid4
import pytest
from sqlmodel import Session

from app.core.dependencies import get_event_bus
from app.shared.infrastructure.unit_of_work import SqlModelUnitOfWork
from app.modules.diagramas.application.use_cases.atributo.atributo_use_cases import AtributoUseCase
from app.modules.diagramas.application.use_cases.clase.crear_clase import CrearClaseUseCase
from app.modules.diagramas.application.use_cases.relacion.crear_relacion import CrearRelacionUseCase
from app.modules.diagramas.infrastructure.persistence.models.diagrama_model import DiagramaModel
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
from app.modules.gestion_proyectos.infrastructure.persistence.models.proyecto_model import ProyectoModel
from app.modules.gestion_proyectos.infrastructure.persistence.repositories.sqlmodel_proyecto_repository import (
    SQLModelProyectoRepository,
)
from app.modules.inteligencia_artificial.application.services.ejecutor_plan_ia import EjecutorPlanIa
from app.modules.inteligencia_artificial.application.services.validador_respuesta_ia import (
    AccionCrearAtributoSchema,
    AccionCrearClaseSchema,
    AccionCrearRelacionSchema,
)
from app.shared.infrastructure.db.better_auth import BetterAuthUser


def _setup_repos(session: Session):
    p_repo = SQLModelProyectoRepository(session)
    d_repo = SQLModelDiagramaRepository(session)
    c_repo = SQLModelClaseRepository(session)
    a_repo = SQLModelAtributoRepository(session)
    r_repo = SQLModelRelacionRepository(session)
    rfk_repo = SQLModelReferenciaFKRepository(session)
    nm_repo = SQLModelEstructuraRelacionNmRepository(session)
    col_repo = SQLModelColaboradorProyectoRepository(session)
    uow = SqlModelUnitOfWork(session, get_event_bus())

    cc_uc = CrearClaseUseCase(
        proyecto_repository=p_repo,
        diagrama_repository=d_repo,
        clase_repository=c_repo,
        atributo_repository=a_repo,
        uow=uow,
        colaborador_repository=col_repo,
    )
    at_uc = AtributoUseCase(
        p=p_repo,
        d=d_repo,
        c=c_repo,
        a=a_repo,
        u=uow,
        col=col_repo,
        rfk=rfk_repo,
        relacion_repository=r_repo,
        estructura_repository=nm_repo,
    )
    cr_uc = CrearRelacionUseCase(
        proyecto_repository=p_repo,
        diagrama_repository=d_repo,
        clase_repository=c_repo,
        relacion_repository=r_repo,
        uow=uow,
        colaborador_repository=col_repo,
        atributo_repository=a_repo,
        referencia_fk_repository=rfk_repo,
    )

    ejecutor = EjecutorPlanIa(
        crear_clase_use_case=cc_uc,
        atributo_use_case=at_uc,
        crear_relacion_use_case=cr_uc,
        clase_repository=c_repo,
        atributo_repository=a_repo,
        relacion_repository=r_repo,
        referencia_fk_repository=rfk_repo,
    )
    return ejecutor, c_repo, a_repo, r_repo


def test_ejecutor_plan_ia_crea_clases_atributos_y_relaciones(session: Session):
    usuario = BetterAuthUser(id="user-ejec-1", name="Ejec", email="ejec@drawi.com", email_verified=True)
    session.add(usuario)
    session.commit()

    proyecto = ProyectoModel(propietario_id=usuario.id, nombre="Proy", color="azul", icono="caja", slug="proy-ejec")
    session.add(proyecto)
    session.commit()

    diagrama = DiagramaModel(id_proyecto=proyecto.id, nombre="Pag 1", numero=1)
    session.add(diagrama)
    session.commit()

    ejecutor, c_repo, a_repo, r_repo = _setup_repos(session)

    acciones = [
        AccionCrearClaseSchema(referencia="cliente", nombre="Cliente"),
        AccionCrearClaseSchema(referencia="pedido", nombre="Pedido"),
        AccionCrearAtributoSchema(clase_referencia="cliente", nombre="nombre", tipo_dato="varchar", longitud=100),
        AccionCrearRelacionSchema(clase_origen_referencia="cliente", clase_destino_referencia="pedido", tipo_relacion="asociacion", nombre="Realiza"),
    ]

    resultados = ejecutor.ejecutar_plan(
        usuario_id=usuario.id,
        diagrama_id=diagrama.id,
        acciones=acciones,
    )

    assert len(resultados) == 4, f"Resultados: {resultados}"
    for r in resultados:
        assert r["estado"] == "completado", f"Paso {r.get('paso')} falló: {r.get('error')}"

    # Verificar que las entidades existen en la base de datos
    clases = c_repo.listar_por_diagrama(diagrama.id)
    assert len(clases) == 2
    nombres_clases = {c.nombre for c in clases}
    assert "Cliente" in nombres_clases
    assert "Pedido" in nombres_clases

    relaciones = r_repo.listar_por_diagrama(diagrama.id)
    assert len(relaciones) == 1
    assert relaciones[0].nombre == "Realiza"
