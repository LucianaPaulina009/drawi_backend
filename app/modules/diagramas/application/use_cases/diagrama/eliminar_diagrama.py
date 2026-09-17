from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.modules.diagramas.domain.exceptions import (
    DiagramaNoEncontradoException,
    UltimoDiagramaException,
)
from app.modules.diagramas.domain.repositories.atributo_repository import AtributoRepository
from app.modules.diagramas.domain.repositories.clase_repository import ClaseRepository
from app.modules.diagramas.domain.repositories.diagrama_repository import (
    DiagramaRepository,
)
from app.modules.diagramas.domain.repositories.referencia_fk_repository import (
    ReferenciaFKRepository,
)
from app.modules.diagramas.domain.repositories.relacion_repository import (
    RelacionRepository,
)
from app.modules.gestion_proyectos.domain.exceptions import (
    ProyectoNoEncontradoException,
)
from app.modules.gestion_proyectos.domain.repositories.proyecto_repository import (
    ProyectoRepository,
)
from app.shared.application.ports import UnitOfWork


@dataclass(slots=True)
class EliminarDiagramaCommand:
    propietario_id: str
    proyecto_id: UUID
    diagrama_id: UUID


class EliminarDiagramaUseCase:
    def __init__(
        self,
        proyecto_repository: ProyectoRepository,
        diagrama_repository: DiagramaRepository,
        clase_repository: ClaseRepository,
        atributo_repository: AtributoRepository,
        uow: UnitOfWork,
        relacion_repository: RelacionRepository | None = None,
        referencia_fk_repository: ReferenciaFKRepository | None = None,
    ) -> None:
        self.proyecto_repository = proyecto_repository
        self.diagrama_repository = diagrama_repository
        self.clase_repository = clase_repository
        self.atributo_repository = atributo_repository
        self.uow = uow
        self.relacion_repository = relacion_repository
        self.referencia_fk_repository = referencia_fk_repository

    def execute(self, command: EliminarDiagramaCommand) -> None:
        proyecto = self.proyecto_repository.obtener_por_id(command.proyecto_id)
        if proyecto is None or proyecto.propietario_id != command.propietario_id:
            raise ProyectoNoEncontradoException()
        diagrama = self.diagrama_repository.obtener_por_id(command.diagrama_id)
        if diagrama is None or diagrama.id_proyecto != command.proyecto_id:
            raise DiagramaNoEncontradoException()
        if (
            self.diagrama_repository.contar_activos_por_proyecto(command.proyecto_id)
            <= 1
        ):
            raise UltimoDiagramaException()

        if self.referencia_fk_repository is not None:
            self.referencia_fk_repository.eliminar_por_diagrama(command.diagrama_id)
        if self.relacion_repository is not None:
            self.relacion_repository.eliminar_por_diagrama(command.diagrama_id)

        self.atributo_repository.eliminar_por_diagrama(command.diagrama_id)
        self.clase_repository.eliminar_por_diagrama(command.diagrama_id)
        self.diagrama_repository.eliminar(command.diagrama_id)
        self.uow.commit()

