from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.modules.diagramas.application.queries.dtos import ClaseDTO
from app.modules.diagramas.application.validaciones import obtener_diagrama_autorizado
from app.modules.diagramas.domain.repositories.clase_repository import ClaseRepository
from app.modules.diagramas.domain.repositories.diagrama_repository import DiagramaRepository
from app.modules.gestion_proyectos.domain.repositories.colaborador_proyecto_repository import (
    ColaboradorProyectoRepository,
)
from app.modules.gestion_proyectos.domain.repositories.proyecto_repository import ProyectoRepository


@dataclass(slots=True)
class ListarClasesQuery:
    propietario_id: str
    diagrama_id: UUID


class ListarClasesQueryHandler:
    def __init__(
        self,
        proyecto_repository: ProyectoRepository,
        diagrama_repository: DiagramaRepository,
        clase_repository: ClaseRepository,
        colaborador_repository: ColaboradorProyectoRepository | None = None,
    ) -> None:
        self.proyecto_repository = proyecto_repository
        self.diagrama_repository = diagrama_repository
        self.clase_repository = clase_repository
        self.colaborador_repository = colaborador_repository

    def execute(self, query: ListarClasesQuery) -> tuple[ClaseDTO, ...]:
        obtener_diagrama_autorizado(
            propietario_id=query.propietario_id,
            diagrama_id=query.diagrama_id,
            proyecto_repository=self.proyecto_repository,
            diagrama_repository=self.diagrama_repository,
            colaborador_repository=self.colaborador_repository,
        )
        return tuple(
            ClaseDTO(
                id=clase.id,
                id_diagrama=clase.id_diagrama,
                nombre=clase.nombre,
                posicion_x=clase.posicion_x,
                posicion_y=clase.posicion_y,
                ancho=clase.ancho,
            )
            for clase in self.clase_repository.listar_por_diagrama(query.diagrama_id)
        )
