from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.modules.diagramas.application.validaciones import obtener_diagrama_autorizado
from app.modules.diagramas.domain.entities.clase import Clase
from app.modules.diagramas.domain.exceptions import (
    ActualizacionClaseVaciaException,
    ClaseNoEncontradaException,
)
from app.modules.diagramas.domain.repositories.clase_repository import ClaseRepository
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
class ActualizarClaseCommand:
    propietario_id: str
    diagrama_id: UUID
    clase_id: UUID
    nombre: str | None = None
    posicion_x: float | None = None
    posicion_y: float | None = None
    ancho: float | None = None


class ActualizarClaseUseCase:
    def __init__(
        self,
        proyecto_repository: ProyectoRepository,
        diagrama_repository: DiagramaRepository,
        clase_repository: ClaseRepository,
        uow: UnitOfWork,
        colaborador_repository: ColaboradorProyectoRepository | None = None,
    ) -> None:
        self.proyecto_repository = proyecto_repository
        self.diagrama_repository = diagrama_repository
        self.clase_repository = clase_repository
        self.uow = uow
        self.colaborador_repository = colaborador_repository

    def execute(self, command: ActualizarClaseCommand) -> Clase:
        if all(
            valor is None
            for valor in (
                command.nombre,
                command.posicion_x,
                command.posicion_y,
                command.ancho,
            )
        ):
            raise ActualizacionClaseVaciaException()
        obtener_diagrama_autorizado(
            propietario_id=command.propietario_id,
            diagrama_id=command.diagrama_id,
            proyecto_repository=self.proyecto_repository,
            diagrama_repository=self.diagrama_repository,
            colaborador_repository=self.colaborador_repository,
            exigir_edicion=True,
        )
        clase = self.clase_repository.obtener_por_id(command.clase_id)
        if clase is None or clase.id_diagrama != command.diagrama_id:
            raise ClaseNoEncontradaException()
        clase.actualizar(
            nombre=command.nombre,
            posicion_x=command.posicion_x,
            posicion_y=command.posicion_y,
            ancho=command.ancho,
        )
        self.clase_repository.guardar(clase)
        self.uow.commit()
        return clase
