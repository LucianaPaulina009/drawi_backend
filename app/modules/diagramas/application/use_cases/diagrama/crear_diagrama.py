from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.modules.diagramas.domain.entities.diagrama import Diagrama
from app.modules.diagramas.domain.repositories.diagrama_repository import (
    DiagramaRepository,
)
from app.modules.gestion_proyectos.domain.exceptions import ProyectoNoEncontradoException
from app.modules.gestion_proyectos.domain.repositories.proyecto_repository import (
    ProyectoRepository,
)
from app.shared.application.ports import UnitOfWork


@dataclass(slots=True)
class CrearDiagramaCommand:
    propietario_id: str
    proyecto_id: UUID
    nombre: str | None = None


class CrearDiagramaUseCase:
    def __init__(
        self,
        proyecto_repository: ProyectoRepository,
        diagrama_repository: DiagramaRepository,
        uow: UnitOfWork,
    ) -> None:
        self.proyecto_repository = proyecto_repository
        self.diagrama_repository = diagrama_repository
        self.uow = uow

    def execute(self, command: CrearDiagramaCommand) -> Diagrama:
        proyecto = self.proyecto_repository.obtener_por_id(command.proyecto_id)
        if proyecto is None or proyecto.propietario_id != command.propietario_id:
            raise ProyectoNoEncontradoException()

        numero = Diagrama.obtener_siguiente_numero(
            self.diagrama_repository.obtener_numeros_activos_por_proyecto(
                command.proyecto_id
            )
        )
        diagrama = Diagrama.crear(
            id_proyecto=command.proyecto_id,
            numero=numero,
            nombre=command.nombre,
        )
        self.diagrama_repository.guardar(diagrama)
        self.uow.commit()
        return diagrama
