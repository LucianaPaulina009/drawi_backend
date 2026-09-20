from __future__ import annotations

from typing import Any
from uuid import UUID

from app.modules.diagramas.domain.exceptions import (
    NombreRelacionInvalidoException,
    RelacionEstructuralInmutableException,
)
from app.modules.diagramas.domain.value_objects.cardinalidad import Cardinalidad
from app.modules.diagramas.domain.value_objects.conector import Conector
from app.modules.diagramas.domain.value_objects.tipo_relacion import TipoRelacion

NO_DEFINIDO: Any = object()


class Relacion:
    """Entidad de dominio que representa una relación UML entre dos clases en un diagrama."""

    def __init__(
        self,
        *,
        id: UUID,
        id_diagrama: UUID,
        id_clase_origen: UUID,
        id_clase_destino: UUID,
        tipo_relacion: str | TipoRelacion,
        cardinalidad_origen: str | Cardinalidad,
        cardinalidad_destino: str | Cardinalidad,
        conector_origen: str | Conector,
        conector_destino: str | Conector,
        nombre: str | None = None,
    ) -> None:
        self.id = id
        self.id_diagrama = id_diagrama
        self.id_clase_origen = id_clase_origen
        self.id_clase_destino = id_clase_destino
        self.tipo_relacion = TipoRelacion.validar(tipo_relacion).value
        self.cardinalidad_origen = (
            cardinalidad_origen.value
            if isinstance(cardinalidad_origen, Cardinalidad)
            else Cardinalidad(cardinalidad_origen).value
        )
        self.cardinalidad_destino = (
            cardinalidad_destino.value
            if isinstance(cardinalidad_destino, Cardinalidad)
            else Cardinalidad(cardinalidad_destino).value
        )
        self.conector_origen = Conector.validar(conector_origen).value
        self.conector_destino = Conector.validar(conector_destino).value
        self.nombre = self.normalizar_nombre(nombre, self.tipo_relacion)

    @classmethod
    def crear(
        cls,
        *,
        id: UUID,
        id_diagrama: UUID,
        id_clase_origen: UUID,
        id_clase_destino: UUID,
        tipo_relacion: str | TipoRelacion,
        cardinalidad_origen: str | Cardinalidad,
        cardinalidad_destino: str | Cardinalidad,
        conector_origen: str | Conector,
        conector_destino: str | Conector,
        nombre: str | None = None,
    ) -> Relacion:
        """Fábrica de creación de Relación con UUID obligatorio provisto por el cliente."""
        return cls(
            id=id,
            id_diagrama=id_diagrama,
            id_clase_origen=id_clase_origen,
            id_clase_destino=id_clase_destino,
            tipo_relacion=tipo_relacion,
            cardinalidad_origen=cardinalidad_origen,
            cardinalidad_destino=cardinalidad_destino,
            conector_origen=conector_origen,
            conector_destino=conector_destino,
            nombre=nombre,
        )

    def actualizar_nombre(self, nuevo_nombre: str | None) -> None:
        if self.tipo_relacion != TipoRelacion.ASOCIACION.value:
            raise RelacionEstructuralInmutableException(
                "Solo las relaciones de tipo asociación pueden tener nombre."
            )
        self.nombre = self.normalizar_nombre(nuevo_nombre, self.tipo_relacion)

    def actualizar(
        self,
        *,
        nombre: Any = NO_DEFINIDO,
        id_clase_origen: Any = NO_DEFINIDO,
        id_clase_destino: Any = NO_DEFINIDO,
        tipo_relacion: Any = NO_DEFINIDO,
        cardinalidad_origen: Any = NO_DEFINIDO,
        cardinalidad_destino: Any = NO_DEFINIDO,
        conector_origen: Any = NO_DEFINIDO,
        conector_destino: Any = NO_DEFINIDO,
    ) -> None:
        campos_estructurales = (
            id_clase_origen,
            id_clase_destino,
            tipo_relacion,
            cardinalidad_origen,
            cardinalidad_destino,
            conector_origen,
            conector_destino,
        )
        if any(c is not NO_DEFINIDO and c is not None for c in campos_estructurales):
            raise RelacionEstructuralInmutableException(
                "Las relaciones son inmutables estructuralmente una vez creadas."
            )
        if nombre is not NO_DEFINIDO:
            self.actualizar_nombre(nombre)

    @staticmethod
    def normalizar_nombre(nombre: str | None, tipo_relacion: str) -> str | None:
        if tipo_relacion != TipoRelacion.ASOCIACION.value:
            return None
        if nombre is None:
            return "Asociación"
        if not isinstance(nombre, str):
            raise NombreRelacionInvalidoException("El nombre de la relación debe ser un texto.")
        limpio = nombre.strip()
        if not limpio or len(limpio) > 100:
            raise NombreRelacionInvalidoException(
                "El nombre de la asociación debe tener entre 1 y 100 caracteres."
            )
        return limpio

