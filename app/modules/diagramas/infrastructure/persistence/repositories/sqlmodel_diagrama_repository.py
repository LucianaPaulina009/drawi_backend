from __future__ import annotations

from uuid import UUID

from app.modules.diagramas.domain.entities.diagrama import Diagrama
from app.modules.diagramas.domain.repositories.diagrama_repository import (
    DiagramaRepository,
)
from app.modules.diagramas.infrastructure.persistence.mappers.diagrama_mapper import (
    DiagramaMapper,
)
from app.modules.diagramas.infrastructure.persistence.models.diagrama_model import (
    DiagramaModel,
)
from app.shared.infrastructure.db.base_model import ahora_utc
from sqlmodel import Session, func, select


class SQLModelDiagramaRepository(DiagramaRepository):
    """Persistencia SQLModel para Diagramas."""

    def __init__(self, session: Session) -> None:
        self.bd = session

    def obtener_por_id(self, diagrama_id: UUID) -> Diagrama | None:
        sentencia = select(DiagramaModel).where(
            DiagramaModel.id == diagrama_id,
            DiagramaModel.fecha_eliminacion.is_(None),
        )
        registro = self.bd.exec(sentencia).first()
        return DiagramaMapper.a_dominio(registro) if registro else None

    def listar_por_proyecto(self, proyecto_id: UUID) -> list[Diagrama]:
        sentencia = (
            select(DiagramaModel)
            .where(
                DiagramaModel.id_proyecto == proyecto_id,
                DiagramaModel.fecha_eliminacion.is_(None),
            )
            .order_by(DiagramaModel.numero)
        )
        return [DiagramaMapper.a_dominio(registro) for registro in self.bd.exec(sentencia)]

    def obtener_numeros_activos_por_proyecto(self, proyecto_id: UUID) -> list[int]:
        sentencia = (
            select(DiagramaModel.numero)
            .where(
                DiagramaModel.id_proyecto == proyecto_id,
                DiagramaModel.fecha_eliminacion.is_(None),
            )
            .order_by(DiagramaModel.numero)
        )
        return list(self.bd.exec(sentencia))

    def contar_activos_por_proyecto(self, proyecto_id: UUID) -> int:
        sentencia = select(func.count(DiagramaModel.id)).where(
            DiagramaModel.id_proyecto == proyecto_id,
            DiagramaModel.fecha_eliminacion.is_(None),
        )
        return int(self.bd.exec(sentencia).one())

    def guardar(self, diagrama: Diagrama) -> None:
        sentencia = select(DiagramaModel).where(DiagramaModel.id == diagrama.id)
        existente = self.bd.exec(sentencia).first()
        if existente:
            existente.nombre = diagrama.nombre
            existente.numero = diagrama.numero
            existente.fecha_actualizacion = ahora_utc()
            self.bd.add(existente)
            return
        self.bd.add(DiagramaMapper.a_modelo(diagrama))

    def eliminar(self, diagrama_id: UUID) -> None:
        sentencia = select(DiagramaModel).where(
            DiagramaModel.id == diagrama_id,
            DiagramaModel.fecha_eliminacion.is_(None),
        )
        registro = self.bd.exec(sentencia).first()
        if registro:
            registro.eliminar_logicamente()
            self.bd.add(registro)
