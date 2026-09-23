from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from app.modules.diagramas.application.queries.dtos import (
    ClaseDetalleDTO,
)
from app.modules.inteligencia_artificial.application.schemas.diagrama_reconocido_ia import (
    ClaseReconocidaIa,
)


@dataclass(frozen=True)
class BoundingBox:
    x_min: float
    y_min: float
    x_max: float
    y_max: float

    def intersecta(self, otro: BoundingBox, margen: float = 20.0) -> bool:
        return not (
            self.x_max + margen < otro.x_min
            or self.x_min - margen > otro.x_max
            or self.y_max + margen < otro.y_min
            or self.y_min - margen > otro.y_max
        )


class ServicioLayoutImportacion:
    """Calculador determinista de layout para posicionar clases reconocidas en una zona libre sin colisiones."""

    ANCHO_BASE_CLASE: float = 220.0
    ALTO_BASE_HEADER: float = 70.0
    ALTO_FILA_ATRIBUTO: float = 26.0
    MARGEN_HORIZONTAL_ENTRE_CLASES: float = 80.0
    MARGEN_VERTICAL_ENTRE_CLASES: float = 60.0
    ESPACIADO_ZONA_LIBRE: float = 140.0

    @classmethod
    def estimar_dimensiones_clase(cls, cantidad_atributos: int, ancho: float | None = None) -> tuple[float, float]:
        """Estima dimensiones de la tarjeta de clase según cantidad de atributos."""
        ancho_final = max(180.0, float(ancho)) if ancho is not None else cls.ANCHO_BASE_CLASE
        alto_final = cls.ALTO_BASE_HEADER + (cantidad_atributos * cls.ALTO_FILA_ATRIBUTO)
        return (ancho_final, alto_final)

    @classmethod
    def calcular_posiciones(
        cls,
        clases_reconocidas: Sequence[ClaseReconocidaIa],
        clases_existentes: Sequence[Any],
    ) -> dict[str, tuple[int, int]]:
        """
        Calcula las coordenadas finales (X, Y) para cada clase reconocida.
        
        Garantiza:
        - Cero colisión con nodos existentes.
        - Preservación razonable de la disposición relativa de la imagen.
        - Cero modificación o desplazamiento de clases existentes.
        """
        if not clases_reconocidas:
            return {}

        # 1. Calcular cajas existentes
        boxes_existentes: list[BoundingBox] = []
        for c in clases_existentes:
            ancho_val = getattr(c, "ancho", None)
            attrs = getattr(c, "atributos", []) or []
            pos_x = float(getattr(c, "posicion_x", getattr(c, "posicionX", 0.0)))
            pos_y = float(getattr(c, "posicion_y", getattr(c, "posicionY", 0.0)))
            ancho, alto = cls.estimar_dimensiones_clase(
                cantidad_atributos=len(attrs),
                ancho=float(ancho_val) if ancho_val is not None else None,
            )
            boxes_existentes.append(
                BoundingBox(
                    x_min=pos_x,
                    y_min=pos_y,
                    x_max=pos_x + ancho,
                    y_max=pos_y + alto,
                )
            )

        # 2. Asignar layout relativo preliminar a las clases reconocidas
        posiciones_relativas: dict[str, tuple[float, float, float, float]] = {}
        # ancho total y alto total del bloque importado
        min_rx = min((c.posicion_relativa_x for c in clases_reconocidas if c.posicion_relativa_x is not None), default=0.0)
        min_ry = min((c.posicion_relativa_y for c in clases_reconocidas if c.posicion_relativa_y is not None), default=0.0)
        max_rx = max((c.posicion_relativa_x for c in clases_reconocidas if c.posicion_relativa_x is not None), default=1.0)
        max_ry = max((c.posicion_relativa_y for c in clases_reconocidas if c.posicion_relativa_y is not None), default=1.0)

        rango_rx = max(0.1, max_rx - min_rx)
        rango_ry = max(0.1, max_ry - min_ry)

        # Dispersión espacial proporcional
        factor_escala_x = max(1, len(clases_reconocidas) - 1) * (cls.ANCHO_BASE_CLASE + cls.MARGEN_HORIZONTAL_ENTRE_CLASES)
        factor_escala_y = max(1, len(clases_reconocidas) - 1) * (cls.ALTO_BASE_HEADER + 4 * cls.ALTO_FILA_ATRIBUTO + cls.MARGEN_VERTICAL_ENTRE_CLASES)

        for i, c in enumerate(clases_reconocidas):
            ancho_est, alto_est = cls.estimar_dimensiones_clase(len(c.atributos))
            if c.posicion_relativa_x is not None and c.posicion_relativa_y is not None:
                norm_x = (c.posicion_relativa_x - min_rx) / rango_rx
                norm_y = (c.posicion_relativa_y - min_ry) / rango_ry
                offset_x = norm_x * factor_escala_x
                offset_y = norm_y * factor_escala_y
            else:
                # Disposición en grilla determinista de 2 columnas
                col = i % 2
                fila = i // 2
                offset_x = col * (cls.ANCHO_BASE_CLASE + cls.MARGEN_HORIZONTAL_ENTRE_CLASES)
                offset_y = fila * (cls.ALTO_BASE_HEADER + 4 * cls.ALTO_FILA_ATRIBUTO + cls.MARGEN_VERTICAL_ENTRE_CLASES)

            posiciones_relativas[c.referencia_semantica.strip()] = (offset_x, offset_y, ancho_est, alto_est)

        # 3. Determinar origen base (X, Y)
        if not boxes_existentes:
            base_x = 100.0
            base_y = 100.0
        else:
            max_x_existente = max(b.x_max for b in boxes_existentes)
            min_y_existente = min(b.y_min for b in boxes_existentes)
            base_x = max_x_existente + cls.ESPACIADO_ZONA_LIBRE
            base_y = min_y_existente

        # 4. Probar zona libre desplazando el bloque completo si colisiona
        intento = 0
        max_intentos = 50
        while intento < max_intentos:
            hay_colision = False
            for ref, (off_x, off_y, w, h) in posiciones_relativas.items():
                box_candidato = BoundingBox(
                    x_min=base_x + off_x,
                    y_min=base_y + off_y,
                    x_max=base_x + off_x + w,
                    y_max=base_y + off_y + h,
                )
                if any(box_candidato.intersecta(b_ex, margen=20.0) for b_ex in boxes_existentes):
                    hay_colision = True
                    break

            if not hay_colision:
                break

            # Desplazamiento en pasos deterministas hacia abajo / derecha
            base_y += 120.0
            if intento % 5 == 0:
                base_x += 100.0
            intento += 1

        # 5. Retornar posiciones enteras redondeadas
        resultado: dict[str, tuple[int, int]] = {}
        for c in clases_reconocidas:
            ref = c.referencia_semantica.strip()
            if ref in posiciones_relativas:
                off_x, off_y, _, _ = posiciones_relativas[ref]
                pos_final = (int(round(base_x + off_x)), int(round(base_y + off_y)))
                resultado[c.referencia_semantica] = pos_final

        return resultado

    @classmethod
    def calcular_posicion_libre_para_clase(
        cls,
        clases_existentes: Sequence[Any],
        posicion_preferida: tuple[float, float] | None = None,
        ancho: float | None = None,
        cantidad_atributos: int = 0,
        margen: float = 10.0,
    ) -> tuple[float, float]:
        """
        Calcula una posición (X, Y) limpia en el lienzo asegurando que NO se
        superponga sobre ninguna clase existente, atributo o relación visible.

        Si se provee una posición preferida que no colisiona, se respeta.
        Si colisiona o no se provee, encuentra de manera ordenada el espacio libre más cercano.
        """
        boxes_existentes: list[BoundingBox] = []
        for c in clases_existentes:
            ancho_val = getattr(c, "ancho", None)
            attrs = getattr(c, "atributos", []) or []
            pos_x = float(getattr(c, "posicion_x", getattr(c, "posicionX", 0.0)))
            pos_y = float(getattr(c, "posicion_y", getattr(c, "posicionY", 0.0)))
            ancho_c, alto_c = cls.estimar_dimensiones_clase(
                cantidad_atributos=len(attrs),
                ancho=float(ancho_val) if ancho_val is not None else None,
            )
            boxes_existentes.append(
                BoundingBox(
                    x_min=pos_x,
                    y_min=pos_y,
                    x_max=pos_x + ancho_c,
                    y_max=pos_y + alto_c,
                )
            )

        ancho_nuevo, alto_nuevo = cls.estimar_dimensiones_clase(
            cantidad_atributos=cantidad_atributos,
            ancho=ancho,
        )

        # Si el lienzo está vacío
        if not boxes_existentes:
            if posicion_preferida is not None:
                return (
                    max(80.0, float(posicion_preferida[0])),
                    max(80.0, float(posicion_preferida[1])),
                )
            return (100.0, 100.0)

        # Si se especificó una posición preferida, verificar si está libre (sin solapamiento real)
        if posicion_preferida is not None:
            px, py = float(posicion_preferida[0]), float(posicion_preferida[1])
            box_pref = BoundingBox(
                x_min=px,
                y_min=py,
                x_max=px + ancho_nuevo,
                y_max=py + alto_nuevo,
            )
            if not any(box_pref.intersecta(b_ex, margen=margen) for b_ex in boxes_existentes):
                return (px, py)

        # Si colisiona o no hay posición preferida, buscar espacio libre ordenado
        min_x = min(b.x_min for b in boxes_existentes)
        min_y = min(b.y_min for b in boxes_existentes)
        max_x = max(b.x_max for b in boxes_existentes)
        max_y = max(b.y_max for b in boxes_existentes)

        base_search_x = posicion_preferida[0] if posicion_preferida is not None else max_x + cls.MARGEN_HORIZONTAL_ENTRE_CLASES
        base_search_y = posicion_preferida[1] if posicion_preferida is not None else min_y

        paso_x = max(ancho_nuevo + cls.MARGEN_HORIZONTAL_ENTRE_CLASES, 320.0)
        paso_y = max(alto_nuevo + cls.MARGEN_VERTICAL_ENTRE_CLASES, 220.0)

        candidatos: list[tuple[float, float]] = []
        candidatos.append((max_x + cls.MARGEN_HORIZONTAL_ENTRE_CLASES, min_y))
        candidatos.append((min_x, max_y + cls.MARGEN_VERTICAL_ENTRE_CLASES))

        for r in range(0, 15):
            for c in range(0, 15):
                cand_x = 100.0 + c * paso_x
                cand_y = 100.0 + r * paso_y
                if cand_x >= 50.0 and cand_y >= 50.0:
                    candidatos.append((cand_x, cand_y))

        target_x, target_y = base_search_x, base_search_y
        candidatos.sort(key=lambda pt: (pt[0] - target_x) ** 2 + (pt[1] - target_y) ** 2)

        for cx, cy in candidatos:
            box_cand = BoundingBox(
                x_min=cx,
                y_min=cy,
                x_max=cx + ancho_nuevo,
                y_max=cy + alto_nuevo,
            )
            if not any(box_cand.intersecta(b_ex, margen=20.0) for b_ex in boxes_existentes):
                return (cx, cy)

        return (max_x + cls.MARGEN_HORIZONTAL_ENTRE_CLASES, min_y)
