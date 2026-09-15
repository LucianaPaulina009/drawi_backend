from __future__ import annotations

from dataclasses import dataclass

from app.modules.diagramas.domain.entities.diagrama import Diagrama
from app.modules.diagramas.domain.repositories.diagrama_repository import (
    DiagramaRepository,
)
from app.modules.gestion_proyectos.domain.entities.proyecto import Proyecto
from app.modules.gestion_proyectos.domain.exceptions import (
    SlugProyectoEnConflictoException,
)
from app.modules.gestion_proyectos.domain.repositories.proyecto_repository import (
    ProyectoRepository,
)
from app.shared.application.ports import UnitOfWork


@dataclass(slots=True)
class CrearProyectoCommand:
    propietario_id: str


class CrearProyectoUseCase:
    """Caso de uso para crear un proyecto con valores por defecto y slug único."""

    def __init__(
        self,
        proyecto_repository: ProyectoRepository,
        diagrama_repository: DiagramaRepository,
        uow: UnitOfWork,
    ) -> None:
        self.proyecto_repository = proyecto_repository
        self.diagrama_repository = diagrama_repository
        self.uow = uow

    def execute(self, command: CrearProyectoCommand) -> str:
        numero = self.proyecto_repository.contar_historicos_por_propietario(
            command.propietario_id
        )
        slug_base = Proyecto.generar_slug(f"Nuevo Proyecto {numero}")
        slug = self._desambiguar_slug(command.propietario_id, slug_base)

        proyecto = Proyecto.crear(
            propietario_id=command.propietario_id,
            numero=numero,
            slug=slug,
        )

        self.proyecto_repository.guardar(proyecto)
        self.diagrama_repository.guardar(
            Diagrama.crear(
                id_proyecto=proyecto.id,
                numero=1,
                nombre="Página 1",
            )
        )
        self.uow.commit()

        return proyecto.slug

    def _desambiguar_slug(self, propietario_id: str, slug_base: str) -> str:
        if not self.proyecto_repository.existe_slug_en_historico(propietario_id, slug_base):
            return slug_base

        for sufijo in range(1, 100):
            candidato = f"{slug_base}-{sufijo}"
            if not self.proyecto_repository.existe_slug_en_historico(
                propietario_id, candidato
            ):
                return candidato

        raise SlugProyectoEnConflictoException()
