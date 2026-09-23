from __future__ import annotations

import re
from dataclasses import dataclass, field
from app.modules.diagramas.domain.value_objects.tipo_dato import TipoDato
from app.modules.intercambio_enterprise_architect.application.dtos.atributo_ea_dto import (
    AtributoEaDTO,
)
from app.modules.intercambio_enterprise_architect.application.dtos.clase_ea_dto import (
    ClaseEaDTO,
)
from app.modules.intercambio_enterprise_architect.application.dtos.relacion_ea_dto import (
    RelacionEaDTO,
)


@dataclass(slots=True)
class EstructuraNmEaPlan:
    clase_origen_ea: str
    clase_destino_ea: str
    nombre_intermedia: str
    id_clase_intermedia_ea: str | None = None
    atributos_payload: list[AtributoEaDTO] = field(default_factory=list)
    posicion_x: float = 200.0
    posicion_y: float = 200.0


@dataclass(slots=True)
class PlanReconciliacionEa:
    clases_regulares: list[ClaseEaDTO]
    estructuras_nm: list[EstructuraNmEaPlan]
    relaciones_binarias: list[RelacionEaDTO]
    advertencias: list[str] = field(default_factory=list)


class ReconciliadorModeloEa:
    """Aplica las reglas deterministas del dominio de DRAWI a los elementos importados de Enterprise Architect:
    - Normalización de tipos de datos a TipoDato.
    - Exclusión de atributos ID/PK manuales de EA (cada clase nace con PK id).
    - Reconstrucción de llaves foráneas desde relaciones (no confía en atributos manuales de EA).
    - Identificación y reconstrucción de relaciones N:M y clases intermedias.
    - Ajuste de coordenadas espaciales para evitar solapamientos.
    """

    @classmethod
    def normalizar_nombre_base(cls, nombre: str) -> str:
        s = (nombre or "").strip().lower()
        for prefijo in ("tb_", "tbl_", "t_"):
            if s.startswith(prefijo):
                s = s[len(prefijo):]
                break
        return s

    @classmethod
    def limpiar_nombre_atributo(cls, nombre: str) -> str:
        s = (nombre or "").strip()
        for prefijo in ("+", "-", "#", "~"):
            if s.startswith(prefijo):
                s = s[1:].strip()
        for patron in [r"\s*\[PK\]", r"\s*\[FK\]", r"\s*\(PK\)", r"\s*\(FK\)", r"\s*PK", r"\s*FK"]:
            s = re.sub(patron, "", s, flags=re.IGNORECASE)
        return s.strip()

    @classmethod
    def coincide_nombre_fk(cls, nombre_attr: str, nombre_clase_ref: str) -> bool:
        if not nombre_attr or not nombre_clase_ref:
            return False
        attr_norm = cls.limpiar_nombre_atributo(nombre_attr).strip().lower().replace("-", "_").replace(" ", "_")
        base_ref = cls.normalizar_nombre_base(nombre_clase_ref).replace("-", "_").replace(" ", "_")

        variaciones = {
            f"{base_ref}_id",
            f"id_{base_ref}",
            f"{base_ref}id",
            f"id{base_ref}",
            f"{base_ref}",
            f"{base_ref}_fk",
            f"id_{base_ref}_fk",
            f"fk_{base_ref}",
            f"fk_{base_ref}_id",
        }
        return attr_norm in variaciones

    @classmethod
    def es_identificador_pk(cls, nombre_attr: str, nombre_clase: str = "") -> bool:
        if not nombre_attr:
            return True
        attr_limpio = cls.limpiar_nombre_atributo(nombre_attr).lower().replace("-", "_").replace(" ", "_")
        if attr_limpio in {"id", "pk", "id_pk", "pk_id", "codigo", "cod", "identificador"}:
            return True

        if nombre_clase:
            base_clase = cls.normalizar_nombre_base(nombre_clase).replace("-", "_").replace(" ", "_")
            variaciones_pk = {
                f"id_{base_clase}",
                f"{base_clase}_id",
                f"id{base_clase}",
                f"{base_clase}id",
                f"cod_{base_clase}",
                f"{base_clase}_cod",
                f"codigo_{base_clase}",
                f"{base_clase}_codigo",
                f"pk_{base_clase}",
                f"{base_clase}_pk",
            }
            if attr_limpio in variaciones_pk:
                return True
        return False

    @classmethod
    def es_cardinalidad_muchos(cls, card: str | None) -> bool:
        if not card:
            return False
        c = (card or "").strip().lower()
        return c in {"*", "0..*", "1..*", "n", "m", "0..n", "1..n", "0..m", "1..m"}

    @classmethod
    def reconciliar(
        cls,
        clases_ea: list[ClaseEaDTO],
        relaciones_ea: list[RelacionEaDTO],
    ) -> PlanReconciliacionEa:
        advertencias: list[str] = []
        mapa_clases: dict[str, ClaseEaDTO] = {c.id_ea: c for c in clases_ea}

        # 1. Identificar relaciones N:M directas o con clases intermedias evidentes
        estructuras_nm: list[EstructuraNmEaPlan] = []
        ids_relaciones_nm_procesadas: set[str] = set()
        ids_clases_intermedias_procesadas: set[str] = set()

        # 1.1 Relaciones N:M directas (muchos a muchos entre dos clases)
        for r in relaciones_ea:
            c_orig = mapa_clases.get(r.id_clase_origen_ea)
            c_dest = mapa_clases.get(r.id_clase_destino_ea)
            if not c_orig or not c_dest or c_orig.id_ea == c_dest.id_ea:
                continue

            es_nm = cls.es_cardinalidad_muchos(r.cardinalidad_origen) and cls.es_cardinalidad_muchos(r.cardinalidad_destino)
            if es_nm:
                nombre_inter = r.nombre or f"{c_orig.nombre}_{c_dest.nombre}"
                mid_x = (c_orig.posicion_x + c_dest.posicion_x) / 2.0
                mid_y = (c_orig.posicion_y + c_dest.posicion_y) / 2.0 + 100.0

                estructuras_nm.append(
                    EstructuraNmEaPlan(
                        clase_origen_ea=c_orig.id_ea,
                        clase_destino_ea=c_dest.id_ea,
                        nombre_intermedia=nombre_inter,
                        posicion_x=mid_x,
                        posicion_y=mid_y,
                    )
                )
                ids_relaciones_nm_procesadas.add(r.id_ea)

        # 1.2 Detectar clases intermedias explícitas con dos relaciones 1:N hacia clases base
        # (ej. Producto <- ProductoVenta -> Venta)
        for c_cand in clases_ea:
            if c_cand.id_ea in ids_clases_intermedias_procesadas:
                continue

            rel_hacia_cand = [
                r for r in relaciones_ea
                if (r.id_clase_destino_ea == c_cand.id_ea or r.id_clase_origen_ea == c_cand.id_ea)
                and r.id_ea not in ids_relaciones_nm_procesadas
            ]

            if len(rel_hacia_cand) == 2:
                r1, r2 = rel_hacia_cand[0], rel_hacia_cand[1]
                extremo1 = r1.id_clase_origen_ea if r1.id_clase_destino_ea == c_cand.id_ea else r1.id_clase_destino_ea
                extremo2 = r2.id_clase_origen_ea if r2.id_clase_destino_ea == c_cand.id_ea else r2.id_clase_destino_ea

                c_ext1 = mapa_clases.get(extremo1)
                c_ext2 = mapa_clases.get(extremo2)

                if c_ext1 and c_ext2 and c_ext1.id_ea != c_ext2.id_ea and c_ext1.id_ea != c_cand.id_ea and c_ext2.id_ea != c_cand.id_ea:
                    # Comprobar si los atributos de c_cand contienen FKs a ambos extremos
                    nombres_cand = [a.nombre for a in c_cand.atributos]
                    tiene_fk1 = any(cls.coincide_nombre_fk(nom, c_ext1.nombre) for nom in nombres_cand)
                    tiene_fk2 = any(cls.coincide_nombre_fk(nom, c_ext2.nombre) for nom in nombres_cand)

                    es_muchos_cand1 = cls.es_cardinalidad_muchos(r1.cardinalidad_destino if r1.id_clase_destino_ea == c_cand.id_ea else r1.cardinalidad_origen)
                    es_muchos_cand2 = cls.es_cardinalidad_muchos(r2.cardinalidad_destino if r2.id_clase_destino_ea == c_cand.id_ea else r2.cardinalidad_origen)

                    if (tiene_fk1 and tiene_fk2) or (es_muchos_cand1 and es_muchos_cand2):
                        # Atributos adicionales de datos (payload) en la tabla intermedia
                        attrs_payload = []
                        for a in c_cand.atributos:
                            if (
                                not cls.es_identificador_pk(a.nombre, c_cand.nombre)
                                and not cls.coincide_nombre_fk(a.nombre, c_ext1.nombre)
                                and not cls.coincide_nombre_fk(a.nombre, c_ext2.nombre)
                            ):
                                a_limp = cls.limpiar_nombre_atributo(a.nombre)
                                t_obj = TipoDato.normalizar_o_inferir(a.tipo_dato, nombre_atributo=a_limp)
                                a.nombre = a_limp
                                a.tipo_dato = str(t_obj.value if hasattr(t_obj, "value") else t_obj)
                                attrs_payload.append(a)
                        estructuras_nm.append(
                            EstructuraNmEaPlan(
                                clase_origen_ea=c_ext1.id_ea,
                                clase_destino_ea=c_ext2.id_ea,
                                nombre_intermedia=c_cand.nombre,
                                id_clase_intermedia_ea=c_cand.id_ea,
                                atributos_payload=attrs_payload,
                                posicion_x=c_cand.posicion_x,
                                posicion_y=c_cand.posicion_y,
                            )
                        )
                        ids_clases_intermedias_procesadas.add(c_cand.id_ea)
                        ids_relaciones_nm_procesadas.add(r1.id_ea)
                        ids_relaciones_nm_procesadas.add(r2.id_ea)

        # 2. Reconciliar Relaciones Binarias restantes (1:1 y 1:N)
        relaciones_binarias: list[RelacionEaDTO] = []
        atributos_fk_reconciliados: set[tuple[str, str]] = set()

        for r in relaciones_ea:
            if r.id_ea in ids_relaciones_nm_procesadas:
                continue

            c_orig = mapa_clases.get(r.id_clase_origen_ea)
            c_dest = mapa_clases.get(r.id_clase_destino_ea)
            if not c_orig or not c_dest:
                continue

            es_muchos_dest = cls.es_cardinalidad_muchos(r.cardinalidad_destino)
            es_muchos_orig = cls.es_cardinalidad_muchos(r.cardinalidad_origen)

            # Determinar en qué clase se materializa la FK
            if es_muchos_dest and not es_muchos_orig:
                clase_fk_obj = c_dest
                clase_ref_obj = c_orig
            elif es_muchos_orig and not es_muchos_dest:
                clase_fk_obj = c_orig
                clase_ref_obj = c_dest
            else:
                clase_fk_obj = c_dest
                clase_ref_obj = c_orig

            # Buscar si el usuario escribió un atributo manual en la clase FK que coincida
            for a in clase_fk_obj.atributos:
                if cls.coincide_nombre_fk(a.nombre, clase_ref_obj.nombre):
                    r.nombre_fk = a.nombre
                    r.clase_fk_ea = clase_fk_obj.id_ea
                    atributos_fk_reconciliados.add((clase_fk_obj.id_ea, a.nombre.lower().strip()))
                    break

            relaciones_binarias.append(r)

        # 3. Filtrar y Sanitizar Atributos de Clases Regulares
        clases_regulares: list[ClaseEaDTO] = []

        for c in clases_ea:
            if c.id_ea in ids_clases_intermedias_procesadas:
                continue

            atributos_limpios: list[AtributoEaDTO] = []
            nombres_vistos: set[str] = set()

            for a in c.atributos:
                a_limpio = cls.limpiar_nombre_atributo(a.nombre)
                a_norm = a_limpio.lower()

                # Regla 1: Omitir llaves primarias manuales (DRAWI crea automáticamente 'id' INTEGER PK)
                if a.es_pk or a_norm in {"id", "pk", "id_pk", "pk_id"} or cls.es_identificador_pk(a_limpio, c.nombre):
                    continue

                # Regla 2: Omitir llaves foráneas manuales que se materializarán mediante relaciones
                if (c.id_ea, a_norm) in atributos_fk_reconciliados:
                    continue

                # Regla 3: Omitir atributos duplicados en la misma clase
                if a_norm in nombres_vistos:
                    advertencias.append(
                        f"Atributo duplicado '{a_limpio}' en la clase '{c.nombre}' omitido."
                    )
                    continue

                nombres_vistos.add(a_norm)

                # Normalizar tipo de dato contra el catálogo del dominio
                tipo_obj = TipoDato.normalizar_o_inferir(
                    a.tipo_dato, nombre_atributo=a_limpio
                )
                tipo_normalizado = str(tipo_obj.value if hasattr(tipo_obj, "value") else tipo_obj)

                a.nombre = a_limpio
                a.tipo_dato = tipo_normalizado
                atributos_limpios.append(a)

            c.atributos = atributos_limpios
            clases_regulares.append(c)

        # 4. Asegurar que las posiciones no se solapen si vienen en (200, 200) o sin coordenadas
        cls._ajustar_posiciones_en_grilla_si_es_necesario(clases_regulares, estructuras_nm)

        return PlanReconciliacionEa(
            clases_regulares=clases_regulares,
            estructuras_nm=estructuras_nm,
            relaciones_binarias=relaciones_binarias,
            advertencias=advertencias,
        )

    @classmethod
    def _ajustar_posiciones_en_grilla_si_es_necesario(
        cls, clases: list[ClaseEaDTO], estructuras_nm: list[EstructuraNmEaPlan]
    ) -> None:
        todas_posiciones = [
            (c.posicion_x, c.posicion_y) for c in clases
        ] + [(nm.posicion_x, nm.posicion_y) for nm in estructuras_nm]

        # Si todas las posiciones son idénticas o hay solapamiento total, distribuir en grilla
        son_todas_iguales = len(set(todas_posiciones)) <= 1 and len(todas_posiciones) > 1
        if son_todas_iguales:
            columnas = 3
            ancho_col = 340.0
            alto_fila = 260.0
            idx = 0
            for c in clases:
                col = idx % columnas
                row = idx // columnas
                c.posicion_x = 100.0 + col * ancho_col
                c.posicion_y = 100.0 + row * alto_fila
                idx += 1
            for nm in estructuras_nm:
                col = idx % columnas
                row = idx // columnas
                nm.posicion_x = 100.0 + col * ancho_col
                nm.posicion_y = 100.0 + row * alto_fila
                idx += 1
