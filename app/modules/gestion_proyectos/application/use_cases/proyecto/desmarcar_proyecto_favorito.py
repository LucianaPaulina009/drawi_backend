from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.modules.gestion_proyectos.domain.exceptions import (
    ProyectoNoEncontradoException,
)
from app.modules.gestion_proyectos.domain.repositories.proyecto_favorito_repository import (
    ProyectoFavoritoRepository,
)
from app.modules.gestion_proyectos.domain.repositories.proyecto_repository import (
    ProyectoRepository,
)
from app.shared.application.ports import UnitOfWork


@dataclass(slots=True)
class DesmarcarProyectoFavoritoCommand:
    propietario_id: str
    proyecto_id: UUID


class DesmarcarProyectoFavoritoUseCase:
    """Caso de uso para quitar la marca de favorito de un proyecto propio."""

    def __init__(
        self,
        proyecto_repository: ProyectoRepository,
        proyecto_favorito_repository: ProyectoFavoritoRepository,
        uow: UnitOfWork,
    ) -> None:
        self.proyecto_repository = proyecto_repository
        self.proyecto_favorito_repository = proyecto_favorito_repository
        self.uow = uow

    def execute(self, command: DesmarcarProyectoFavoritoCommand) -> None:
        # Comprobar que el proyecto existe y pertenece al usuario
        proyecto = self.proyecto_repository.obtener_por_id(command.proyecto_id)
        if proyecto is None or proyecto.propietario_id != command.propietario_id:
            raise ProyectoNoEncontradoException()

        # Si está como favorito activo, dar de baja lógica
        activo = self.proyecto_favorito_repository.obtener_activo(
            usuario_id=command.propietario_id,
            proyecto_id=command.proyecto_id,
        )
        if activo is not None:
            self.proyecto_favorito_repository.eliminar(
                usuario_id=command.propietario_id,
                proyecto_id=command.proyecto_id,
            )

        self.uow.commit()
