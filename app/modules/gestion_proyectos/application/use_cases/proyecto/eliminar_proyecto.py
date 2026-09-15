from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.modules.gestion_proyectos.domain.exceptions import (
    ProyectoNoEncontradoException,
)
from app.modules.gestion_proyectos.domain.repositories.proyecto_repository import (
    ProyectoRepository,
)
from app.shared.application.ports import UnitOfWork


@dataclass(slots=True)
class EliminarProyectoCommand:
    propietario_id: str
    proyecto_id: UUID


class EliminarProyectoUseCase:
    """Caso de uso para eliminar lógicamente un proyecto propio."""

    def __init__(
        self,
        proyecto_repository: ProyectoRepository,
        uow: UnitOfWork,
    ) -> None:
        self.proyecto_repository = proyecto_repository
        self.uow = uow

    def execute(self, command: EliminarProyectoCommand) -> None:
        proyecto = self.proyecto_repository.obtener_por_id(command.proyecto_id)
        if proyecto is None or proyecto.propietario_id != command.propietario_id:
            raise ProyectoNoEncontradoException()

        self.proyecto_repository.eliminar(command.proyecto_id)
        self.uow.commit()
