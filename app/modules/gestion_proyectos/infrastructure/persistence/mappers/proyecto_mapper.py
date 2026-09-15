from __future__ import annotations

from app.modules.gestion_proyectos.domain.entities.proyecto import (
    ColorProyecto,
    IconoProyecto,
    Proyecto,
)
from app.modules.gestion_proyectos.infrastructure.persistence.models.proyecto_model import (
    ProyectoModel,
)


class ProyectoMapper:
    """Mapeador entre la entidad de dominio Proyecto y el modelo de persistencia ProyectoModel."""

    @staticmethod
    def a_dominio(modelo: ProyectoModel) -> Proyecto:
        return Proyecto(
            id=modelo.id,
            propietario_id=modelo.propietario_id,
            nombre=modelo.nombre,
            color=ColorProyecto(modelo.color),
            icono=IconoProyecto(modelo.icono),
            slug=modelo.slug,
        )

    @staticmethod
    def a_modelo(entidad: Proyecto) -> ProyectoModel:
        return ProyectoModel(
            id=entidad.id,
            propietario_id=entidad.propietario_id,
            nombre=entidad.nombre,
            color=entidad.color.value,
            icono=entidad.icono.value,
            slug=entidad.slug,
        )
