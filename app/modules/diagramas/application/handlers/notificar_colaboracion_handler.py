from __future__ import annotations

import asyncio
import logging

from app.modules.diagramas.domain.events.operacion_diagrama_confirmada import (
    OperacionDiagramaConfirmada,
)
from app.modules.diagramas.infrastructure.websocket.gestor_salas import gestor_salas

logger = logging.getLogger(__name__)


class NotificarColaboracionHandler:
    @staticmethod
    def handle(event: OperacionDiagramaConfirmada) -> None:
        """
        Despacha la difusión de la mutación confirmada a la sala WebSocket correspondiente.
        """
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(
                gestor_salas.difundir_mutacion(
                    diagrama_id=event.diagrama_id,
                    action_id=event.action_id,
                    tipo_operacion=event.tipo_operacion,
                    emisor_id=event.emisor_id,
                    efectos=event.efectos,
                )
            )
        except RuntimeError:
            try:
                asyncio.run(
                    gestor_salas.difundir_mutacion(
                        diagrama_id=event.diagrama_id,
                        action_id=event.action_id,
                        tipo_operacion=event.tipo_operacion,
                        emisor_id=event.emisor_id,
                        efectos=event.efectos,
                    )
                )
            except Exception as e:
                logger.error("Error al difundir mutación confirmada a WebSocket: %s", e)
