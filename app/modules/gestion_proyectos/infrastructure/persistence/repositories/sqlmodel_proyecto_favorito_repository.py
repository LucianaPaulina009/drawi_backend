from __future__ import annotations

from uuid import UUID
from sqlmodel import Session, select

from app.modules.gestion_proyectos.domain.entities.proyecto_favorito import (
    ProyectoFavorito,
)
from app.modules.gestion_proyectos.domain.repositories.proyecto_favorito_repository import (
    ProyectoFavoritoRepository,
)
from app.modules.gestion_proyectos.infrastructure.persistence.mappers.proyecto_favorito_mapper import (
    ProyectoFavoritoMapper,
)
from app.modules.gestion_proyectos.infrastructure.persistence.models.proyecto_favorito_model import (
    ProyectoFavoritoModel,
)


class SQLModelProyectoFavoritoRepository(ProyectoFavoritoRepository):
    """Implementación de persistencia SQLModel para ProyectoFavorito."""

    def __init__(self, session: Session) -> None:
        self.bd = session

    def obtener_activo(
        self, usuario_id: str, proyecto_id: UUID
    ) -> ProyectoFavorito | None:
        sentencia = select(ProyectoFavoritoModel).where(
            ProyectoFavoritoModel.usuario_id == usuario_id,
            ProyectoFavoritoModel.proyecto_id == proyecto_id,
            ProyectoFavoritoModel.fecha_eliminacion.is_(None),
        )
        registro = self.bd.exec(sentencia).first()
        return ProyectoFavoritoMapper.a_dominio(registro) if registro else None

    def obtener_eliminado(
        self, usuario_id: str, proyecto_id: UUID
    ) -> ProyectoFavorito | None:
        sentencia = select(ProyectoFavoritoModel).where(
            ProyectoFavoritoModel.usuario_id == usuario_id,
            ProyectoFavoritoModel.proyecto_id == proyecto_id,
            ProyectoFavoritoModel.fecha_eliminacion.is_not(None),
        )
        registro = self.bd.exec(sentencia).first()
        return ProyectoFavoritoMapper.a_dominio(registro) if registro else None

    def guardar(self, favorito: ProyectoFavorito) -> None:
        modelo = ProyectoFavoritoMapper.a_modelo(favorito)
        self.bd.add(modelo)

    def restaurar(self, favorito_id: UUID) -> None:
        sentencia = select(ProyectoFavoritoModel).where(
            ProyectoFavoritoModel.id == favorito_id
        )
        registro = self.bd.exec(sentencia).first()
        if registro and registro.fecha_eliminacion is not None:
            registro.restaurar()
            self.bd.add(registro)

    def eliminar(self, usuario_id: str, proyecto_id: UUID) -> None:
        sentencia = select(ProyectoFavoritoModel).where(
            ProyectoFavoritoModel.usuario_id == usuario_id,
            ProyectoFavoritoModel.proyecto_id == proyecto_id,
            ProyectoFavoritoModel.fecha_eliminacion.is_(None),
        )
        registro = self.bd.exec(sentencia).first()
        if registro:
            registro.eliminar_logicamente()
            self.bd.add(registro)
