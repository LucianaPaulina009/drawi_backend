from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.modules.gestion_proyectos.domain.entities.proyecto_favorito import (
    ProyectoFavorito,
)
from app.modules.gestion_proyectos.domain.exceptions import ProyectoNoEncontradoException
from app.modules.gestion_proyectos.domain.repositories.proyecto_favorito_repository import (
    ProyectoFavoritoRepository,
)
from app.modules.gestion_proyectos.domain.repositories.proyecto_repository import (
    ProyectoRepository,
)
from app.shared.application.ports import UnitOfWork


@dataclass(slots=True)
class AgregarProyectoFavoritoCommand:
    propietario_id: str
    proyecto_id: UUID


class AgregarProyectoFavoritoUseCase:
    """Caso de uso para marcar un proyecto propio como favorito."""

    def __init__(
        self,
        proyecto_repository: ProyectoRepository,
        proyecto_favorito_repository: ProyectoFavoritoRepository,
        uow: UnitOfWork,
    ) -> None:
        self.proyecto_repository = proyecto_repository
        self.proyecto_favorito_repository = proyecto_favorito_repository
        self.uow = uow

    def execute(self, command: AgregarProyectoFavoritoCommand) -> None:
        # Verificar que el proyecto existe, está activo y pertenece al usuario
        proyecto = self.proyecto_repository.obtener_por_id(command.proyecto_id)
        if proyecto is None or proyecto.propietario_id != command.propietario_id:
            raise ProyectoNoEncontradoException()

        # Si ya es favorito activo, la operación es idempotente
        activo = self.proyecto_favorito_repository.obtener_activo(
            usuario_id=command.propietario_id,
            proyecto_id=command.proyecto_id,
        )
        if activo is not None:
            self.uow.commit()
            return

        # Si estaba eliminado lógicamente, restaurar
        eliminado = self.proyecto_favorito_repository.obtener_eliminado(
            usuario_id=command.propietario_id,
            proyecto_id=command.proyecto_id,
        )
        if eliminado is not None:
            self.proyecto_favorito_repository.restaurar(eliminado.id)
        else:
            # Crear nueva relación de favorito
            nuevo_favorito = ProyectoFavorito.crear(
                usuario_id=command.propietario_id,
                proyecto_id=command.proyecto_id,
            )
            self.proyecto_favorito_repository.guardar(nuevo_favorito)

        self.uow.commit()
