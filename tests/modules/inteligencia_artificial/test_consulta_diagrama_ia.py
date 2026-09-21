from uuid import uuid4
from sqlmodel import Session

from app.core.dependencies import get_event_bus
from app.shared.infrastructure.unit_of_work import SqlModelUnitOfWork
from app.modules.diagramas.infrastructure.persistence.models.clase_model import ClaseModel
from app.modules.diagramas.infrastructure.persistence.models.diagrama_model import DiagramaModel
from app.modules.gestion_proyectos.infrastructure.persistence.models.proyecto_model import ProyectoModel
from app.modules.inteligencia_artificial.application.ports.providers.proveedor_ia import (
    ProveedorIa,
    ResultadoProveedorIa,
)
from app.modules.inteligencia_artificial.application.services.constructor_contexto_diagrama import (
    ConstructorContextoDiagrama,
)
from app.modules.inteligencia_artificial.application.services.ejecutor_plan_ia import (
    EjecutorPlanIa,
)
from app.modules.inteligencia_artificial.application.services.estrategia_modelos_gemini import (
    EstrategiaModelosGemini,
)
from app.modules.inteligencia_artificial.application.use_cases.procesar_mensaje_ia import (
    ProcesarMensajeIaCommand,
    ProcesarMensajeIaUseCase,
)
from app.modules.diagramas.infrastructure.persistence.repositories.sqlmodel_clase_repository import (
    SQLModelClaseRepository,
)
from app.modules.diagramas.infrastructure.persistence.repositories.sqlmodel_diagrama_repository import (
    SQLModelDiagramaRepository,
)
from app.modules.gestion_proyectos.infrastructure.persistence.repositories.sqlmodel_proyecto_repository import (
    SQLModelProyectoRepository,
)
from app.modules.inteligencia_artificial.infrastructure.persistence.repositories.sqlmodel_interaccion_ia_repository import (
    SQLModelInteraccionIaRepository,
)
from app.modules.diagramas.application.queries.diagrama.obtener_diagrama import (
    ObtenerDiagramaCompletoQueryHandler,
)
from app.modules.diagramas.infrastructure.persistence.repositories.sqlmodel_atributo_repository import (
    SQLModelAtributoRepository,
)
from app.modules.diagramas.infrastructure.persistence.repositories.sqlmodel_relacion_repository import (
    SQLModelRelacionRepository,
)
from app.modules.diagramas.infrastructure.persistence.repositories.sqlmodel_referencia_fk_repository import (
    SQLModelReferenciaFKRepository,
)
from app.modules.diagramas.infrastructure.persistence.repositories.sqlmodel_estructura_relacion_nm_repository import (
    SQLModelEstructuraRelacionNmRepository,
)
from app.modules.gestion_colaboradores.infrastructure.persistence.repositories.sqlmodel_colaborador_proyecto_repository import (
    SQLModelColaboradorProyectoRepository,
)
from app.modules.diagramas.application.use_cases.clase.crear_clase import (
    CrearClaseUseCase,
)
from app.modules.diagramas.application.use_cases.atributo.atributo_use_cases import (
    AtributoUseCase,
)
from app.modules.diagramas.application.use_cases.relacion.crear_relacion import (
    CrearRelacionUseCase,
)
from app.shared.infrastructure.db.better_auth import BetterAuthUser


class FakeConsultaProveedor(ProveedorIa):
    def generar_respuesta(
        self,
        *,
        modelo: str,
        prompt_sistema: str,
        mensaje_usuario: str,
        temperatura: float = 0.2,
    ) -> ResultadoProveedorIa:
        return ResultadoProveedorIa(
            texto_respuesta='{"respuesta_usuario": "El diagrama contiene las clases Cliente y Pedido.", "acciones": []}',
            modelo=modelo,
        )


def test_consulta_solo_lectura_produce_cero_mutaciones(session: Session):
    usuario = BetterAuthUser(id="usuario-lector", name="Lector", email="lector@drawi.com", email_verified=True)
    session.add(usuario)
    session.commit()

    proyecto = ProyectoModel(propietario_id=usuario.id, nombre="Proy Consulta", color="azul", icono="caja", slug="proy-consulta")
    session.add(proyecto)
    session.commit()

    diagrama = DiagramaModel(id_proyecto=proyecto.id, nombre="Pagina 1", numero=1)
    session.add(diagrama)
    session.commit()

    clase1 = ClaseModel(id_diagrama=diagrama.id, nombre="Cliente", posicion_x=100.0, posicion_y=100.0, ancho=280.0)
    session.add(clase1)
    session.commit()

    uow = SqlModelUnitOfWork(session, get_event_bus())
    proy_repo = SQLModelProyectoRepository(session)
    diag_repo = SQLModelDiagramaRepository(session)
    clase_repo = SQLModelClaseRepository(session)
    attr_repo = SQLModelAtributoRepository(session)
    rel_repo = SQLModelRelacionRepository(session)
    rfk_repo = SQLModelReferenciaFKRepository(session)
    est_repo = SQLModelEstructuraRelacionNmRepository(session)
    col_repo = SQLModelColaboradorProyectoRepository(session)
    inter_repo = SQLModelInteraccionIaRepository(session)

    query_diag = ObtenerDiagramaCompletoQueryHandler(
        proyecto_repository=proy_repo,
        diagrama_repository=diag_repo,
        clase_repository=clase_repo,
        atributo_repository=attr_repo,
        colaborador_repository=col_repo,
        relacion_repository=rel_repo,
        referencia_fk_repository=rfk_repo,
        estructura_nm_repository=est_repo,
    )
    contexto = ConstructorContextoDiagrama(query_diag, inter_repo)
    coordinador = EstrategiaModelosGemini(FakeConsultaProveedor())

    crear_clase_uc = CrearClaseUseCase(proy_repo, diag_repo, clase_repo, attr_repo, uow, colaborador_repository=col_repo)
    atributo_uc = AtributoUseCase(proy_repo, diag_repo, clase_repo, attr_repo, uow, col=col_repo, rfk=rfk_repo, relacion_repository=rel_repo, estructura_repository=est_repo)
    crear_rel_uc = CrearRelacionUseCase(proy_repo, diag_repo, clase_repo, rel_repo, uow, colaborador_repository=col_repo, atributo_repository=attr_repo, referencia_fk_repository=rfk_repo)

    ejecutor = EjecutorPlanIa(
        crear_clase_use_case=crear_clase_uc,
        atributo_use_case=atributo_uc,
        crear_relacion_use_case=crear_rel_uc,
        clase_repository=clase_repo,
        atributo_repository=attr_repo,
        relacion_repository=rel_repo,
        referencia_fk_repository=rfk_repo,
    )

    use_case = ProcesarMensajeIaUseCase(
        proyecto_repository=proy_repo,
        diagrama_repository=diag_repo,
        interaccion_repository=inter_repo,
        clase_repository=clase_repo,
        constructor_contexto=contexto,
        coordinador_gemini=coordinador,
        ejecutor_plan=ejecutor,
        uow=uow,
        colaborador_repository=col_repo,
    )

    clave = uuid4()
    interaccion = use_case.execute(
        ProcesarMensajeIaCommand(
            usuario_id=usuario.id,
            diagrama_id=diagrama.id,
            texto="¿Qué clases existen en este diagrama?",
            clave_idempotencia=clave,
        )
    )

    assert interaccion.estado.value == "completado" or str(interaccion.estado) == "completado"
    assert interaccion.respuesta_ia == "El diagrama contiene las clases Cliente y Pedido."
    assert interaccion.detalle_ejecucion is None or len(interaccion.detalle_ejecucion) == 0

    # Verificar que no se creó ninguna clase adicional
    clases_actuales = clase_repo.listar_por_diagrama(diagrama.id)
    assert len(clases_actuales) == 1
