from uuid import UUID
from sqlmodel import Session, select
from app.modules.diagramas.domain.entities.atributo import Atributo
from app.modules.diagramas.domain.repositories.atributo_repository import AtributoRepository
from app.modules.diagramas.infrastructure.persistence.mappers.atributo_mapper import AtributoMapper
from app.modules.diagramas.infrastructure.persistence.models.atributo_model import AtributoModel
from app.modules.diagramas.infrastructure.persistence.models.clase_model import ClaseModel
from app.shared.infrastructure.db.base_model import ahora_utc

class SQLModelAtributoRepository(AtributoRepository):
    def __init__(self, session: Session) -> None: self.bd=session
    def obtener_por_id(self, atributo_id: UUID) -> Atributo | None:
        m=self.bd.exec(select(AtributoModel).where(AtributoModel.id==atributo_id,AtributoModel.fecha_eliminacion.is_(None))).first(); return AtributoMapper.a_dominio(m) if m else None
    def listar_por_clase(self, clase_id: UUID) -> list[Atributo]:
        return [AtributoMapper.a_dominio(m) for m in self.bd.exec(select(AtributoModel).where(AtributoModel.id_clase==clase_id,AtributoModel.fecha_eliminacion.is_(None)).order_by(AtributoModel.orden_de_posicion))]
    def listar_por_diagrama(self, diagrama_id: UUID) -> list[Atributo]:
        s=select(AtributoModel).join(ClaseModel).where(ClaseModel.id_diagrama==diagrama_id,ClaseModel.fecha_eliminacion.is_(None),AtributoModel.fecha_eliminacion.is_(None)).order_by(AtributoModel.id_clase,AtributoModel.orden_de_posicion)
        return [AtributoMapper.a_dominio(m) for m in self.bd.exec(s)]
    def guardar(self, a: Atributo) -> None:
        m=self.bd.exec(select(AtributoModel).where(AtributoModel.id==a.id)).first()
        if not m: self.bd.add(AtributoMapper.a_modelo(a)); return
        for campo in ("tipo_dato","nombre","longitud","precision","escala","es_llave_primaria","permite_nulo","es_unico","valor_por_defecto","orden_de_posicion","procedencia"): setattr(m,campo,getattr(a,campo))
        m.fecha_actualizacion=ahora_utc(); self.bd.add(m)
    def guardar_varios(self, atributos: list[Atributo]) -> None:
        # Libera los órdenes actuales antes de escribir el nuevo orden para no
        # infringir transitoriamente el índice único de atributos activos.
        for indice, atributo in enumerate(atributos, start=1):
            modelo = self.bd.exec(
                select(AtributoModel).where(AtributoModel.id == atributo.id)
            ).first()
            if modelo:
                modelo.orden_de_posicion = -indice
                self.bd.add(modelo)
        self.bd.flush()
        for atributo in atributos:
            self.guardar(atributo)
    def eliminar(self, atributo_id: UUID) -> None:
        m=self.bd.exec(select(AtributoModel).where(AtributoModel.id==atributo_id,AtributoModel.fecha_eliminacion.is_(None))).first()
        if m: m.eliminar_logicamente(); self.bd.add(m)
    def eliminar_por_clase(self, clase_id: UUID) -> None:
        for m in self.bd.exec(select(AtributoModel).where(AtributoModel.id_clase==clase_id,AtributoModel.fecha_eliminacion.is_(None))): m.eliminar_logicamente(); self.bd.add(m)
    def eliminar_por_diagrama(self, diagrama_id: UUID) -> None:
        for a in self.listar_por_diagrama(diagrama_id): self.eliminar(a.id)
