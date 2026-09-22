from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, select

from app.modules.inteligencia_artificial.domain.entities.interaccion_ia import (
    InteraccionIa,
)
from app.modules.inteligencia_artificial.domain.repositories.interaccion_ia_repository import (
    InteraccionIaRepository,
)
from app.modules.inteligencia_artificial.infrastructure.persistence.mappers.interaccion_ia_mapper import (
    InteraccionIaMapper,
)
from app.modules.inteligencia_artificial.infrastructure.persistence.models.interaccion_ia_model import (
    InteraccionIaModel,
)
from app.shared.infrastructure.db.base_model import ahora_utc


class SQLModelInteraccionIaRepository(InteraccionIaRepository):
    """Persistencia SQLModel para interacciones de inteligencia artificial."""

    def __init__(self, session: Session) -> None:
        self.bd = session

    def obtener_por_id(self, interaccion_id: UUID) -> InteraccionIa | None:
        sentencia = select(InteraccionIaModel).where(
            InteraccionIaModel.id == interaccion_id,
            InteraccionIaModel.fecha_eliminacion.is_(None),
        )
        registro = self.bd.exec(sentencia).first()
        return InteraccionIaMapper.a_dominio(registro) if registro else None

    def obtener_por_idempotencia(
        self, id_usuario: str, id_diagrama: UUID, clave_idempotencia: UUID
    ) -> InteraccionIa | None:
        sentencia = select(InteraccionIaModel).where(
            InteraccionIaModel.id_usuario == id_usuario,
            InteraccionIaModel.id_diagrama == id_diagrama,
            InteraccionIaModel.clave_idempotencia == clave_idempotencia,
            InteraccionIaModel.fecha_eliminacion.is_(None),
        )
        registro = self.bd.exec(sentencia).first()
        return InteraccionIaMapper.a_dominio(registro) if registro else None

    def listar_por_diagrama(
        self,
        id_diagrama: UUID,
        limite: int = 40,
        antes_de_id: UUID | None = None,
    ) -> list[InteraccionIa]:
        sentencia = (
            select(InteraccionIaModel)
            .where(
                InteraccionIaModel.id_diagrama == id_diagrama,
                InteraccionIaModel.fecha_eliminacion.is_(None),
            )
        )

        if antes_de_id:
            cursor_ref = self.bd.exec(
                select(InteraccionIaModel.fecha_creacion).where(
                    InteraccionIaModel.id == antes_de_id,
                    InteraccionIaModel.fecha_eliminacion.is_(None),
                )
            ).first()
            if cursor_ref:
                sentencia = sentencia.where(InteraccionIaModel.fecha_creacion < cursor_ref)

        sentencia = sentencia.order_by(InteraccionIaModel.fecha_creacion.asc()).limit(limite)
        registros = self.bd.exec(sentencia).all()
        return [InteraccionIaMapper.a_dominio(registro) for registro in registros]

    def listar_recientes_por_diagrama(
        self,
        id_diagrama: UUID,
        limite: int = 5,
    ) -> list[InteraccionIa]:
        sentencia = (
            select(InteraccionIaModel)
            .where(
                InteraccionIaModel.id_diagrama == id_diagrama,
                InteraccionIaModel.fecha_eliminacion.is_(None),
            )
            .order_by(InteraccionIaModel.fecha_creacion.desc())
            .limit(limite)
        )
        registros = self.bd.exec(sentencia).all()
        # Invertir para preservar orden cronológico de lectura
        return [InteraccionIaMapper.a_dominio(registro) for registro in reversed(registros)]

    def guardar(self, interaccion: InteraccionIa) -> None:
        sentencia = select(InteraccionIaModel).where(
            InteraccionIaModel.id == interaccion.id
        )
        existente = self.bd.exec(sentencia).first()
        if existente:
            existente.tipo_interaccion = (
                interaccion.tipo_interaccion.value
                if hasattr(interaccion.tipo_interaccion, "value")
                else str(interaccion.tipo_interaccion)
            )
            existente.entrada_usuario = interaccion.entrada_usuario
            existente.respuesta_ia = interaccion.respuesta_ia
            existente.url_imagen = interaccion.url_imagen
            existente.estado = (
                interaccion.estado.value
                if hasattr(interaccion.estado, "value")
                else str(interaccion.estado)
            )
            existente.modelo_utilizado = interaccion.modelo_utilizado
            existente.detalle_ejecucion = interaccion.detalle_ejecucion
            existente.fecha_actualizacion = ahora_utc()
            self.bd.add(existente)
            return
        self.bd.add(InteraccionIaMapper.a_modelo(interaccion))

    def eliminar(self, interaccion_id: UUID) -> None:
        sentencia = select(InteraccionIaModel).where(
            InteraccionIaModel.id == interaccion_id,
            InteraccionIaModel.fecha_eliminacion.is_(None),
        )
        registro = self.bd.exec(sentencia).first()
        if registro:
            registro.eliminar_logicamente()
            self.bd.add(registro)
