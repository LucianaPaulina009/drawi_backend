from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.modules.diagramas.application.validaciones import obtener_diagrama_autorizado
from app.modules.diagramas.domain.entities.clase import Clase
from app.modules.diagramas.domain.repositories.clase_repository import ClaseRepository
from app.modules.diagramas.domain.repositories.diagrama_repository import (
    DiagramaRepository,
)
from app.modules.gestion_proyectos.domain.repositories.proyecto_repository import (
    ProyectoRepository,
)
from app.shared.application.ports import UnitOfWork


@dataclass(slots=True)
class CrearClaseCommand:
    propietario_id: str
    diagrama_id: UUID
    nombre: str
    posicion_x: float
    posicion_y: float
    ancho: float


class CrearClaseUseCase:
    def __init__(
        self,
        proyecto_repository: ProyectoRepository,
        diagrama_repository: DiagramaRepository,
        clase_repository: ClaseRepository,
        uow: UnitOfWork,
    ) -> None:
        self.proyecto_repository = proyecto_repository
        self.diagrama_repository = diagrama_repository
        self.clase_repository = clase_repository
        self.uow = uow

    def execute(self, command: CrearClaseCommand) -> Clase:
        obtener_diagrama_autorizado(
            propietario_id=command.propietario_id,
            diagrama_id=command.diagrama_id,
            proyecto_repository=self.proyecto_repository,
            diagrama_repository=self.diagrama_repository,
        )
        clase = Clase.crear(
            id_diagrama=command.diagrama_id,
            nombre=command.nombre,
            posicion_x=command.posicion_x,
            posicion_y=command.posicion_y,
            ancho=command.ancho,
        )
        self.clase_repository.guardar(clase)
        self.uow.commit()
        return clase
