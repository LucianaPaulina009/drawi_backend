from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.modules.gestion_colaboradores.application.ports.readers.miembros_proyecto_reader import (
    MiembroProyectoDTO,
    MiembrosProyectoReader,
)
from app.modules.gestion_colaboradores.domain.exceptions import (
    NoAutorizadoProyectoException,
)
from app.modules.gestion_colaboradores.domain.repositories.colaborador_proyecto_repository import (
    ColaboradorProyectoRepository,
)
from app.modules.gestion_proyectos.domain.exceptions import (
    ProyectoNoEncontradoException,
)
from app.modules.gestion_proyectos.domain.repositories.proyecto_repository import (
    ProyectoRepository,
)


@dataclass(slots=True)
class ListarMiembrosProyectoQuery:
    usuario_id: str
    proyecto_id: UUID


class ListarMiembrosProyectoQueryHandler:
    """Consulta para listar los miembros de un proyecto enriquecidos con datos de usuario."""

    def __init__(
        self,
        proyecto_repository: ProyectoRepository,
        colaborador_repository: ColaboradorProyectoRepository,
        miembros_reader: MiembrosProyectoReader,
    ) -> None:
        self.proyecto_repository = proyecto_repository
        self.colaborador_repository = colaborador_repository
        self.miembros_reader = miembros_reader

    def execute(self, query: ListarMiembrosProyectoQuery) -> list[MiembroProyectoDTO]:
        proyecto = self.proyecto_repository.obtener_por_id(query.proyecto_id)
        if proyecto is None:
            raise ProyectoNoEncontradoException()

        # Verificar si el solicitante es el propietario o un colaborador activo
        es_propietario = proyecto.propietario_id == query.usuario_id
        if not es_propietario:
            colaborador = self.colaborador_repository.obtener_por_proyecto_y_usuario(
                query.proyecto_id, query.usuario_id
            )
            if colaborador is None or not colaborador.esta_activo():
                raise NoAutorizadoProyectoException()

        return self.miembros_reader.listar_miembros_proyecto(query.proyecto_id)
