from __future__ import annotations

from uuid import UUID
from sqlmodel import Session, select

from app.modules.gestion_colaboradores.domain.entities.colaborador_proyecto import (
    ColaboradorProyecto,
)
from app.modules.gestion_colaboradores.domain.repositories.colaborador_proyecto_repository import (
    ColaboradorProyectoRepository,
)
from app.modules.gestion_colaboradores.infrastructure.persistence.mappers.colaborador_proyecto_mapper import (
    ColaboradorProyectoMapper,
)
from app.modules.gestion_colaboradores.infrastructure.persistence.models.colaborador_proyecto_model import (
    ColaboradorProyectoModel,
)


class SQLModelColaboradorProyectoRepository(ColaboradorProyectoRepository):
    """Implementación SQLModel del repositorio de colaboradores."""

    def __init__(self, bd: Session) -> None:
        self.bd = bd

    def obtener_por_id(self, colaborador_id: UUID) -> ColaboradorProyecto | None:
        sentencia = select(ColaboradorProyectoModel).where(
            ColaboradorProyectoModel.id == colaborador_id,
            ColaboradorProyectoModel.fecha_eliminacion.is_(None),
        )
        registro = self.bd.exec(sentencia).first()
        return ColaboradorProyectoMapper.a_dominio(registro) if registro else None

    def obtener_por_proyecto_y_usuario(
        self, id_proyecto: UUID, id_usuario: str
    ) -> ColaboradorProyecto | None:
        sentencia = select(ColaboradorProyectoModel).where(
            ColaboradorProyectoModel.id_proyecto == id_proyecto,
            ColaboradorProyectoModel.id_usuario == id_usuario,
            ColaboradorProyectoModel.fecha_eliminacion.is_(None),
        )
        registro = self.bd.exec(sentencia).first()
        return ColaboradorProyectoMapper.a_dominio(registro) if registro else None

    def listar_por_proyecto(self, id_proyecto: UUID) -> list[ColaboradorProyecto]:
        sentencia = select(ColaboradorProyectoModel).where(
            ColaboradorProyectoModel.id_proyecto == id_proyecto,
            ColaboradorProyectoModel.fecha_eliminacion.is_(None),
        )
        registros = self.bd.exec(sentencia).all()
        return [ColaboradorProyectoMapper.a_dominio(r) for r in registros]

    def guardar(self, colaborador: ColaboradorProyecto) -> None:
        registro = self.bd.get(ColaboradorProyectoModel, colaborador.id)
        if registro is None:
            # Comprobar si existía un registro eliminado previamente para reactivarlo
            sentencia_previo = select(ColaboradorProyectoModel).where(
                ColaboradorProyectoModel.id_proyecto == colaborador.id_proyecto,
                ColaboradorProyectoModel.id_usuario == colaborador.id_usuario,
            )
            registro_previo = self.bd.exec(sentencia_previo).first()
            if registro_previo is not None:
                registro_previo.rol = colaborador.rol.value
                registro_previo.estado = colaborador.estado.value
                registro_previo.restaurar()
                return

            modelo = ColaboradorProyectoMapper.a_modelo(colaborador)
            self.bd.add(modelo)
            return

        registro.rol = colaborador.rol.value
        registro.estado = colaborador.estado.value
        if registro.fecha_eliminacion is not None:
            registro.restaurar()

    def eliminar(self, colaborador_id: UUID) -> None:
        registro = self.bd.get(ColaboradorProyectoModel, colaborador_id)
        if registro is not None and registro.fecha_eliminacion is None:
            registro.eliminar_logicamente()
