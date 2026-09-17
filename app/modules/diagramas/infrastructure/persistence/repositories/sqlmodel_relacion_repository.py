from __future__ import annotations

from uuid import UUID

from sqlalchemy import or_
from sqlmodel import Session, select

from app.modules.diagramas.domain.entities.relacion import Relacion
from app.modules.diagramas.domain.repositories.relacion_repository import RelacionRepository
from app.modules.diagramas.infrastructure.persistence.mappers.relacion_mapper import (
    RelacionMapper,
)
from app.modules.diagramas.infrastructure.persistence.models.relacion_model import (
    RelacionModel,
)
from app.shared.infrastructure.db.base_model import ahora_utc


class SQLModelRelacionRepository(RelacionRepository):
    """Persistencia SQLModel para relaciones UML de Diagramas."""

    def __init__(self, session: Session) -> None:
        self.bd = session

    def obtener_por_id(self, relacion_id: UUID) -> Relacion | None:
        sentencia = select(RelacionModel).where(
            RelacionModel.id == relacion_id,
            RelacionModel.fecha_eliminacion.is_(None),
        )
        registro = self.bd.exec(sentencia).first()
        return RelacionMapper.a_dominio(registro) if registro else None

    def listar_por_diagrama(self, diagrama_id: UUID) -> list[Relacion]:
        sentencia = select(RelacionModel).where(
            RelacionModel.id_diagrama == diagrama_id,
            RelacionModel.fecha_eliminacion.is_(None),
        )
        return [RelacionMapper.a_dominio(registro) for registro in self.bd.exec(sentencia)]

    def listar_por_clase(self, clase_id: UUID) -> list[Relacion]:
        sentencia = select(RelacionModel).where(
            or_(
                RelacionModel.id_clase_origen == clase_id,
                RelacionModel.id_clase_destino == clase_id,
            ),
            RelacionModel.fecha_eliminacion.is_(None),
        )
        return [RelacionMapper.a_dominio(registro) for registro in self.bd.exec(sentencia)]

    def guardar(self, relacion: Relacion) -> None:
        sentencia = select(RelacionModel).where(RelacionModel.id == relacion.id)
        existente = self.bd.exec(sentencia).first()
        if existente:
            existente.id_clase_origen = relacion.id_clase_origen
            existente.id_clase_destino = relacion.id_clase_destino
            existente.tipo_relacion = relacion.tipo_relacion
            existente.cardinalidad_origen = relacion.cardinalidad_origen
            existente.cardinalidad_destino = relacion.cardinalidad_destino
            existente.conector_origen = relacion.conector_origen
            existente.conector_destino = relacion.conector_destino
            existente.fecha_actualizacion = ahora_utc()
            self.bd.add(existente)
            return
        self.bd.add(RelacionMapper.a_modelo(relacion))

    def eliminar(self, relacion_id: UUID) -> None:
        sentencia = select(RelacionModel).where(
            RelacionModel.id == relacion_id,
            RelacionModel.fecha_eliminacion.is_(None),
        )
        registro = self.bd.exec(sentencia).first()
        if registro:
            registro.eliminar_logicamente()
            self.bd.add(registro)

    def eliminar_por_clase(self, clase_id: UUID) -> None:
        sentencia = select(RelacionModel).where(
            or_(
                RelacionModel.id_clase_origen == clase_id,
                RelacionModel.id_clase_destino == clase_id,
            ),
            RelacionModel.fecha_eliminacion.is_(None),
        )
        for relacion in self.bd.exec(sentencia):
            relacion.eliminar_logicamente()
            self.bd.add(relacion)

    def eliminar_por_diagrama(self, diagrama_id: UUID) -> None:
        sentencia = select(RelacionModel).where(
            RelacionModel.id_diagrama == diagrama_id,
            RelacionModel.fecha_eliminacion.is_(None),
        )
        for relacion in self.bd.exec(sentencia):
            relacion.eliminar_logicamente()
            self.bd.add(relacion)
