from __future__ import annotations

from uuid import UUID

from sqlalchemy import or_
from sqlmodel import Session, select

from app.modules.diagramas.domain.entities.referencia_fk import ReferenciaFK
from app.modules.diagramas.domain.repositories.referencia_fk_repository import (
    ReferenciaFKRepository,
)
from app.modules.diagramas.infrastructure.persistence.mappers.referencia_fk_mapper import (
    ReferenciaFKMapper,
)
from app.modules.diagramas.infrastructure.persistence.models.referencia_fk_model import (
    ReferenciaFKModel,
)
from app.modules.diagramas.infrastructure.persistence.models.relacion_model import (
    RelacionModel,
)
from app.shared.infrastructure.db.base_model import ahora_utc


class SQLModelReferenciaFKRepository(ReferenciaFKRepository):
    """Persistencia SQLModel para referencias FK de Diagramas."""

    def __init__(self, session: Session) -> None:
        self.bd = session

    def obtener_por_id(self, referencia_id: UUID) -> ReferenciaFK | None:
        sentencia = select(ReferenciaFKModel).where(
            ReferenciaFKModel.id == referencia_id,
            ReferenciaFKModel.fecha_eliminacion.is_(None),
        )
        registro = self.bd.exec(sentencia).first()
        return ReferenciaFKMapper.a_dominio(registro) if registro else None

    def listar_por_relacion(self, relacion_id: UUID) -> list[ReferenciaFK]:
        sentencia = select(ReferenciaFKModel).where(
            ReferenciaFKModel.id_relacion == relacion_id,
            ReferenciaFKModel.fecha_eliminacion.is_(None),
        )
        return [ReferenciaFKMapper.a_dominio(registro) for registro in self.bd.exec(sentencia)]

    def listar_por_atributo(self, atributo_id: UUID) -> list[ReferenciaFK]:
        sentencia = select(ReferenciaFKModel).where(
            or_(
                ReferenciaFKModel.id_atributo_fk == atributo_id,
                ReferenciaFKModel.id_atributo_referenciado == atributo_id,
            ),
            ReferenciaFKModel.fecha_eliminacion.is_(None),
        )
        return [ReferenciaFKMapper.a_dominio(registro) for registro in self.bd.exec(sentencia)]

    def listar_por_diagrama(self, diagrama_id: UUID) -> list[ReferenciaFK]:
        sentencia = (
            select(ReferenciaFKModel)
            .join(RelacionModel, RelacionModel.id == ReferenciaFKModel.id_relacion)
            .where(
                RelacionModel.id_diagrama == diagrama_id,
                RelacionModel.fecha_eliminacion.is_(None),
                ReferenciaFKModel.fecha_eliminacion.is_(None),
            )
        )
        return [ReferenciaFKMapper.a_dominio(registro) for registro in self.bd.exec(sentencia)]

    def obtener_por_par(
        self,
        relacion_id: UUID,
        id_atributo_fk: UUID,
        id_atributo_referenciado: UUID,
    ) -> ReferenciaFK | None:
        sentencia = select(ReferenciaFKModel).where(
            ReferenciaFKModel.id_relacion == relacion_id,
            ReferenciaFKModel.id_atributo_fk == id_atributo_fk,
            ReferenciaFKModel.id_atributo_referenciado == id_atributo_referenciado,
            ReferenciaFKModel.fecha_eliminacion.is_(None),
        )
        registro = self.bd.exec(sentencia).first()
        return ReferenciaFKMapper.a_dominio(registro) if registro else None

    def guardar(self, referencia_fk: ReferenciaFK) -> None:
        sentencia = select(ReferenciaFKModel).where(ReferenciaFKModel.id == referencia_fk.id)
        existente = self.bd.exec(sentencia).first()
        if existente:
            existente.id_atributo_fk = referencia_fk.id_atributo_fk
            existente.id_atributo_referenciado = referencia_fk.id_atributo_referenciado
            existente.on_delete = referencia_fk.on_delete
            existente.on_update = referencia_fk.on_update
            existente.fecha_actualizacion = ahora_utc()
            self.bd.add(existente)
            return
        self.bd.add(ReferenciaFKMapper.a_modelo(referencia_fk))

    def eliminar(self, referencia_id: UUID) -> None:
        sentencia = select(ReferenciaFKModel).where(
            ReferenciaFKModel.id == referencia_id,
            ReferenciaFKModel.fecha_eliminacion.is_(None),
        )
        registro = self.bd.exec(sentencia).first()
        if registro:
            registro.eliminar_logicamente()
            self.bd.add(registro)

    def eliminar_por_relacion(self, relacion_id: UUID) -> None:
        sentencia = select(ReferenciaFKModel).where(
            ReferenciaFKModel.id_relacion == relacion_id,
            ReferenciaFKModel.fecha_eliminacion.is_(None),
        )
        for ref in self.bd.exec(sentencia):
            ref.eliminar_logicamente()
            self.bd.add(ref)

    def eliminar_por_atributo(self, atributo_id: UUID) -> None:
        sentencia = select(ReferenciaFKModel).where(
            or_(
                ReferenciaFKModel.id_atributo_fk == atributo_id,
                ReferenciaFKModel.id_atributo_referenciado == atributo_id,
            ),
            ReferenciaFKModel.fecha_eliminacion.is_(None),
        )
        for ref in self.bd.exec(sentencia):
            ref.eliminar_logicamente()
            self.bd.add(ref)

    def eliminar_por_clase(self, clase_id: UUID) -> None:
        sentencia = (
            select(ReferenciaFKModel)
            .join(RelacionModel, RelacionModel.id == ReferenciaFKModel.id_relacion)
            .where(
                or_(
                    RelacionModel.id_clase_origen == clase_id,
                    RelacionModel.id_clase_destino == clase_id,
                ),
                ReferenciaFKModel.fecha_eliminacion.is_(None),
            )
        )
        for ref in self.bd.exec(sentencia):
            ref.eliminar_logicamente()
            self.bd.add(ref)

    def eliminar_por_diagrama(self, diagrama_id: UUID) -> None:
        sentencia = (
            select(ReferenciaFKModel)
            .join(RelacionModel, RelacionModel.id == ReferenciaFKModel.id_relacion)
            .where(
                RelacionModel.id_diagrama == diagrama_id,
                ReferenciaFKModel.fecha_eliminacion.is_(None),
            )
        )
        for ref in self.bd.exec(sentencia):
            ref.eliminar_logicamente()
            self.bd.add(ref)
