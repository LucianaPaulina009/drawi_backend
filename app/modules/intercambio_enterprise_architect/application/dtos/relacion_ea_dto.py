from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class RelacionEaDTO:
    id_ea: str
    id_clase_origen_ea: str
    id_clase_destino_ea: str
    nombre: str | None = None
    tipo_relacion: str = "asociacion"
    cardinalidad_origen: str = "1"
    cardinalidad_destino: str = "0..*"
    nombre_fk: str | None = None
    clase_fk_ea: str | None = None
