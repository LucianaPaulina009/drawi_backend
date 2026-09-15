from __future__ import annotations

from uuid import UUID
from sqlmodel import Session, func, select

from app.modules.gestion_proyectos.domain.entities.proyecto import Proyecto
from app.modules.gestion_proyectos.domain.repositories.proyecto_repository import (
    ProyectoRepository,
)
from app.modules.gestion_proyectos.infrastructure.persistence.mappers.proyecto_mapper import (
    ProyectoMapper,
)
from app.modules.gestion_proyectos.infrastructure.persistence.models.proyecto_model import (
    ProyectoModel,
)
from app.shared.infrastructure.db.base_model import ahora_utc


class SQLModelProyectoRepository(ProyectoRepository):
    """Implementación de persistencia SQLModel para Proyecto."""

    def __init__(self, session: Session) -> None:
        self.bd = session

    def contar_historicos_por_propietario(self, propietario_id: str) -> int:
        sentencia = (
            select(func.count(ProyectoModel.id))
            .where(ProyectoModel.propietario_id == propietario_id)
        )
        total = self.bd.exec(sentencia).one()
        return int(total)

    def obtener_por_id(self, proyecto_id: UUID) -> Proyecto | None:
        sentencia = (
            select(ProyectoModel)
            .where(
                ProyectoModel.id == proyecto_id,
                ProyectoModel.fecha_eliminacion.is_(None),
            )
        )
        registro = self.bd.exec(sentencia).first()
        return ProyectoMapper.a_dominio(registro) if registro else None

    def obtener_por_propietario_y_slug(
        self, propietario_id: str, slug: str
    ) -> Proyecto | None:
        sentencia = (
            select(ProyectoModel)
            .where(
                ProyectoModel.propietario_id == propietario_id,
                ProyectoModel.slug == slug,
            )
        )
        registro = self.bd.exec(sentencia).first()
        return ProyectoMapper.a_dominio(registro) if registro else None

    def existe_slug_en_historico(
        self, propietario_id: str, slug: str, excluir_id: UUID | None = None
    ) -> bool:
        sentencia = (
            select(func.count(ProyectoModel.id))
            .where(
                ProyectoModel.propietario_id == propietario_id,
                ProyectoModel.slug == slug,
            )
        )
        if excluir_id is not None:
            sentencia = sentencia.where(ProyectoModel.id != excluir_id)
        total = self.bd.exec(sentencia).one()
        return int(total) > 0

    def guardar(self, proyecto: Proyecto) -> None:
        sentencia = select(ProyectoModel).where(ProyectoModel.id == proyecto.id)
        existente = self.bd.exec(sentencia).first()
        if existente:
            existente.nombre = proyecto.nombre
            existente.color = proyecto.color.value
            existente.icono = proyecto.icono.value
            existente.slug = proyecto.slug
            existente.fecha_actualizacion = ahora_utc()
            self.bd.add(existente)
        else:
            modelo = ProyectoMapper.a_modelo(proyecto)
            self.bd.add(modelo)

    def eliminar(self, proyecto_id: UUID) -> None:
        sentencia = select(ProyectoModel).where(
            ProyectoModel.id == proyecto_id,
            ProyectoModel.fecha_eliminacion.is_(None),
        )
        registro = self.bd.exec(sentencia).first()
        if registro:
            registro.eliminar_logicamente()
            self.bd.add(registro)
