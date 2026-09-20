from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.shared.domain.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class OperacionDiagramaConfirmada(DomainEvent):
    """
    Evento de dominio emitido tras la persistencia exitosa de una mutación sobre un diagrama.
    Permite notificar a los suscriptores (ej. gestor de colaboración en tiempo real).
    """

    diagrama_id: UUID
    action_id: str
    tipo_operacion: str
    emisor_id: str
    efectos: dict[str, Any]
