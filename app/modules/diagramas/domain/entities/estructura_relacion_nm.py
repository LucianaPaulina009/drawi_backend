from __future__ import annotations

from uuid import UUID


class EstructuraRelacionNm:
    """Agrupa los recursos que materializan una relación muchos-a-muchos."""

    def __init__(
        self,
        *,
        id: UUID,
        id_diagrama: UUID,
        id_clase_origen: UUID,
        id_clase_destino: UUID,
        id_clase_intermedia: UUID,
        id_relacion_origen: UUID,
        id_relacion_destino: UUID,
    ) -> None:
        self.id = id
        self.id_diagrama = id_diagrama
        self.id_clase_origen = id_clase_origen
        self.id_clase_destino = id_clase_destino
        self.id_clase_intermedia = id_clase_intermedia
        self.id_relacion_origen = id_relacion_origen
        self.id_relacion_destino = id_relacion_destino

