from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.modules.diagramas.application.validaciones import (
    obtener_diagrama_autorizado,
)
from app.modules.diagramas.domain.repositories.diagrama_repository import (
    DiagramaRepository,
)
from app.modules.gestion_colaboradores.domain.repositories.colaborador_proyecto_repository import (
    ColaboradorProyectoRepository,
)
from app.modules.gestion_proyectos.domain.repositories.proyecto_repository import (
    ProyectoRepository,
)
from app.modules.inteligencia_artificial.domain.entities.interaccion_ia import (
    InteraccionIa,
)
from app.modules.inteligencia_artificial.domain.repositories.interaccion_ia_repository import (
    InteraccionIaRepository,
)


@dataclass(slots=True)
class ListarInteraccionesIaQuery:
    usuario_id: str
    diagrama_id: UUID
    limite: int = 5
    offset: int = 0
    antes_de_id: UUID | None = None


class ResultadoListaInteracciones(list[InteraccionIa]):
    """Lista de interacciones que preserva compatibilidad con list y expone metadatos de paginación."""

    def __init__(
        self,
        items: list[InteraccionIa],
        total: int,
        hay_mas: bool,
        siguiente_cursor: UUID | None = None,
        offset: int = 0,
        limite: int = 5,
    ) -> None:
        super().__init__(items)
        self.items = items
        self.total = total
        self.hay_mas = hay_mas
        self.siguiente_cursor = siguiente_cursor
        self.offset = offset
        self.limite = limite


class ListarInteraccionesIaQueryHandler:
    """Consulta el historial persistente de interacciones IA de un diagrama autorizado."""

    def __init__(
        self,
        proyecto_repository: ProyectoRepository,
        diagrama_repository: DiagramaRepository,
        interaccion_repository: InteraccionIaRepository,
        colaborador_repository: ColaboradorProyectoRepository | None = None,
    ) -> None:
        self.proyecto_repo = proyecto_repository
        self.diagrama_repo = diagrama_repository
        self.interaccion_repo = interaccion_repository
        self.colaborador_repo = colaborador_repository

    def execute(self, query: ListarInteraccionesIaQuery) -> ResultadoListaInteracciones:
        obtener_diagrama_autorizado(
            propietario_id=query.usuario_id,
            diagrama_id=query.diagrama_id,
            proyecto_repository=self.proyecto_repo,
            diagrama_repository=self.diagrama_repo,
            colaborador_repository=self.colaborador_repo,
            exigir_edicion=False,
        )

        if query.antes_de_id:
            items = self.interaccion_repo.listar_por_diagrama(
                id_diagrama=query.diagrama_id,
                limite=query.limite,
                antes_de_id=query.antes_de_id,
            )
            return ResultadoListaInteracciones(
                items=items,
                total=len(items),
                hay_mas=len(items) == query.limite,
                siguiente_cursor=items[-1].id if len(items) == query.limite and items else None,
                offset=query.offset,
                limite=query.limite,
            )

        items, total = self.interaccion_repo.listar_paginado_por_diagrama(
            id_diagrama=query.diagrama_id,
            limite=query.limite,
            offset=query.offset,
        )
        hay_mas = (query.offset + query.limite) < total
        return ResultadoListaInteracciones(
            items=items,
            total=total,
            hay_mas=hay_mas,
            offset=query.offset,
            limite=query.limite,
        )
