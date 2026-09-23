from uuid import UUID

from sqlalchemy import or_
from sqlmodel import Session, select

from app.modules.diagramas.domain.entities.estructura_relacion_nm import EstructuraRelacionNm
from app.modules.diagramas.domain.repositories.estructura_relacion_nm_repository import EstructuraRelacionNmRepository
from app.modules.diagramas.infrastructure.persistence.mappers.estructura_relacion_nm_mapper import EstructuraRelacionNmMapper
from app.modules.diagramas.infrastructure.persistence.models.estructura_relacion_nm_model import EstructuraRelacionNmModel


class SQLModelEstructuraRelacionNmRepository(EstructuraRelacionNmRepository):
    def __init__(self, session: Session) -> None:
        self.bd = session

    def obtener_por_id(self, estructura_id: UUID) -> EstructuraRelacionNm | None:
        modelo = self.bd.exec(select(EstructuraRelacionNmModel).where(
            EstructuraRelacionNmModel.id == estructura_id,
            EstructuraRelacionNmModel.fecha_eliminacion.is_(None),
        )).first()
        return EstructuraRelacionNmMapper.a_dominio(modelo) if modelo else None

    def listar_por_diagrama(self, diagrama_id: UUID) -> list[EstructuraRelacionNm]:
        from app.modules.diagramas.infrastructure.persistence.models.clase_model import ClaseModel
        from sqlalchemy.orm import aliased

        clase_orig = aliased(ClaseModel)
        clase_dest = aliased(ClaseModel)
        clase_inter = aliased(ClaseModel)

        sentencia = (
            select(EstructuraRelacionNmModel)
            .join(clase_orig, EstructuraRelacionNmModel.id_clase_origen == clase_orig.id)
            .join(clase_dest, EstructuraRelacionNmModel.id_clase_destino == clase_dest.id)
            .join(clase_inter, EstructuraRelacionNmModel.id_clase_intermedia == clase_inter.id)
            .where(
                EstructuraRelacionNmModel.id_diagrama == diagrama_id,
                EstructuraRelacionNmModel.fecha_eliminacion.is_(None),
                clase_orig.fecha_eliminacion.is_(None),
                clase_dest.fecha_eliminacion.is_(None),
                clase_inter.fecha_eliminacion.is_(None),
            )
        )
        registros = self.bd.exec(sentencia)
        return [EstructuraRelacionNmMapper.a_dominio(item) for item in registros]

    def obtener_por_recurso(self, recurso_id: UUID) -> EstructuraRelacionNm | None:
        modelo = self.bd.exec(select(EstructuraRelacionNmModel).where(
            or_(
                EstructuraRelacionNmModel.id_clase_intermedia == recurso_id,
                EstructuraRelacionNmModel.id_relacion_origen == recurso_id,
                EstructuraRelacionNmModel.id_relacion_destino == recurso_id,
            ), EstructuraRelacionNmModel.fecha_eliminacion.is_(None),
        )).first()
        return EstructuraRelacionNmMapper.a_dominio(modelo) if modelo else None

    def guardar(self, estructura: EstructuraRelacionNm) -> None:
        self.bd.add(EstructuraRelacionNmMapper.a_modelo(estructura))

    def eliminar(self, estructura_id: UUID) -> None:
        modelo = self.bd.exec(select(EstructuraRelacionNmModel).where(
            EstructuraRelacionNmModel.id == estructura_id,
            EstructuraRelacionNmModel.fecha_eliminacion.is_(None),
        )).first()
        if modelo:
            modelo.eliminar_logicamente()
            self.bd.add(modelo)

