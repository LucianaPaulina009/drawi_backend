from __future__ import annotations

import logging
from typing import Any
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


def proyectar_clase(clase_repo: Any, atributo_repo: Any, clase_id: UUID) -> dict[str, Any] | None:
    clase = clase_repo.obtener_por_id(clase_id)
    if not clase:
        return None
    atributos = atributo_repo.listar_por_clase(clase_id)
    return {
        "id": str(clase.id),
        "id_diagrama": str(clase.id_diagrama),
        "nombre": clase.nombre,
        "posicion_x": float(clase.posicion_x),
        "posicion_y": float(clase.posicion_y),
        "ancho": float(clase.ancho),
        "atributos": [
            {
                "id": str(a.id),
                "id_clase": str(a.id_clase),
                "nombre": a.nombre,
                "tipo_dato": a.tipo_dato,
                "longitud": a.longitud,
                "precision": a.precision,
                "escala": a.escala,
                "permite_nulo": a.permite_nulo,
                "es_unico": a.es_unico,
                "valor_por_defecto": a.valor_por_defecto,
                "orden_de_posicion": a.orden_de_posicion,
                "es_llave_primaria": a.es_llave_primaria,
                "procedencia": a.procedencia.value if hasattr(a.procedencia, "value") else str(a.procedencia),
            }
            for a in atributos
        ],
    }


def proyectar_relacion(relacion_repo: Any, referencia_fk_repo: Any, relacion_id: UUID) -> dict[str, Any] | None:
    rel = relacion_repo.obtener_por_id(relacion_id)
    if not rel:
        return None
    referencias = referencia_fk_repo.listar_por_relacion(relacion_id)
    return {
        "id": str(rel.id),
        "id_diagrama": str(rel.id_diagrama),
        "id_clase_origen": str(rel.id_clase_origen),
        "id_clase_destino": str(rel.id_clase_destino),
        "tipo_relacion": rel.tipo_relacion,
        "cardinalidad_origen": rel.cardinalidad_origen,
        "cardinalidad_destino": rel.cardinalidad_destino,
        "conector_origen": rel.conector_origen,
        "conector_destino": rel.conector_destino,
        "nombre": rel.nombre,
        "referencias_fk": [
            {
                "id": str(r.id),
                "id_relacion": str(r.id_relacion),
                "id_atributo_fk": str(r.id_atributo_fk),
                "id_atributo_referenciado": str(r.id_atributo_referenciado),
                "on_delete": r.on_delete,
                "on_update": r.on_update,
            }
            for r in referencias
        ],
    }


def proyectar_estructura_nm(estructura_repo: Any, struct_id: UUID) -> dict[str, Any] | None:
    nm = estructura_repo.obtener_por_id(struct_id)
    if not nm:
        return None
    return {
        "id": str(nm.id),
        "id_diagrama": str(nm.id_diagrama),
        "id_clase_origen": str(nm.id_clase_origen),
        "id_clase_destino": str(nm.id_clase_destino),
        "id_clase_intermedia": str(nm.id_clase_intermedia),
        "id_relacion_origen": str(nm.id_relacion_origen),
        "id_relacion_destino": str(nm.id_relacion_destino),
    }


def construir_efectos(
    clases_actualizadas: list[dict[str, Any] | None] | None = None,
    clases_eliminadas: list[str | UUID] | None = None,
    relaciones_actualizadas: list[dict[str, Any] | None] | None = None,
    relaciones_eliminadas: list[str | UUID] | None = None,
    estructuras_nm_actualizadas: list[dict[str, Any] | None] | None = None,
    estructuras_nm_eliminadas: list[str | UUID] | None = None,
) -> dict[str, Any]:
    c_act = [c for c in (clases_actualizadas or []) if c is not None]
    c_elim = [str(cid) for cid in (clases_eliminadas or [])]
    r_act = [r for r in (relaciones_actualizadas or []) if r is not None]
    r_elim = [str(rid) for rid in (relaciones_eliminadas or [])]
    e_act = [e for e in (estructuras_nm_actualizadas or []) if e is not None]
    e_elim = [str(eid) for eid in (estructuras_nm_eliminadas or [])]

    # Deduplicar por id
    clases_dict = {c["id"]: c for c in c_act if c["id"] not in c_elim}
    relaciones_dict = {r["id"]: r for r in r_act if r["id"] not in r_elim}
    estructuras_dict = {s["id"]: s for s in e_act if s["id"] not in e_elim}

    return {
        "clases_actualizadas": list(clases_dict.values()),
        "clases_eliminadas": list(set(c_elim)),
        "relaciones_actualizadas": list(relaciones_dict.values()),
        "relaciones_eliminadas": list(set(r_elim)),
        "estructuras_nm_actualizadas": list(estructuras_dict.values()),
        "estructuras_nm_eliminadas": list(set(e_elim)),
    }


def emitir_evento_mutacion_confirmada(
    diagrama_id: UUID,
    action_id: str | None,
    tipo_operacion: str,
    emisor_id: str,
    efectos: dict[str, Any],
) -> None:
    """
    Publica el evento de dominio OperacionDiagramaConfirmada en el EventBus central.
    """
    try:
        from app.core.dependencies import get_event_bus
        from app.modules.diagramas.domain.events.operacion_diagrama_confirmada import (
            OperacionDiagramaConfirmada,
        )

        aid = action_id or str(uuid4())
        logger.info(
            "[Colaboración Backend] Publicando OperacionDiagramaConfirmada: diagrama=%s, actionId=%s, op=%s, emisor=%s",
            diagrama_id,
            aid,
            tipo_operacion,
            emisor_id,
        )

        event = OperacionDiagramaConfirmada(
            diagrama_id=diagrama_id,
            action_id=aid,
            tipo_operacion=tipo_operacion,
            emisor_id=emisor_id,
            efectos=efectos,
        )
        get_event_bus().publish(event)
    except Exception as e:
        logger.warning(
            "No se pudo emitir OperacionDiagramaConfirmada para diagrama %s (action_id=%s): %s",
            diagrama_id,
            action_id,
            e,
        )
