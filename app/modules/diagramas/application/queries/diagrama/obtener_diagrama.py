from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.modules.diagramas.application.queries.dtos import (
    AtributoDTO,
    ClaseDetalleDTO,
    DiagramaDTO,
    DiagramaDetalleDTO,
    ReferenciaFKDTO,
    RelacionDetalleDTO,
)
from app.modules.diagramas.domain.exceptions import DiagramaNoEncontradoException
from app.modules.diagramas.domain.repositories.atributo_repository import AtributoRepository
from app.modules.diagramas.domain.repositories.clase_repository import ClaseRepository
from app.modules.diagramas.domain.repositories.diagrama_repository import DiagramaRepository
from app.modules.diagramas.domain.repositories.referencia_fk_repository import (
    ReferenciaFKRepository,
)
from app.modules.diagramas.domain.repositories.relacion_repository import (
    RelacionRepository,
)
from app.modules.gestion_colaboradores.domain.exceptions import (
    UsuarioBloqueadoException,
)
from app.modules.gestion_colaboradores.domain.repositories.colaborador_proyecto_repository import (
    ColaboradorProyectoRepository,
)
from app.modules.gestion_proyectos.domain.exceptions import (
    ProyectoNoEncontradoException,
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
        relacion_repository: RelacionRepository | None = None,
        referencia_fk_repository: ReferenciaFKRepository | None = None,
    ) -> None:
        self.proyecto_repository = proyecto_repository
        self.diagrama_repository = diagrama_repository
        self.clase_repository = clase_repository
        self.atributo_repository = atributo_repository
        self.colaborador_repository = colaborador_repository
        self.relacion_repository = relacion_repository
        self.referencia_fk_repository = referencia_fk_repository

    def execute(self, query: ObtenerDiagramaQuery) -> DiagramaDetalleDTO:
        diagrama = ObtenerDiagramaQueryHandler(
            self.proyecto_repository,
            self.diagrama_repository,
            self.colaborador_repository,
        ).obtener_entidad(query)

        atributos_por_clase: dict[UUID, list[AtributoDTO]] = {}
        for atributo in self.atributo_repository.listar_por_diagrama(diagrama.id):
            atributos_por_clase.setdefault(atributo.id_clase, []).append(
                AtributoDTO(
                    id=atributo.id,
                    id_clase=atributo.id_clase,
                    tipo_dato=atributo.tipo_dato,
                    nombre=atributo.nombre,
                    longitud=atributo.longitud,
                    precision=atributo.precision,
                    escala=atributo.escala,
                    es_llave_primaria=atributo.es_llave_primaria,
                    permite_nulo=atributo.permite_nulo,
                    es_unico=atributo.es_unico,
                    valor_por_defecto=atributo.valor_por_defecto,
                    orden_de_posicion=atributo.orden_de_posicion,
                    procedencia=atributo.procedencia,
                )
            )

        clases = tuple(
            ClaseDetalleDTO(
                id=clase.id,
                id_diagrama=clase.id_diagrama,
                nombre=clase.nombre,
                posicion_x=clase.posicion_x,
                posicion_y=clase.posicion_y,
                ancho=clase.ancho,
                atributos=tuple(atributos_por_clase.get(clase.id, [])),
            )
            for clase in self.clase_repository.listar_por_diagrama(diagrama.id)
        )

        referencias_por_relacion: dict[UUID, list[ReferenciaFKDTO]] = {}
        if self.referencia_fk_repository is not None:
            for rfk in self.referencia_fk_repository.listar_por_diagrama(diagrama.id):
                referencias_por_relacion.setdefault(rfk.id_relacion, []).append(
                    ReferenciaFKDTO(
                        id=rfk.id,
                        id_relacion=rfk.id_relacion,
                        id_atributo_fk=rfk.id_atributo_fk,
                        id_atributo_referenciado=rfk.id_atributo_referenciado,
                        on_delete=rfk.on_delete,
                        on_update=rfk.on_update,
                    )
                )

        relaciones: list[RelacionDetalleDTO] = []
        if self.relacion_repository is not None:
            for rel in self.relacion_repository.listar_por_diagrama(diagrama.id):
                relaciones.append(
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
                        referencias_fk=tuple(referencias_por_relacion.get(rel.id, [])),
                    )
                )

        return DiagramaDetalleDTO(
            id=diagrama.id,
            id_proyecto=diagrama.id_proyecto,
            nombre=diagrama.nombre,
            numero=diagrama.numero,
            clases=clases,
            relaciones=tuple(relaciones),
        )
