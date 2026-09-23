from sqlalchemy import and_, exists, or_
from sqlmodel import Session, select

from app.modules.gestion_proyectos.application.ports.readers.listado_proyectos_usuario_reader import (
    ItemProyectoUsuarioDTO,
    ListadoProyectosUsuarioReader,
)
from app.modules.gestion_colaboradores.domain.value_objects.estado_colaborador import (
    EstadoColaborador,
)
from app.modules.gestion_colaboradores.infrastructure.persistence.models.colaborador_proyecto_model import (
    ColaboradorProyectoModel,
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

        condicion_acceso = or_(
            ProyectoModel.propietario_id == usuario_id,
            exists(
                select(ColaboradorProyectoModel.id).where(
                    ColaboradorProyectoModel.id_proyecto == ProyectoModel.id,
                    ColaboradorProyectoModel.id_usuario == usuario_id,
                    ColaboradorProyectoModel.estado == EstadoColaborador.ACTIVO.value,
                    ColaboradorProyectoModel.fecha_eliminacion.is_(None),
                )
            ),
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
                condicion_acceso,
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
                propietario_id=fila[0].propietario_id,
                es_dueno=(fila[0].propietario_id == usuario_id),
            )
            for fila in filas
        ]

