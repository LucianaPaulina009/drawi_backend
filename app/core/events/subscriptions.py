"""
app/core/events/subscriptions.py

Registro centralizado de todos los handlers de eventos del sistema.

Este módulo es el único lugar donde se configuran las suscripciones
entre eventos y sus handlers. Se invoca una sola vez durante el
startup de la aplicación (lifespan en main.py).

Convención
----------
Cada módulo agrega sus suscripciones en la sección correspondiente.
Los imports de los handlers se hacen dentro de la función para evitar
importaciones circulares entre módulos.
"""

from app.shared.domain.event_bus import EventBus


def configure_event_subscriptions(event_bus: EventBus) -> None:
    """
    Registra todos los handlers de eventos del sistema en el Event Bus.

    Se llama una sola vez durante el startup de la aplicación.
    Agregar suscripciones por módulo en las secciones indicadas.
    """
    # ── Módulo Diagramas ────────────────────────────────────────────────────────
    from app.modules.diagramas.domain.events.operacion_diagrama_confirmada import (
        OperacionDiagramaConfirmada,
    )
    from app.modules.diagramas.application.handlers.notificar_colaboracion_handler import (
        NotificarColaboracionHandler,
    )

    event_bus.subscribe(
        OperacionDiagramaConfirmada, NotificarColaboracionHandler.handle
    )
