from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.modules.diagramas.application.queries.dtos import AtributoDTO, ClaseDetalleDTO, DiagramaDTO, DiagramaDetalleDTO
from app.modules.diagramas.domain.exceptions import DiagramaNoEncontradoException
from app.modules.diagramas.domain.repositories.atributo_repository import AtributoRepository
from app.modules.diagramas.domain.repositories.clase_repository import ClaseRepository
from app.modules.diagramas.domain.repositories.diagrama_repository import DiagramaRepository
from app.modules.gestion_proyectos.domain.exceptions import (
    ProyectoNoEncontradoException,
    UsuarioBloqueadoException,
)
from app.modules.gestion_proyectos.domain.repositories.colaborador_proyecto_repository import (
    ColaboradorProyectoRepository,
)
from app.modules.gestion_proyectos.domain.repositories.proyecto_repository import ProyectoRepository


@dataclass(slots=True)
class ObtenerDiagramaQuery:
    proyecto_id: UUID
    diagrama_id: UUID
    propietario_id: str | None = None
    usuario_id: str | None = None

    @property
    def id_usuario(self) -> str:
        return self.usuario_id or self.propietario_id or ""


class ObtenerDiagramaQueryHandler:
    def __init__(
        self,
        proyecto_repository: ProyectoRepository,
        diagrama_repository: DiagramaRepository,
        colaborador_repository: ColaboradorProyectoRepository | None = None,
    ) -> None:
        self.proyecto_repository = proyecto_repository
        self.diagrama_repository = diagrama_repository
        self.colaborador_repository = colaborador_repository

    def obtener_entidad(self, query: ObtenerDiagramaQuery):
        proyecto = self.proyecto_repository.obtener_por_id(query.proyecto_id)
        if proyecto is None:
            raise ProyectoNoEncontradoException()

        usuario_id = query.id_usuario
        if proyecto.propietario_id != usuario_id:
            if self.colaborador_repository is not None:
                colaborador = self.colaborador_repository.obtener_por_proyecto_y_usuario(
                    query.proyecto_id, usuario_id
                )
                if colaborador is None:
                    raise ProyectoNoEncontradoException()
                if colaborador.esta_bloqueado():
                    raise UsuarioBloqueadoException()
                if not colaborador.esta_activo():
                    raise ProyectoNoEncontradoException()
            else:
                raise ProyectoNoEncontradoException()

        diagrama = self.diagrama_repository.obtener_por_id(query.diagrama_id)
        if diagrama is None or diagrama.id_proyecto != query.proyecto_id:
            raise DiagramaNoEncontradoException()
        return diagrama

    def execute(self, query: ObtenerDiagramaQuery) -> DiagramaDTO:
        diagrama = self.obtener_entidad(query)
        return DiagramaDTO(diagrama.id, diagrama.id_proyecto, diagrama.nombre, diagrama.numero)


class ObtenerDiagramaCompletoQueryHandler:
    def __init__(
        self,
        proyecto_repository: ProyectoRepository,
        diagrama_repository: DiagramaRepository,
        clase_repository: ClaseRepository,
        atributo_repository: AtributoRepository,
        colaborador_repository: ColaboradorProyectoRepository | None = None,
    ) -> None:
        self.proyecto_repository = proyecto_repository
        self.diagrama_repository = diagrama_repository
        self.clase_repository = clase_repository
        self.atributo_repository = atributo_repository
        self.colaborador_repository = colaborador_repository

    def execute(self, query: ObtenerDiagramaQuery) -> DiagramaDetalleDTO:
        diagrama = ObtenerDiagramaQueryHandler(
            self.proyecto_repository,
            self.diagrama_repository,
            self.colaborador_repository,
        ).obtener_entidad(query)
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
