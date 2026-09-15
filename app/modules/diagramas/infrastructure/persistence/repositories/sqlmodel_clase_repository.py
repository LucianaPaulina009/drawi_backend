from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, select

from app.modules.diagramas.domain.entities.clase import Clase
from app.modules.diagramas.domain.repositories.clase_repository import ClaseRepository
from app.modules.diagramas.infrastructure.persistence.mappers.clase_mapper import (
    ClaseMapper,
)
from app.modules.diagramas.infrastructure.persistence.models.clase_model import ClaseModel
from app.shared.infrastructure.db.base_model import ahora_utc


class SQLModelClaseRepository(ClaseRepository):
    """Persistencia SQLModel para clases de Diagramas."""

    def __init__(self, session: Session) -> None:
        self.bd = session

    def obtener_por_id(self, clase_id: UUID) -> Clase | None:
        sentencia = select(ClaseModel).where(
            ClaseModel.id == clase_id,
            ClaseModel.fecha_eliminacion.is_(None),
        )
        registro = self.bd.exec(sentencia).first()
        return ClaseMapper.a_dominio(registro) if registro else None

    def listar_por_diagrama(self, diagrama_id: UUID) -> list[Clase]:
        sentencia = select(ClaseModel).where(
            ClaseModel.id_diagrama == diagrama_id,
            ClaseModel.fecha_eliminacion.is_(None),
        )
        return [ClaseMapper.a_dominio(registro) for registro in self.bd.exec(sentencia)]

    def guardar(self, clase: Clase) -> None:
        sentencia = select(ClaseModel).where(ClaseModel.id == clase.id)
        existente = self.bd.exec(sentencia).first()
        if existente:
            existente.nombre = clase.nombre
            existente.posicion_x = clase.posicion_x
            existente.posicion_y = clase.posicion_y
            existente.ancho = clase.ancho
            existente.fecha_actualizacion = ahora_utc()
            self.bd.add(existente)
            return
        self.bd.add(ClaseMapper.a_modelo(clase))

    def eliminar(self, clase_id: UUID) -> None:
        sentencia = select(ClaseModel).where(
            ClaseModel.id == clase_id,
            ClaseModel.fecha_eliminacion.is_(None),
        )
        registro = self.bd.exec(sentencia).first()
        if registro:
            registro.eliminar_logicamente()
            self.bd.add(registro)

    def eliminar_por_diagrama(self, diagrama_id: UUID) -> None:
        for clase in self.bd.exec(
            select(ClaseModel).where(
                ClaseModel.id_diagrama == diagrama_id,
                ClaseModel.fecha_eliminacion.is_(None),
            )
        ):
            clase.eliminar_logicamente()
            self.bd.add(clase)
