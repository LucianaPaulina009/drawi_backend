from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class AtributoEaDTO:
    id_ea: str = ""
    nombre: str = ""
    tipo_dato: str = "varchar"
    es_pk: bool = False
    es_fk: bool = False
    fk_clase_destino: str | None = None
    texto_exportacion: str | None = None
