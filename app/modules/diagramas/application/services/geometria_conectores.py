from __future__ import annotations

from typing import Any

from app.modules.diagramas.domain.value_objects.conector import Conector


def generar_candidatos_sub_handles(lado: str, delta_x: float, delta_y: float) -> list[str]:
    """Genera candidatos de conectores para un lado dado ordenados según el ángulo relativo."""
    lado_norm = lado.lower().split("-")[0]
    if lado_norm == "right":
        if delta_y < -20:
            return ["right-top", "right-center", "right-bottom", "right"]
        if delta_y > 20:
            return ["right-bottom", "right-center", "right-top", "right"]
        return ["right-center", "right-top", "right-bottom", "right"]
    elif lado_norm == "left":
        if delta_y < -20:
            return ["left-top", "left-center", "left-bottom", "left"]
        if delta_y > 20:
            return ["left-bottom", "left-center", "left-top", "left"]
        return ["left-center", "left-top", "left-bottom", "left"]
    elif lado_norm == "top":
        if delta_x < -20:
            return ["top-left", "top-center", "top-right", "top"]
        if delta_x > 20:
            return ["top-right", "top-center", "top-left", "top"]
        return ["top-center", "top-right", "top-left", "top"]
    elif lado_norm == "bottom":
        if delta_x < -20:
            return ["bottom-left", "bottom-center", "bottom-right", "bottom"]
        if delta_x > 20:
            return ["bottom-right", "bottom-center", "bottom-left", "bottom"]
        return ["bottom-center", "bottom-right", "bottom-left", "bottom"]
    return ["right-center", "right-top", "right-bottom", "right"]


def obtener_orden_lados_alternativos(lado_principal: str, delta_x: float, delta_y: float) -> list[str]:
    """Determina la prioridad de lados para buscar conectores libres si el principal está saturado."""
    lado_norm = lado_principal.lower().split("-")[0]
    if lado_norm in ("right", "left"):
        vertical = "top" if delta_y < 0 else "bottom"
        vertical_opuesta = "bottom" if delta_y < 0 else "top"
        opuesto = "left" if lado_norm == "right" else "right"
        return [lado_norm, vertical, vertical_opuesta, opuesto]
    else:
        horizontal = "left" if delta_x < 0 else "right"
        horizontal_opuesta = "right" if delta_x < 0 else "left"
        opuesto = "bottom" if lado_norm == "top" else "top"
        return [lado_norm, horizontal, horizontal_opuesta, opuesto]


def seleccionar_conector_libre(
    clase_id: Any,
    lado_preferido: str,
    delta_x: float,
    delta_y: float,
    ocupados: set[tuple[Any, str]],
) -> str:
    """Encuentra el conector disponible con mejor alineación visual para la clase dada."""
    lados = obtener_orden_lados_alternativos(lado_preferido, delta_x, delta_y)

    for lado in lados:
        candidatos = generar_candidatos_sub_handles(lado, delta_x, delta_y)
        for cand in candidatos:
            try:
                handle_canonico = Conector.a_handle_canonico(cand)
            except Exception:
                handle_canonico = cand
            if (clase_id, handle_canonico) not in ocupados:
                ocupados.add((clase_id, handle_canonico))
                return cand

    # Fallback si todos los puertos estuvieran ocupados
    candidatos_default = generar_candidatos_sub_handles(lado_preferido, delta_x, delta_y)
    return candidatos_default[0]


def calcular_mejores_conectores(
    clase_origen: Any,
    clase_destino: Any,
    relaciones_existentes: list[Any] | None = None,
    conector_origen_preferido: str | None = None,
    conector_destino_preferido: str | None = None,
) -> tuple[str, str]:
    """
    Calcula los mejores puntos de conexión entre dos clases basándose en su
    geometría relativa en el lienzo y los conectores ya ocupados.

    Garantiza que:
    - Si A está a la izquierda y B a la derecha -> A conecta en 'right' y B en 'left'.
    - Si A está a la derecha y B a la izquierda -> A conecta en 'left' y B en 'right'.
    - Si A está arriba y B abajo -> A conecta en 'bottom' y B en 'top'.
    - Si A está abajo y B arriba -> A conecta en 'top' y B en 'bottom'.
    - Si hay puertos ocupados, selecciona el sub-handle libre más cercano.
    """
    x_a = float(getattr(clase_origen, "posicion_x", 0.0) or 0.0)
    y_a = float(getattr(clase_origen, "posicion_y", 0.0) or 0.0)
    w_a = float(getattr(clase_origen, "ancho", 280.0) or 280.0)
    h_a = 120.0

    x_b = float(getattr(clase_destino, "posicion_x", 0.0) or 0.0)
    y_b = float(getattr(clase_destino, "posicion_y", 0.0) or 0.0)
    w_b = float(getattr(clase_destino, "ancho", 280.0) or 280.0)
    h_b = 120.0

    cx_a = x_a + w_a / 2.0
    cy_a = y_a + h_a / 2.0
    cx_b = x_b + w_b / 2.0
    cy_b = y_b + h_b / 2.0

    delta_x = cx_b - cx_a
    delta_y = cy_b - cy_a

    # Construir conjunto de ocupaciones existentes
    ocupados: set[tuple[Any, str]] = set()
    if relaciones_existentes:
        for rel in relaciones_existentes:
            if hasattr(rel, "id_clase_origen") and hasattr(rel, "conector_origen") and rel.conector_origen:
                try:
                    ocupados.add((rel.id_clase_origen, Conector.a_handle_canonico(rel.conector_origen)))
                except Exception:
                    pass
            if hasattr(rel, "id_clase_destino") and hasattr(rel, "conector_destino") and rel.conector_destino:
                try:
                    ocupados.add((rel.id_clase_destino, Conector.a_handle_canonico(rel.conector_destino)))
                except Exception:
                    pass

    # Caso recursivo: misma clase
    if str(getattr(clase_origen, "id", "a")) == str(getattr(clase_destino, "id", "b")):
        con_orig = seleccionar_conector_libre(clase_origen.id, "right", 100.0, 100.0, ocupados)
        con_dest = seleccionar_conector_libre(clase_destino.id, "top", 100.0, -100.0, ocupados)
        return con_orig, con_dest

    # Determinar lados geométricos principales
    if abs(delta_x) >= abs(delta_y):
        lado_origen = "right" if delta_x >= 0 else "left"
        lado_destino = "left" if delta_x >= 0 else "right"
    else:
        lado_origen = "bottom" if delta_y >= 0 else "top"
        lado_destino = "top" if delta_y >= 0 else "bottom"

    # Si se proporcionaron conectores preferidos explícitos que son válidos
    conectores_validos = {
        "top", "right", "bottom", "left",
        "top-left", "top-center", "top-right",
        "right-top", "right-center", "right-bottom",
        "bottom-left", "bottom-center", "bottom-right",
        "left-top", "left-center", "left-bottom",
    }
    if conector_origen_preferido and conector_origen_preferido in conectores_validos:
        lado_origen = conector_origen_preferido

    if conector_destino_preferido and conector_destino_preferido in conectores_validos:
        lado_destino = conector_destino_preferido

    id_origen = getattr(clase_origen, "id", "origen")
    id_destino = getattr(clase_destino, "id", "destino")

    con_orig = seleccionar_conector_libre(id_origen, lado_origen, delta_x, delta_y, ocupados)
    con_dest = seleccionar_conector_libre(id_destino, lado_destino, -delta_x, -delta_y, ocupados)

    return con_orig, con_dest
