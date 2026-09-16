from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.modules.diagramas.application.validaciones import obtener_diagrama_autorizado
from app.modules.diagramas.domain.exceptions import ClaseNoEncontradaException
from app.modules.diagramas.domain.repositories.clase_repository import ClaseRepository
from app.modules.diagramas.domain.repositories.atributo_repository import AtributoRepository
from app.modules.diagramas.domain.repositories.diagrama_repository import (
    DiagramaRepository,
)
from app.modules.gestion_proyectos.domain.repositories.colaborador_proyecto_repository import (
    ColaboradorProyectoRepository,
)
from app.modules.gestion_proyectos.domain.repositories.proyecto_repository import (
    ProyectoRepository,
)
from app.shared.application.ports import UnitOfWork


@dataclass(slots=True)
class EliminarClaseCommand:
    propietario_id: str
    diagrama_id: UUID
    clase_id: UUID


class EliminarClaseUseCase:
    def __init__(
        self,
        proyecto_repository: ProyectoRepository,
        diagrama_repository: DiagramaRepository,
        clase_repository: ClaseRepository,
        atributo_repository: AtributoRepository,
        uow: UnitOfWork,
        colaborador_repository: ColaboradorProyectoRepository | None = None,
    ) -> None:
        self.proyecto_repository = proyecto_repository
        self.diagrama_repository = diagrama_repository
        self.clase_repository = clase_repository
        self.atributo_repository = atributo_repository
        self.uow = uow
        self.colaborador_repository = colaborador_repository

    def execute(self, command: EliminarClaseCommand) -> None:
        obtener_diagrama_autorizado(
            propietario_id=command.propietario_id,
            diagrama_id=command.diagrama_id,
            proyecto_repository=self.proyecto_repository,
            diagrama_repository=self.diagrama_repository,
            colaborador_repository=self.colaborador_repository,
        )
        clase = self.clase_repository.obtener_por_id(command.clase_id)
        if clase is None or clase.id_diagrama != command.diagrama_id:
            raise ClaseNoEncontradaException()
        self.atributo_repository.eliminar_por_clase(command.clase_id)
        self.clase_repository.eliminar(command.clase_id)
        self.uow.commit()
