from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.modules.diagramas.application.queries.dtos import (
    ReferenciaFKDTO,
    RelacionDetalleDTO,
)
from app.modules.diagramas.application.validaciones import obtener_diagrama_autorizado
from app.modules.diagramas.domain.repositories.diagrama_repository import (
    DiagramaRepository,
)
from app.modules.diagramas.domain.repositories.referencia_fk_repository import (
    ReferenciaFKRepository,
)
from app.modules.diagramas.domain.repositories.relacion_repository import (
    RelacionRepository,
)
from app.modules.gestion_colaboradores.domain.repositories.colaborador_proyecto_repository import (
    ColaboradorProyectoRepository,
)
from app.modules.gestion_proyectos.domain.repositories.proyecto_repository import (
    ProyectoRepository,
)


@dataclass(slots=True)
class ListarRelacionesQuery:
    propietario_id: str
    diagrama_id: UUID


class ListarRelacionesQueryHandler:
    def __init__(
        self,
        proyecto_repository: ProyectoRepository,
        diagrama_repository: DiagramaRepository,
        relacion_repository: RelacionRepository,
        referencia_fk_repository: ReferenciaFKRepository,
        colaborador_repository: ColaboradorProyectoRepository | None = None,
    ) -> None:
        self.proyecto_repository = proyecto_repository
        self.diagrama_repository = diagrama_repository
        self.relacion_repository = relacion_repository
        self.referencia_fk_repository = referencia_fk_repository
        self.colaborador_repository = colaborador_repository

    def execute(self, query: ListarRelacionesQuery) -> list[RelacionDetalleDTO]:
        obtener_diagrama_autorizado(
            propietario_id=query.propietario_id,
            diagrama_id=query.diagrama_id,
            proyecto_repository=self.proyecto_repository,
            diagrama_repository=self.diagrama_repository,
            colaborador_repository=self.colaborador_repository,
        )

        relaciones = self.relacion_repository.listar_por_diagrama(query.diagrama_id)
        todas_referencias = self.referencia_fk_repository.listar_por_diagrama(
            query.diagrama_id
        )

        # Agrupar referencias por id_relacion en memoria para evitar consultas N+1
        referencias_por_relacion: dict[UUID, list[ReferenciaFKDTO]] = {}
        for r in todas_referencias:
            dto = ReferenciaFKDTO(
                id=r.id,
                id_relacion=r.id_relacion,
                id_atributo_fk=r.id_atributo_fk,
                id_atributo_referenciado=r.id_atributo_referenciado,
                on_delete=r.on_delete,
                on_update=r.on_update,
            )
            referencias_por_relacion.setdefault(r.id_relacion, []).append(dto)

        return [
            RelacionDetalleDTO(
                id=rel.id,
                id_diagrama=rel.id_diagrama,
                id_clase_origen=rel.id_clase_origen,
                id_clase_destino=rel.id_clase_destino,
                tipo_relacion=rel.tipo_relacion,
                cardinalidad_origen=rel.cardinalidad_origen,
                cardinalidad_destino=rel.cardinalidad_destino,
                conector_origen=rel.conector_origen,
                conector_destino=rel.conector_destino,
                nombre=rel.nombre,
                referencias_fk=tuple(referencias_por_relacion.get(rel.id, [])),
            )
            for rel in relaciones
        ]
