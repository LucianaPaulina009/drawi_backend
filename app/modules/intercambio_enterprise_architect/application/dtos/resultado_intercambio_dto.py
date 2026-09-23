from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID


@dataclass(slots=True)
class ResultadoImportacionEaDTO:
    diagrama_id: UUID
    clases_importadas: int
    atributos_importados: int
    relaciones_importadas: int
    estructuras_nm_importadas: int
    advertencias: list[str] = field(default_factory=list)
