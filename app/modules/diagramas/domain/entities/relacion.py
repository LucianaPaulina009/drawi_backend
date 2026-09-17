from __future__ import annotations

from typing import Any
from uuid import UUID

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
        )

    def actualizar(
        self,
        *,
        id_clase_origen: Any = NO_DEFINIDO,
        id_clase_destino: Any = NO_DEFINIDO,
        tipo_relacion: Any = NO_DEFINIDO,
        cardinalidad_origen: Any = NO_DEFINIDO,
        cardinalidad_destino: Any = NO_DEFINIDO,
        conector_origen: Any = NO_DEFINIDO,
        conector_destino: Any = NO_DEFINIDO,
    ) -> None:
        if id_clase_origen is not NO_DEFINIDO and id_clase_origen is not None:
            self.id_clase_origen = id_clase_origen
        if id_clase_destino is not NO_DEFINIDO and id_clase_destino is not None:
            self.id_clase_destino = id_clase_destino
        if tipo_relacion is not NO_DEFINIDO and tipo_relacion is not None:
            self.tipo_relacion = TipoRelacion.validar(tipo_relacion).value
        if cardinalidad_origen is not NO_DEFINIDO and cardinalidad_origen is not None:
            self.cardinalidad_origen = (
                cardinalidad_origen.value
                if isinstance(cardinalidad_origen, Cardinalidad)
                else Cardinalidad(cardinalidad_origen).value
            )
        if cardinalidad_destino is not NO_DEFINIDO and cardinalidad_destino is not None:
            self.cardinalidad_destino = (
                cardinalidad_destino.value
                if isinstance(cardinalidad_destino, Cardinalidad)
                else Cardinalidad(cardinalidad_destino).value
            )
        if conector_origen is not NO_DEFINIDO and conector_origen is not None:
            self.conector_origen = Conector.validar(conector_origen).value
        if conector_destino is not NO_DEFINIDO and conector_destino is not None:
            self.conector_destino = Conector.validar(conector_destino).value
