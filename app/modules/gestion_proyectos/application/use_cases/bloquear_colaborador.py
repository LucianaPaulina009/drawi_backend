from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.modules.gestion_proyectos.domain.exceptions import (
    ColaboradorNoEncontradoException,
    NoAutorizadoProyectoException,
    OperacionNoPermitidaPropietarioException,
    ProyectoNoEncontradoException,
)
from app.modules.gestion_proyectos.domain.repositories.colaborador_proyecto_repository import (
    ColaboradorProyectoRepository,
)
from app.modules.gestion_proyectos.domain.repositories.proyecto_repository import (
    ProyectoRepository,
)
from app.shared.application.ports import UnitOfWork


@dataclass(slots=True)
class BloquearColaboradorCommand:
    propietario_id: str
    proyecto_id: UUID
    colaborador_id: UUID


class BloquearColaboradorUseCase:
    """Caso de uso para bloquear a un colaborador en un proyecto propio (conservando rol e impidiendo reingreso)."""

    def __init__(
        self,
        proyecto_repository: ProyectoRepository,
        colaborador_repository: ColaboradorProyectoRepository,
        uow: UnitOfWork,
    ) -> None:
        self.proyecto_repository = proyecto_repository
        self.colaborador_repository = colaborador_repository
        self.uow = uow

    def execute(self, command: BloquearColaboradorCommand) -> None:
        proyecto = self.proyecto_repository.obtener_por_id(command.proyecto_id)
        if proyecto is None:
            raise ProyectoNoEncontradoException()

        if proyecto.propietario_id != command.propietario_id:
            raise NoAutorizadoProyectoException()

        if command.colaborador_id == proyecto.id:
            raise OperacionNoPermitidaPropietarioException()

        colaborador = self.colaborador_repository.obtener_por_id(command.colaborador_id)
        if colaborador is None or colaborador.id_proyecto != command.proyecto_id:
            raise ColaboradorNoEncontradoException()

        if colaborador.id_usuario == proyecto.propietario_id:
            raise OperacionNoPermitidaPropietarioException()

        colaborador.bloquear()
        self.colaborador_repository.guardar(colaborador)
        self.uow.commit()
