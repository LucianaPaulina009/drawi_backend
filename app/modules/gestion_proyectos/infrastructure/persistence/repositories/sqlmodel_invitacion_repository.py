from __future__ import annotations

from uuid import UUID
from sqlmodel import Session, select

from app.modules.gestion_proyectos.domain.entities.invitacion import Invitacion
from app.modules.gestion_proyectos.domain.repositories.invitacion_repository import (
    InvitacionRepository,
)
from app.modules.gestion_proyectos.infrastructure.persistence.mappers.invitacion_mapper import (
    InvitacionMapper,
)
from app.modules.gestion_proyectos.infrastructure.persistence.models.invitacion_model import (
    InvitacionModel,
)


class SQLModelInvitacionRepository(InvitacionRepository):
    """Implementación SQLModel del repositorio de invitaciones."""

    def __init__(self, bd: Session) -> None:
        self.bd = bd

    def obtener_por_id(self, invitacion_id: UUID) -> Invitacion | None:
        sentencia = select(InvitacionModel).where(
            InvitacionModel.id == invitacion_id,
            InvitacionModel.fecha_eliminacion.is_(None),
        )
        registro = self.bd.exec(sentencia).first()
        return InvitacionMapper.a_dominio(registro) if registro else None

    def obtener_por_proyecto(self, id_proyecto: UUID) -> Invitacion | None:
        sentencia = select(InvitacionModel).where(
            InvitacionModel.id_proyecto == id_proyecto,
            InvitacionModel.fecha_eliminacion.is_(None),
        )
        registro = self.bd.exec(sentencia).first()
        return InvitacionMapper.a_dominio(registro) if registro else None

    def obtener_por_codigo(self, codigo_acceso: str) -> Invitacion | None:
        sentencia = select(InvitacionModel).where(
            InvitacionModel.codigo_acceso == codigo_acceso,
            InvitacionModel.fecha_eliminacion.is_(None),
        )
        registro = self.bd.exec(sentencia).first()
        return InvitacionMapper.a_dominio(registro) if registro else None

    def guardar(self, invitacion: Invitacion) -> None:
        registro = self.bd.get(InvitacionModel, invitacion.id)
        if registro is None:
            # Comprobar si ya había una invitación para este proyecto para reutilizarla
            sentencia_existente = select(InvitacionModel).where(
                InvitacionModel.id_proyecto == invitacion.id_proyecto,
            )
            existente = self.bd.exec(sentencia_existente).first()
            if existente is not None:
                existente.codigo_acceso = invitacion.codigo_acceso
                existente.fecha_expiracion = invitacion.fecha_expiracion
                if existente.fecha_eliminacion is not None:
                    existente.restaurar()
                return

            modelo = InvitacionMapper.a_modelo(invitacion)
            self.bd.add(modelo)
            return

        registro.codigo_acceso = invitacion.codigo_acceso
        registro.fecha_expiracion = invitacion.fecha_expiracion
        if registro.fecha_eliminacion is not None:
            registro.restaurar()

    def eliminar(self, invitacion_id: UUID) -> None:
        registro = self.bd.get(InvitacionModel, invitacion_id)
        if registro is not None and registro.fecha_eliminacion is None:
            registro.eliminar_logicamente()
