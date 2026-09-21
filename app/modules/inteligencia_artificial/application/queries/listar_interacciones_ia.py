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
    limite: int = 40
    antes_de_id: UUID | None = None


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

    def execute(self, query: ListarInteraccionesIaQuery) -> list[InteraccionIa]:
        obtener_diagrama_autorizado(
            propietario_id=query.usuario_id,
            diagrama_id=query.diagrama_id,
            proyecto_repository=self.proyecto_repo,
            diagrama_repository=self.diagrama_repo,
            colaborador_repository=self.colaborador_repo,
            exigir_edicion=False,
        )

        return self.interaccion_repo.listar_por_diagrama(
            id_diagrama=query.diagrama_id,
            limite=query.limite,
            antes_de_id=query.antes_de_id,
        )
