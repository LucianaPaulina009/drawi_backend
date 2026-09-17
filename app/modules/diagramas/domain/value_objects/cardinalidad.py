from __future__ import annotations

import re
from dataclasses import dataclass

from app.modules.diagramas.domain.exceptions import CardinalidadInvalidaException
from app.shared.domain.value_object import ValueObject


@dataclass(frozen=True, slots=True)
class Cardinalidad(ValueObject):
    """Value Object inmutable que representa la cardinalidad de un extremo de relación UML.

    Formatos válidos normalizados:
    - Entero no negativo exacto: "0", "1", "2", etc.
    - Rango numérico acotado: "min..max" con 0 <= min <= max (ej. "0..1", "1..5", "2..10").
    - Rango abierto: "min..*" con min >= 0 (ej. "0..*", "1..*").
    """

    value: str

    def __post_init__(self) -> None:
        raw = self.value if isinstance(self.value, str) else ""
        normalized = raw.strip()
        self._set_attr("value", normalized)
        self.validate()

    def validate(self) -> None:
        if not self.value:
            raise CardinalidadInvalidaException("La cardinalidad no puede estar vacía.")

        # Caso 1: Entero no negativo único (ej. "1", "0", "5")
        if self.value.isdigit():
            return

        # Caso 2: Rango con ".."
        partes = self.value.split("..")
        if len(partes) != 2:
            raise CardinalidadInvalidaException(
                f"Formato de cardinalidad no válido: '{self.value}'."
            )

        izq, der = partes[0].strip(), partes[1].strip()

        if not izq.isdigit():
            raise CardinalidadInvalidaException(
                f"El límite inferior de la cardinalidad debe ser un entero no negativo: '{izq}'."
            )

        limite_inferior = int(izq)

        if der == "*":
            # Límite superior abierto válido (ej. "0..*", "1..*")
            return

        if not der.isdigit():
            raise CardinalidadInvalidaException(
                f"El límite superior de la cardinalidad debe ser un entero no negativo o '*': '{der}'."
            )

        limite_superior = int(der)

        if limite_inferior > limite_superior:
            raise CardinalidadInvalidaException(
                f"El límite inferior ({limite_inferior}) no puede ser mayor que el superior ({limite_superior})."
            )
