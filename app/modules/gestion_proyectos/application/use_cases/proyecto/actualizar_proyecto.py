from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.modules.gestion_proyectos.domain.entities.proyecto import (
    ColorProyecto,
    IconoProyecto,
    Proyecto,
)
from app.modules.gestion_proyectos.domain.exceptions import (
    ActualizacionProyectoVaciaException,
    ProyectoNoEncontradoException,
    SlugProyectoEnConflictoException,
)
from app.modules.gestion_proyectos.domain.repositories.proyecto_repository import (
    ProyectoRepository,
)
from app.shared.application.ports import UnitOfWork


@dataclass(slots=True)
class ActualizarProyectoCommand:
    propietario_id: str
    proyecto_id: UUID
    nombre: str | None = None
    color: ColorProyecto | str | None = None
    icono: IconoProyecto | str | None = None


class ActualizarProyectoUseCase:
    """Caso de uso para personalizar nombre, color o ícono de un proyecto propio."""

    def __init__(
        self,
        proyecto_repository: ProyectoRepository,
        uow: UnitOfWork,
    ) -> None:
        self.proyecto_repository = proyecto_repository
        self.uow = uow

    def execute(self, command: ActualizarProyectoCommand) -> None:
        if (
            command.nombre is None
            and command.color is None
            and command.icono is None
        ):
            raise ActualizacionProyectoVaciaException()

        proyecto = self.proyecto_repository.obtener_por_id(command.proyecto_id)
        if proyecto is None or proyecto.propietario_id != command.propietario_id:
            raise ProyectoNoEncontradoException()

        nuevo_slug: str | None = None
        if command.nombre is not None:
            nombre_normalizado = Proyecto.normalizar_nombre(command.nombre)
            if nombre_normalizado != proyecto.nombre:
                slug_base = Proyecto.generar_slug(nombre_normalizado)
                nuevo_slug = self._desambiguar_slug(
                    command.propietario_id, slug_base, excluir_id=command.proyecto_id
                )

        proyecto.actualizar(
            nombre=command.nombre,
            color=command.color,
            icono=command.icono,
            nuevo_slug=nuevo_slug,
        )

        self.proyecto_repository.guardar(proyecto)
        self.uow.commit()

    def _desambiguar_slug(
        self, propietario_id: str, slug_base: str, excluir_id: UUID
    ) -> str:
        if not self.proyecto_repository.existe_slug_en_historico(
            propietario_id, slug_base, excluir_id=excluir_id
        ):
            return slug_base

        for sufijo in range(1, 100):
            candidato = f"{slug_base}-{sufijo}"
            if not self.proyecto_repository.existe_slug_en_historico(
                propietario_id, candidato, excluir_id=excluir_id
            ):
                return candidato

        raise SlugProyectoEnConflictoException()
