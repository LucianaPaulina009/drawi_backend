from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.modules.diagramas.application.queries.dtos import DiagramaDTO
from app.modules.diagramas.domain.repositories.diagrama_repository import DiagramaRepository
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
class ListarDiagramasQuery:
    proyecto_id: UUID
    propietario_id: str | None = None
    usuario_id: str | None = None

    @property
    def id_usuario(self) -> str:
        return self.usuario_id or self.propietario_id or ""


class ListarDiagramasQueryHandler:
    def __init__(
        self,
        proyecto_repository: ProyectoRepository,
        diagrama_repository: DiagramaRepository,
        colaborador_repository: ColaboradorProyectoRepository | None = None,
    ) -> None:
        self.proyecto_repository = proyecto_repository
        self.diagrama_repository = diagrama_repository
        self.colaborador_repository = colaborador_repository

    def execute(self, query: ListarDiagramasQuery) -> tuple[DiagramaDTO, ...]:
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

        return tuple(
            DiagramaDTO(
                id=diagrama.id,
                id_proyecto=diagrama.id_proyecto,
                nombre=diagrama.nombre,
                numero=diagrama.numero,
            )
            for diagrama in self.diagrama_repository.listar_por_proyecto(query.proyecto_id)
        )
