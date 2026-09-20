from __future__ import annotations

import hashlib
import json
from uuid import UUID, uuid4

from app.modules.diagramas.domain.entities.operacion_diagrama import OperacionDiagrama
from app.modules.diagramas.domain.exceptions import ConflictoIdempotenciaException
from app.modules.diagramas.domain.repositories.operacion_diagrama_repository import OperacionDiagramaRepository


def huella_payload(payload: object) -> str:
    serializado = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(serializado.encode()).hexdigest()


class IdempotenciaDiagramaService:
    def __init__(self, repository: OperacionDiagramaRepository) -> None:
        self.repository = repository

    def confirmar_o_recuperar(
        self, *, action_id: UUID, usuario_id: str, diagrama_id: UUID, payload: object
    ) -> dict | None:
        existente = self.repository.obtener_por_action_id(action_id)
        if existente is None:
            return None
        if existente.usuario_id != usuario_id or existente.id_diagrama != diagrama_id or existente.huella_payload != huella_payload(payload):
            raise ConflictoIdempotenciaException()
        return existente.respuesta

    def registrar_confirmacion(
        self, *, action_id: UUID, usuario_id: str, diagrama_id: UUID, payload: object, respuesta: dict
    ) -> None:
        self.repository.guardar(OperacionDiagrama(
            id=uuid4(), action_id=action_id, usuario_id=usuario_id, id_diagrama=diagrama_id,
            huella_payload=huella_payload(payload), estado="confirmada", respuesta=respuesta,
        ))
