from __future__ import annotations

from typing import Any
from uuid import UUID

from app.modules.diagramas.domain.value_objects.accion_referencial import AccionReferencial

NO_DEFINIDO: Any = object()


class ReferenciaFK:
    """Entidad de dominio que representa la configuración de una clave foránea en una relación."""

    def __init__(
        self,
        *,
        id: UUID,
        id_relacion: UUID,
        id_atributo_fk: UUID,
        id_atributo_referenciado: UUID,
        on_delete: str | AccionReferencial = AccionReferencial.NO_ACTION,
        on_update: str | AccionReferencial = AccionReferencial.NO_ACTION,
    ) -> None:
        self.id = id
        self.id_relacion = id_relacion
        self.id_atributo_fk = id_atributo_fk
        self.id_atributo_referenciado = id_atributo_referenciado
        self.on_delete = AccionReferencial.validar(on_delete).value
        self.on_update = AccionReferencial.validar(on_update).value

    @classmethod
    def crear(
        cls,
        *,
        id: UUID,
        id_relacion: UUID,
        id_atributo_fk: UUID,
        id_atributo_referenciado: UUID,
        on_delete: str | AccionReferencial = AccionReferencial.NO_ACTION,
        on_update: str | AccionReferencial = AccionReferencial.NO_ACTION,
    ) -> ReferenciaFK:
        """Fábrica de creación de Referencia FK con UUID obligatorio provisto por el cliente."""
        return cls(
            id=id,
            id_relacion=id_relacion,
            id_atributo_fk=id_atributo_fk,
            id_atributo_referenciado=id_atributo_referenciado,
            on_delete=on_delete,
            on_update=on_update,
        )

    def actualizar(
        self,
        *,
        id_atributo_fk: Any = NO_DEFINIDO,
        id_atributo_referenciado: Any = NO_DEFINIDO,
        on_delete: Any = NO_DEFINIDO,
        on_update: Any = NO_DEFINIDO,
    ) -> None:
        if id_atributo_fk is not NO_DEFINIDO and id_atributo_fk is not None:
            self.id_atributo_fk = id_atributo_fk
        if id_atributo_referenciado is not NO_DEFINIDO and id_atributo_referenciado is not None:
            self.id_atributo_referenciado = id_atributo_referenciado
        if on_delete is not NO_DEFINIDO and on_delete is not None:
            self.on_delete = AccionReferencial.validar(on_delete).value
        if on_update is not NO_DEFINIDO and on_update is not None:
            self.on_update = AccionReferencial.validar(on_update).value
