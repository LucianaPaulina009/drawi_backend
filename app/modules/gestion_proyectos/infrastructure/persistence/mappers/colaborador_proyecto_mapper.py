from __future__ import annotations

from app.modules.gestion_proyectos.domain.entities.colaborador_proyecto import (
    ColaboradorProyecto,
)
from app.modules.gestion_proyectos.domain.value_objects.estado_colaborador import (
    EstadoColaborador,
)
from app.modules.gestion_proyectos.domain.value_objects.rol_colaborador import (
    RolColaborador,
)
from app.modules.gestion_proyectos.infrastructure.persistence.models.colaborador_proyecto_model import (
    ColaboradorProyectoModel,
)


class ColaboradorProyectoMapper:
    """Mapper entre la entidad de dominio ColaboradorProyecto y el modelo SQLModel."""

    @staticmethod
    def a_dominio(modelo: ColaboradorProyectoModel) -> ColaboradorProyecto:
        return ColaboradorProyecto(
            id=modelo.id,
            id_proyecto=modelo.id_proyecto,
            id_usuario=modelo.id_usuario,
            rol=RolColaborador(modelo.rol),
            estado=EstadoColaborador(modelo.estado),
        )

    @staticmethod
    def a_modelo(entidad: ColaboradorProyecto) -> ColaboradorProyectoModel:
        return ColaboradorProyectoModel(
            id=entidad.id,
            id_proyecto=entidad.id_proyecto,
            id_usuario=entidad.id_usuario,
            rol=entidad.rol.value,
            estado=entidad.estado.value,
        )
