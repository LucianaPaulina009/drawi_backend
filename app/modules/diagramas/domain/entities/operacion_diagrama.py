from __future__ import annotations

from uuid import UUID


class OperacionDiagrama:
    """Confirmación persistente de una mutación idempotente del diagramador."""

    def __init__(
        self,
        *,
        id: UUID,
        action_id: UUID,
        usuario_id: str,
        id_diagrama: UUID,
        huella_payload: str,
        estado: str,
        respuesta: dict | None,
    ) -> None:
        self.id = id
        self.action_id = action_id
        self.usuario_id = usuario_id
        self.id_diagrama = id_diagrama
        self.huella_payload = huella_payload
        self.estado = estado
        self.respuesta = respuesta

