from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, select

from app.modules.generacion_backend.domain.entities.generacion_backend import (
    GeneracionBackend,
)
from app.modules.generacion_backend.domain.repositories.generacion_backend_repository import (
    GeneracionBackendRepository,
)
from app.modules.generacion_backend.infrastructure.persistence.mappers.generacion_backend_mapper import (
    GeneracionBackendMapper,
)
from app.modules.generacion_backend.infrastructure.persistence.models.generacion_backend_model import (
    GeneracionBackendModel,
)


class SQLModelGeneracionBackendRepository(GeneracionBackendRepository):
    """Implementación SQLModel del repositorio de generaciones de backend."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def guardar(self, generacion: GeneracionBackend) -> GeneracionBackend:
        existente = self.session.get(GeneracionBackendModel, generacion.id)
        if existente is not None:
            existente.estado = generacion.estado.value
            existente.version_plantilla = generacion.version_plantilla
            existente.fecha_generacion = generacion.fecha_generacion
            existente.detalle_error = generacion.detalle_error
            self.session.add(existente)
            self.session.flush()
            return GeneracionBackendMapper.a_dominio(existente)
        else:
            modelo = GeneracionBackendMapper.a_modelo(generacion)
            self.session.add(modelo)
            self.session.flush()
            return GeneracionBackendMapper.a_dominio(modelo)

    def obtener_por_id(self, generacion_id: UUID) -> GeneracionBackend | None:
        modelo = self.session.get(GeneracionBackendModel, generacion_id)
        return GeneracionBackendMapper.a_dominio(modelo) if modelo is not None else None

    def listar_por_diagrama(
        self, id_diagrama: UUID, limite: int = 50
    ) -> list[GeneracionBackend]:
        sentencia = (
            select(GeneracionBackendModel)
            .where(GeneracionBackendModel.id_diagrama == id_diagrama)
            .order_by(GeneracionBackendModel.fecha_generacion.desc())
            .limit(limite)
        )
        resultados = self.session.exec(sentencia).all()
        return [GeneracionBackendMapper.a_dominio(m) for m in resultados]
