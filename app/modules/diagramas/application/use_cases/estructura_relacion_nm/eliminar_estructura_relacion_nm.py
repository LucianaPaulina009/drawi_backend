from dataclasses import dataclass
from uuid import UUID

from app.modules.diagramas.application.validaciones import obtener_diagrama_autorizado
from app.modules.diagramas.domain.exceptions import EstructuraRelacionNmNoEncontradaException
from app.modules.diagramas.domain.repositories.atributo_repository import AtributoRepository
from app.modules.diagramas.domain.repositories.clase_repository import ClaseRepository
from app.modules.diagramas.domain.repositories.diagrama_repository import DiagramaRepository
from app.modules.diagramas.domain.repositories.estructura_relacion_nm_repository import EstructuraRelacionNmRepository
from app.modules.diagramas.domain.repositories.referencia_fk_repository import ReferenciaFKRepository
from app.modules.diagramas.domain.repositories.relacion_repository import RelacionRepository
from app.modules.gestion_colaboradores.domain.repositories.colaborador_proyecto_repository import ColaboradorProyectoRepository
from app.modules.gestion_proyectos.domain.repositories.proyecto_repository import ProyectoRepository
from app.shared.application.ports import UnitOfWork


from app.modules.diagramas.application.services.cascadas_diagrama import (
    CascadasDiagramaService,
    CierreCascadaResultado,
)


@dataclass(slots=True)
class EliminarEstructuraRelacionNmCommand:
    propietario_id: str
    diagrama_id: UUID
    estructura_id: UUID


class EliminarEstructuraRelacionNmUseCase:
    def __init__(self, proyecto_repository: ProyectoRepository, diagrama_repository: DiagramaRepository,
                 estructura_repository: EstructuraRelacionNmRepository, clase_repository: ClaseRepository,
                 atributo_repository: AtributoRepository, relacion_repository: RelacionRepository,
                 referencia_fk_repository: ReferenciaFKRepository, uow: UnitOfWork,
                 colaborador_repository: ColaboradorProyectoRepository | None = None) -> None:
        self.proyecto_repository = proyecto_repository
        self.diagrama_repository = diagrama_repository
        self.estructura_repository = estructura_repository
        self.clase_repository = clase_repository
        self.atributo_repository = atributo_repository
        self.relacion_repository = relacion_repository
        self.referencia_fk_repository = referencia_fk_repository
        self.uow = uow
        self.colaborador_repository = colaborador_repository

    def execute(
        self, command: EliminarEstructuraRelacionNmCommand, confirmar: bool = True
    ) -> CierreCascadaResultado:
        obtener_diagrama_autorizado(propietario_id=command.propietario_id, diagrama_id=command.diagrama_id,
            proyecto_repository=self.proyecto_repository, diagrama_repository=self.diagrama_repository,
            colaborador_repository=self.colaborador_repository, exigir_edicion=True)
        estructura = self.estructura_repository.obtener_por_id(command.estructura_id)
        if estructura is None or estructura.id_diagrama != command.diagrama_id:
            raise EstructuraRelacionNmNoEncontradaException()

        servicio = CascadasDiagramaService(
            clase_repository=self.clase_repository,
            atributo_repository=self.atributo_repository,
            relacion_repository=self.relacion_repository,
            referencia_fk_repository=self.referencia_fk_repository,
            estructura_nm_repository=self.estructura_repository,
        )
        resultado = servicio.cerrar_por_estructura_nm(command.estructura_id, command.diagrama_id)

        if confirmar:
            self.uow.commit()
        return resultado
