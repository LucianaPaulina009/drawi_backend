from __future__ import annotations

from sqlalchemy import and_
from sqlmodel import Session, select

from app.modules.gestion_proyectos.application.ports.readers.listado_proyectos_usuario_reader import (
    ItemProyectoUsuarioDTO,
    ListadoProyectosUsuarioReader,
)
from app.modules.gestion_proyectos.infrastructure.persistence.models.proyecto_favorito_model import (
    ProyectoFavoritoModel,
)
from app.modules.gestion_proyectos.infrastructure.persistence.models.proyecto_model import (
    ProyectoModel,
)


class SQLModelListadoProyectosUsuarioReader(ListadoProyectosUsuarioReader):
    """Implementación de lectura optimizada mediante unión SQLModel."""

    def __init__(self, session: Session) -> None:
        self.bd = session

    def listar_por_usuario(
        self, usuario_id: str, solo_favoritos: bool = False
    ) -> list[ItemProyectoUsuarioDTO]:
        condicion_favorito = and_(
            ProyectoFavoritoModel.proyecto_id == ProyectoModel.id,
            ProyectoFavoritoModel.usuario_id == usuario_id,
            ProyectoFavoritoModel.fecha_eliminacion.is_(None),
        )

        sentencia = (
            select(
                ProyectoModel,
                ProyectoFavoritoModel.id.is_not(None).label("es_favorito"),
            )
            .outerjoin(
                ProyectoFavoritoModel,
                condicion_favorito,
            )
            .where(
                ProyectoModel.propietario_id == usuario_id,
                ProyectoModel.fecha_eliminacion.is_(None),
            )
            .order_by(ProyectoModel.fecha_actualizacion.desc())
        )

        if solo_favoritos:
            sentencia = sentencia.where(ProyectoFavoritoModel.id.is_not(None))

        filas = self.bd.exec(sentencia).all()

        return [
            ItemProyectoUsuarioDTO(
                id=fila[0].id,
                nombre=fila[0].nombre,
                color=fila[0].color,
                icono=fila[0].icono,
                fecha_actualizacion=fila[0].fecha_actualizacion,
                es_favorito=bool(fila[1]),
                slug=fila[0].slug,
            )
            for fila in filas
        ]
