from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.modules.diagramas.domain.entities.diagrama import Diagrama
from app.modules.diagramas.domain.exceptions import (
    ActualizacionDiagramaVaciaException,
    DiagramaNoEncontradoException,
)
from app.modules.diagramas.domain.repositories.diagrama_repository import (
    DiagramaRepository,
)
from app.modules.gestion_proyectos.domain.exceptions import ProyectoNoEncontradoException
from app.modules.gestion_proyectos.domain.repositories.proyecto_repository import (
    ProyectoRepository,
)
from app.shared.application.ports import UnitOfWork


@dataclass(slots=True)
class ActualizarDiagramaCommand:
    propietario_id: str
    proyecto_id: UUID
    diagrama_id: UUID
    nombre: str | None = None


class ActualizarDiagramaUseCase:
    def __init__(
        self,
        proyecto_repository: ProyectoRepository,
        diagrama_repository: DiagramaRepository,
        uow: UnitOfWork,
    ) -> None:
        self.proyecto_repository = proyecto_repository
        self.diagrama_repository = diagrama_repository
        self.uow = uow

    def execute(self, command: ActualizarDiagramaCommand) -> Diagrama:
        if command.nombre is None:
            raise ActualizacionDiagramaVaciaException()
        self._validar_proyecto(command.proyecto_id, command.propietario_id)
        diagrama = self.diagrama_repository.obtener_por_id(command.diagrama_id)
        if diagrama is None or diagrama.id_proyecto != command.proyecto_id:
            raise DiagramaNoEncontradoException()
        diagrama.actualizar(nombre=command.nombre)
        self.diagrama_repository.guardar(diagrama)
        self.uow.commit()
        return diagrama

    def _validar_proyecto(self, proyecto_id: UUID, propietario_id: str) -> None:
        proyecto = self.proyecto_repository.obtener_por_id(proyecto_id)
        if proyecto is None or proyecto.propietario_id != propietario_id:
            raise ProyectoNoEncontradoException()
