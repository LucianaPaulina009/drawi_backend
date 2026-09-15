from __future__ import annotations

from dataclasses import dataclass

from app.modules.gestion_proyectos.application.ports.readers.listado_proyectos_usuario_reader import (
    ItemProyectoUsuarioDTO,
    ListadoProyectosUsuarioReader,
)


@dataclass(frozen=True, slots=True)
class ListarProyectosUsuarioQuery:
    usuario_id: str
    solo_favoritos: bool = False


@dataclass(frozen=True, slots=True)
class ListadoProyectosUsuarioDTO:
    items: list[ItemProyectoUsuarioDTO]


class ListarProyectosUsuarioQueryHandler:
    """Manejador para consultar los proyectos del usuario autenticado."""

    def __init__(self, reader: ListadoProyectosUsuarioReader) -> None:
        self.reader = reader

    def execute(
        self, query: ListarProyectosUsuarioQuery
    ) -> ListadoProyectosUsuarioDTO:
        items = self.reader.listar_por_usuario(
            usuario_id=query.usuario_id,
            solo_favoritos=query.solo_favoritos,
        )
        return ListadoProyectosUsuarioDTO(items=items)
