from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.modules.diagramas.application.queries.dtos import DiagramaDTO
from app.modules.diagramas.domain.repositories.diagrama_repository import DiagramaRepository
from app.modules.gestion_proyectos.domain.exceptions import ProyectoNoEncontradoException
from app.modules.gestion_proyectos.domain.repositories.proyecto_repository import ProyectoRepository


@dataclass(slots=True)
class ListarDiagramasQuery:
    propietario_id: str
    proyecto_id: UUID


class ListarDiagramasQueryHandler:
    def __init__(
        self,
        proyecto_repository: ProyectoRepository,
        diagrama_repository: DiagramaRepository,
    ) -> None:
        self.proyecto_repository = proyecto_repository
        self.diagrama_repository = diagrama_repository

    def execute(self, query: ListarDiagramasQuery) -> tuple[DiagramaDTO, ...]:
        proyecto = self.proyecto_repository.obtener_por_id(query.proyecto_id)
        if proyecto is None or proyecto.propietario_id != query.propietario_id:
            raise ProyectoNoEncontradoException()
        return tuple(
            DiagramaDTO(
                id=diagrama.id,
                id_proyecto=diagrama.id_proyecto,
                nombre=diagrama.nombre,
                numero=diagrama.numero,
            )
            for diagrama in self.diagrama_repository.listar_por_proyecto(query.proyecto_id)
        )
