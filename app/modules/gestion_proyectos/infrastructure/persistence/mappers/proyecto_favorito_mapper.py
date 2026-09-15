from __future__ import annotations

from app.modules.gestion_proyectos.domain.entities.proyecto_favorito import (
    ProyectoFavorito,
)
from app.modules.gestion_proyectos.infrastructure.persistence.models.proyecto_favorito_model import (
    ProyectoFavoritoModel,
)


class ProyectoFavoritoMapper:
    """Mapeador entre la entidad de dominio ProyectoFavorito y el modelo ProyectoFavoritoModel."""

    @staticmethod
    def a_dominio(modelo: ProyectoFavoritoModel) -> ProyectoFavorito:
        return ProyectoFavorito(
            id=modelo.id,
            usuario_id=modelo.usuario_id,
            proyecto_id=modelo.proyecto_id,
        )

    @staticmethod
    def a_modelo(entidad: ProyectoFavorito) -> ProyectoFavoritoModel:
        return ProyectoFavoritoModel(
            id=entidad.id,
            usuario_id=entidad.usuario_id,
            proyecto_id=entidad.proyecto_id,
        )
