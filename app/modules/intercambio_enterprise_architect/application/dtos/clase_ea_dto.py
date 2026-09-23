from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.modules.intercambio_enterprise_architect.application.dtos.atributo_ea_dto import (
        AtributoEaDTO,
    )


@dataclass(slots=True)
class ClaseEaDTO:
    id_ea: str
    nombre: str
    posicion_x: float = 200.0
    posicion_y: float = 200.0
    ancho: float = 280.0
    alto: float = 120.0
    atributos: list[AtributoEaDTO] = field(default_factory=list)
