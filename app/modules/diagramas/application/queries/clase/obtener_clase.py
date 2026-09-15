from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.modules.diagramas.application.queries.dtos import AtributoDTO, ClaseDetalleDTO
from app.modules.diagramas.application.validaciones import obtener_diagrama_autorizado
from app.modules.diagramas.domain.exceptions import ClaseNoEncontradaException
from app.modules.diagramas.domain.repositories.atributo_repository import AtributoRepository
from app.modules.diagramas.domain.repositories.clase_repository import ClaseRepository
from app.modules.diagramas.domain.repositories.diagrama_repository import DiagramaRepository
from app.modules.gestion_proyectos.domain.repositories.proyecto_repository import ProyectoRepository


@dataclass(slots=True)
class ObtenerClaseQuery:
    propietario_id: str
    diagrama_id: UUID
    clase_id: UUID


class ObtenerClaseQueryHandler:
    def __init__(self, proyecto_repository: ProyectoRepository, diagrama_repository: DiagramaRepository, clase_repository: ClaseRepository, atributo_repository: AtributoRepository) -> None:
        self.proyecto_repository = proyecto_repository
        self.diagrama_repository = diagrama_repository
        self.clase_repository = clase_repository
        self.atributo_repository = atributo_repository

    def execute(self, query: ObtenerClaseQuery) -> ClaseDetalleDTO:
        obtener_diagrama_autorizado(
            propietario_id=query.propietario_id,
            diagrama_id=query.diagrama_id,
            proyecto_repository=self.proyecto_repository,
            diagrama_repository=self.diagrama_repository,
        )
        clase = self.clase_repository.obtener_por_id(query.clase_id)
        if clase is None or clase.id_diagrama != query.diagrama_id:
            raise ClaseNoEncontradaException()
        atributos = tuple(
            AtributoDTO(a.id, a.id_clase, a.tipo_dato, a.nombre, a.longitud, a.precision, a.escala, a.es_llave_primaria, a.permite_nulo, a.es_unico, a.valor_por_defecto, a.orden_de_posicion)
            for a in self.atributo_repository.listar_por_clase(clase.id)
        )
        return ClaseDetalleDTO(clase.id, clase.id_diagrama, clase.nombre, clase.posicion_x, clase.posicion_y, clase.ancho, atributos)
