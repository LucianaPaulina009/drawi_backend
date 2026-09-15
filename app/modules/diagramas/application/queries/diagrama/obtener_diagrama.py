from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.modules.diagramas.application.queries.dtos import AtributoDTO, ClaseDetalleDTO, DiagramaDTO, DiagramaDetalleDTO
from app.modules.diagramas.domain.exceptions import DiagramaNoEncontradoException
from app.modules.diagramas.domain.repositories.atributo_repository import AtributoRepository
from app.modules.diagramas.domain.repositories.clase_repository import ClaseRepository
from app.modules.diagramas.domain.repositories.diagrama_repository import DiagramaRepository
from app.modules.gestion_proyectos.domain.exceptions import ProyectoNoEncontradoException
from app.modules.gestion_proyectos.domain.repositories.proyecto_repository import ProyectoRepository


@dataclass(slots=True)
class ObtenerDiagramaQuery:
    propietario_id: str
    proyecto_id: UUID
    diagrama_id: UUID


class ObtenerDiagramaQueryHandler:
    def __init__(self, proyecto_repository: ProyectoRepository, diagrama_repository: DiagramaRepository) -> None:
        self.proyecto_repository = proyecto_repository
        self.diagrama_repository = diagrama_repository

    def obtener_entidad(self, query: ObtenerDiagramaQuery):
        proyecto = self.proyecto_repository.obtener_por_id(query.proyecto_id)
        if proyecto is None or proyecto.propietario_id != query.propietario_id:
            raise ProyectoNoEncontradoException()
        diagrama = self.diagrama_repository.obtener_por_id(query.diagrama_id)
        if diagrama is None or diagrama.id_proyecto != query.proyecto_id:
            raise DiagramaNoEncontradoException()
        return diagrama

    def execute(self, query: ObtenerDiagramaQuery) -> DiagramaDTO:
        diagrama = self.obtener_entidad(query)
        return DiagramaDTO(diagrama.id, diagrama.id_proyecto, diagrama.nombre, diagrama.numero)


class ObtenerDiagramaCompletoQueryHandler:
    def __init__(self, proyecto_repository: ProyectoRepository, diagrama_repository: DiagramaRepository, clase_repository: ClaseRepository, atributo_repository: AtributoRepository) -> None:
        self.proyecto_repository = proyecto_repository
        self.diagrama_repository = diagrama_repository
        self.clase_repository = clase_repository
        self.atributo_repository = atributo_repository

    def execute(self, query: ObtenerDiagramaQuery) -> DiagramaDetalleDTO:
        diagrama = ObtenerDiagramaQueryHandler(self.proyecto_repository, self.diagrama_repository).obtener_entidad(query)
        atributos_por_clase: dict[UUID, list[AtributoDTO]] = {}
        for atributo in self.atributo_repository.listar_por_diagrama(diagrama.id):
            atributos_por_clase.setdefault(atributo.id_clase, []).append(
                AtributoDTO(atributo.id, atributo.id_clase, atributo.tipo_dato, atributo.nombre, atributo.longitud, atributo.precision, atributo.escala, atributo.es_llave_primaria, atributo.permite_nulo, atributo.es_unico, atributo.valor_por_defecto, atributo.orden_de_posicion)
            )
        clases = tuple(
            ClaseDetalleDTO(clase.id, clase.id_diagrama, clase.nombre, clase.posicion_x, clase.posicion_y, clase.ancho, tuple(atributos_por_clase.get(clase.id, [])))
            for clase in self.clase_repository.listar_por_diagrama(diagrama.id)
        )
        return DiagramaDetalleDTO(diagrama.id, diagrama.id_proyecto, diagrama.nombre, diagrama.numero, clases)
