from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.modules.diagramas.application.queries.dtos import AtributoDTO
from app.modules.diagramas.application.validaciones import obtener_diagrama_autorizado
from app.modules.diagramas.domain.exceptions import AtributoNoEncontradoException, ClaseNoEncontradaException
from app.modules.diagramas.domain.repositories.atributo_repository import AtributoRepository
from app.modules.diagramas.domain.repositories.clase_repository import ClaseRepository
from app.modules.diagramas.domain.repositories.diagrama_repository import DiagramaRepository
from app.modules.gestion_proyectos.domain.repositories.proyecto_repository import ProyectoRepository


@dataclass(slots=True)
class AtributoQuery:
    propietario_id: str
    clase_id: UUID
    atributo_id: UUID | None = None


class AtributoQueryHandler:
    def __init__(self, proyecto_repository: ProyectoRepository, diagrama_repository: DiagramaRepository, clase_repository: ClaseRepository, atributo_repository: AtributoRepository) -> None:
        self.proyecto_repository = proyecto_repository
        self.diagrama_repository = diagrama_repository
        self.clase_repository = clase_repository
        self.atributo_repository = atributo_repository

    def clase_autorizada(self, query: AtributoQuery):
        clase = self.clase_repository.obtener_por_id(query.clase_id)
        if clase is None:
            raise ClaseNoEncontradaException()
        obtener_diagrama_autorizado(
            propietario_id=query.propietario_id,
            diagrama_id=clase.id_diagrama,
            proyecto_repository=self.proyecto_repository,
            diagrama_repository=self.diagrama_repository,
        )
        return clase

    @staticmethod
    def _dto(atributo) -> AtributoDTO:
        return AtributoDTO(atributo.id, atributo.id_clase, atributo.tipo_dato, atributo.nombre, atributo.longitud, atributo.precision, atributo.escala, atributo.es_llave_primaria, atributo.permite_nulo, atributo.es_unico, atributo.valor_por_defecto, atributo.orden_de_posicion)

    def obtener_entidad(self, query: AtributoQuery):
        self.clase_autorizada(query)
        atributo = self.atributo_repository.obtener_por_id(query.atributo_id)
        if atributo is None or atributo.id_clase != query.clase_id:
            raise AtributoNoEncontradoException()
        return atributo

    def listar(self, query: AtributoQuery) -> tuple[AtributoDTO, ...]:
        self.clase_autorizada(query)
        return tuple(self._dto(atributo) for atributo in self.atributo_repository.listar_por_clase(query.clase_id))

    def obtener(self, query: AtributoQuery) -> AtributoDTO:
        return self._dto(self.obtener_entidad(query))
