from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.modules.diagramas.application.queries.dtos import (
    ReferenciaFKDTO,
    RelacionDetalleDTO,
)
from app.modules.diagramas.application.validaciones import obtener_diagrama_autorizado
from app.modules.diagramas.domain.exceptions import RelacionNoEncontradaException
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
class ObtenerRelacionQuery:
    propietario_id: str
    diagrama_id: UUID
    relacion_id: UUID


class ObtenerRelacionQueryHandler:
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

    def execute(self, query: ObtenerRelacionQuery) -> RelacionDetalleDTO:
        obtener_diagrama_autorizado(
            propietario_id=query.propietario_id,
            diagrama_id=query.diagrama_id,
            proyecto_repository=self.proyecto_repository,
            diagrama_repository=self.diagrama_repository,
            colaborador_repository=self.colaborador_repository,
        )

        relacion = self.relacion_repository.obtener_por_id(query.relacion_id)
        if relacion is None or relacion.id_diagrama != query.diagrama_id:
            raise RelacionNoEncontradaException()

        referencias = tuple(
            ReferenciaFKDTO(
                id=r.id,
                id_relacion=r.id_relacion,
                id_atributo_fk=r.id_atributo_fk,
                id_atributo_referenciado=r.id_atributo_referenciado,
                on_delete=r.on_delete,
                on_update=r.on_update,
            )
            for r in self.referencia_fk_repository.listar_por_relacion(relacion.id)
        )

        return RelacionDetalleDTO(
            id=relacion.id,
            id_diagrama=relacion.id_diagrama,
            id_clase_origen=relacion.id_clase_origen,
            id_clase_destino=relacion.id_clase_destino,
            tipo_relacion=relacion.tipo_relacion,
            cardinalidad_origen=relacion.cardinalidad_origen,
            cardinalidad_destino=relacion.cardinalidad_destino,
            conector_origen=relacion.conector_origen,
            conector_destino=relacion.conector_destino,
            referencias_fk=referencias,
        )
