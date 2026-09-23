from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Sequence
from uuid import UUID

from app.modules.diagramas.application.queries.dtos import (
    DiagramaDetalleDTO,
)
from app.modules.inteligencia_artificial.application.schemas.diagrama_reconocido_ia import (
    AtributoReconocidoIa,
    ClaseReconocidaIa,
    DiagramaReconocidoIa,
    RelacionReconocidaIa,
)
from app.modules.inteligencia_artificial.application.services.validador_respuesta_ia import (
    AccionCrearAtributoSchema,
    AccionCrearClaseSchema,
    AccionCrearEstructuraNmSchema,
    AccionCrearRelacionSchema,
    AccionIaUnion,
    PosicionSchema,
)


@dataclass
class PlanImportacionImagen:
    """Resultado de la planificación de importación de imagen."""

    acciones: list[AccionIaUnion] = field(default_factory=list)
    clases_existentes_mapeo: dict[str, UUID] = field(default_factory=dict)
    clases_creadas_referencias: list[str] = field(default_factory=list)
    clases_reutilizadas: list[str] = field(default_factory=list)
    atributos_omitidos: list[str] = field(default_factory=list)
    advertencias: list[str] = field(default_factory=list)


class PlanificadorImportacionImagen:
    """
    Planifica la creación y reconciliación de elementos reconocidos desde una imagen UML.
    
    Reglas fundamentales:
    1. Reconciliación exacta: si una clase ya existe (match case-insensitive/trim), se reutiliza
       y se prohíbe agregar silenciosamente nuevos atributos a dicha clase existente.
    2. Orden de dependencias: Clase -> Atributo -> Relación / Estructura N:M.
    3. Cero duplicación de FKs ni estructuras intermedias manuales: delega en los casos de uso existentes.
    """

    TIPOS_VALIDOS = {
        "varchar",
        "integer",
        "bigint",
        "decimal",
        "boolean",
        "date",
        "timestamp",
        "text",
    }

    TIPOS_RELACION_VALIDOS = {
        "asociacion",
        "asociacion_dirigida",
        "agregacion",
        "composicion",
        "herencia",
        "realizacion",
        "dependencia",
    }

    @classmethod
    def normalizar_tipo_dato(cls, tipo: str | None) -> str:
        if not tipo:
            return "varchar"
        t = tipo.strip().lower()
        if t in cls.TIPOS_VALIDOS:
            return t
        if "int" in t:
            return "bigint" if "big" in t else "integer"
        if "bool" in t:
            return "boolean"
        if "dec" in t or "float" in t or "double" in t or "num" in t:
            return "decimal"
        if "date" in t or "time" in t:
            return "timestamp" if "time" in t else "date"
        if "text" in t:
            return "text"
        return "varchar"

    @classmethod
    def normalizar_tipo_relacion(cls, tipo: str | None) -> str:
        if not tipo:
            return "asociacion"
        t = tipo.strip().lower()
        if t in cls.TIPOS_RELACION_VALIDOS:
            return t
        if "dirigida" in t:
            return "asociacion_dirigida"
        if "agreg" in t:
            return "agregacion"
        if "comp" in t:
            return "composicion"
        if "heren" in t or "gen" in t:
            return "herencia"
        if "real" in t:
            return "realizacion"
        if "dep" in t:
            return "dependencia"
        return "asociacion"

    @classmethod
    def normalizar_cardinalidad(cls, card: str | None, default: str = "1") -> str:
        if not card:
            return default
        c = card.strip()
        if c in {"1", "0..1", "1..*", "0..*"}:
            return c
        if c in {"*", "N", "M", "n", "m"}:
            return "0..*"
        if c in {"0..N", "0..n", "0..M", "0..m"}:
            return "0..*"
        if c in {"1..N", "1..n", "1..M", "1..m"}:
            return "1..*"
        return default

    @classmethod
    def es_cardinalidad_muchos(cls, card: str | None) -> bool:
        if not card:
            return False
        c = card.strip().lower()
        return c in {"*", "0..*", "1..*", "n", "m", "0..n", "0..m", "1..n", "1..m"}

    @classmethod
    def limpiar_nombre_atributo(cls, nombre: str) -> str:
        s = nombre.strip()
        # Quitar visibilidad UML (+, -, #, ~) al inicio
        s = re.sub(r"^[\+\-\#\~]\s*", "", s)
        # Quitar estereotipos <<PK>>, <<FK>>, (PK), (FK), [PK], [FK]
        s = re.sub(r"<<.*?>>|\(.*?\)|\[.*?\]", "", s)
        # Quitar sufijos de tipo como ": int", ": varchar(50)", etc.
        if ":" in s:
            s = s.split(":", 1)[0]
        # Quitar sufijo "PK" o "FK" aislado al final
        s = re.sub(r"\s+(?:pk|fk)\b", "", s, flags=re.IGNORECASE)
        s = s.strip()
        return s if s else nombre.strip()

    @classmethod
    def normalizar_nombre_base(cls, nombre: str) -> str:
        s = nombre.strip().lower()
        for prefijo in ("tb_", "tbl_", "t_"):
            if s.startswith(prefijo):
                s = s[len(prefijo):]
                break
        return s

    @classmethod
    def coincide_nombre_fk(
        cls, nombre_attr: str, nombre_clase_ref: str, es_recursiva: bool = False
    ) -> bool:
        attr_norm = nombre_attr.strip().lower()
        base_ref = cls.normalizar_nombre_base(nombre_clase_ref)

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
        if attr_norm in variaciones:
            return True

        if es_recursiva:
            variaciones_recursivas = {
                "supervisor_id",
                "id_supervisor",
                "supervisor",
                "jefe_id",
                "id_jefe",
                "jefe",
                "padre_id",
                "id_padre",
                "padre",
                "parent_id",
                "id_parent",
                "parent",
                "superior_id",
                "id_superior",
                "superior",
                "manager_id",
                "id_manager",
                "manager",
                "lider_id",
                "id_lider",
                "lider",
                "responsable_id",
                "id_responsable",
                f"{base_ref}_padre_id",
                f"id_{base_ref}_padre",
                f"{base_ref}_supervisor_id",
                f"id_{base_ref}_supervisor",
            }
            if attr_norm in variaciones_recursivas:
                return True

        return False

    @classmethod
    def es_identificador_pk(cls, nombre_attr: str, nombre_clase: str) -> bool:
        """
        Determina si un nombre de atributo representa la clave primaria propia de una clase
        (ej. id, pk, id_producto, producto_id, cod_producto, etc.).
        """
        if not nombre_attr:
            return True
        attr_limpio = cls.limpiar_nombre_atributo(nombre_attr).lower().replace("-", "_").replace(" ", "_")
        base_clase = cls.normalizar_nombre_base(nombre_clase).replace("-", "_").replace(" ", "_")

        # Identificadores genéricos de PK
        if attr_limpio in {"id", "pk", "id_pk", "pk_id", "codigo", "cod", "identificador"}:
            return True

        # Identificadores específicos con el nombre de la clase
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
        return attr_limpio in variaciones_pk

    @classmethod
    def determinar_lado_fk_relacion(
        cls,
        rel: RelacionReconocidaIa,
        clases_por_ref: dict[str, ClaseReconocidaIa],
    ) -> tuple[str | None, str | None, bool]:
        """
        Determina (clase_fk_ref, clase_ref_ref, requiere_materializacion)
        para una relación según las reglas del dominio de DRAWI.
        """
        es_nm = rel.es_nm or (
            cls.es_cardinalidad_muchos(rel.cardinalidad_origen)
            and cls.es_cardinalidad_muchos(rel.cardinalidad_destino)
        )
        if es_nm:
            return None, None, False

        tipo_rel = cls.normalizar_tipo_relacion(rel.tipo)
        orig_ref = rel.origen_ref.strip()
        dest_ref = rel.destino_ref.strip()

        # Herencia / Realización / Dependencia -> FK en clase origen apuntando a clase destino
        if tipo_rel in {"herencia", "realizacion", "dependencia"}:
            return orig_ref, dest_ref, True

        if tipo_rel not in cls.TIPOS_RELACION_VALIDOS:
            return None, None, False

        # Relación recursiva
        if rel.es_recursiva or orig_ref.lower() == dest_ref.lower():
            return orig_ref, dest_ref, True

        origen_muchos = cls.es_cardinalidad_muchos(rel.cardinalidad_origen)
        destino_muchos = cls.es_cardinalidad_muchos(rel.cardinalidad_destino)

        if origen_muchos != destino_muchos:
            clase_fk = orig_ref if origen_muchos else dest_ref
            clase_ref = dest_ref if origen_muchos else orig_ref
            return clase_fk, clase_ref, True

        # 1:1
        # Comprobar si origen_ref tiene explícitamente un atributo FK o nombre que apunta a destino_ref
        clase_orig_obj = clases_por_ref.get(orig_ref.lower())
        clase_dest_obj = clases_por_ref.get(dest_ref.lower())
        nombre_dest = clase_dest_obj.nombre if clase_dest_obj else dest_ref

        if clase_orig_obj:
            for a in clase_orig_obj.atributos:
                if a.es_pk or a.nombre.lower() == "id":
                    continue
                if a.fk_destino_ref and a.fk_destino_ref.strip().lower() in (
                    dest_ref.lower(),
                    nombre_dest.lower(),
                ):
                    return orig_ref, dest_ref, True
                if a.es_fk and cls.coincide_nombre_fk(a.nombre, nombre_dest):
                    return orig_ref, dest_ref, True
                if cls.coincide_nombre_fk(a.nombre, nombre_dest):
                    return orig_ref, dest_ref, True

        # Por defecto en 1:1, la FK se coloca en el destino apuntando al origen
        return dest_ref, orig_ref, True

    @classmethod
    def evaluar_evidencia_referencia_clase(
        cls,
        clase_c: ClaseReconocidaIa,
        clase_ref: ClaseReconocidaIa,
        relaciones: Sequence[RelacionReconocidaIa],
    ) -> tuple[int, AtributoReconocidoIa | None]:
        """
        Evalúa el nivel de evidencia estructural de que clase_c referencia a clase_ref.
        Retorna (score, atributo_candidato_fk).
        """
        score = 0
        candidato_attr: AtributoReconocidoIa | None = None
        base_ref = cls.normalizar_nombre_base(clase_ref.nombre)

        # 1. Analizar atributos de clase_c
        for a in clase_c.atributos:
            if a.es_pk or a.nombre.strip().lower() == "id":
                continue

            # Coincidencia explícita fk_destino_ref
            if a.fk_destino_ref and a.fk_destino_ref.strip().lower() in (
                clase_ref.referencia_semantica.lower(),
                clase_ref.nombre.strip().lower(),
            ):
                score = max(score, 5)
                candidato_attr = a
                break

            # Marcado es_fk=True y coincide nombre
            if a.es_fk and cls.coincide_nombre_fk(a.nombre, clase_ref.nombre):
                score = max(score, 5)
                candidato_attr = a
                break

            # Coincide nombre de FK (ej: producto_id, id_producto, id-producto)
            if cls.coincide_nombre_fk(a.nombre, clase_ref.nombre):
                score = max(score, 4)
                candidato_attr = a
                break

            # Patrón más laxo: contiene base_ref y ('id' o 'fk' o 'cod')
            a_norm = a.nombre.strip().lower().replace("-", "_").replace(" ", "_")
            if base_ref in a_norm and any(sub in a_norm for sub in ("id", "fk", "cod", "codigo")):
                score = max(score, 3)
                if candidato_attr is None:
                    candidato_attr = a

        # 2. Analizar conexiones/relaciones visibles en el diagrama
        c_ref_lower = clase_c.referencia_semantica.lower()
        c_nom_lower = clase_c.nombre.strip().lower()
        t_ref_lower = clase_ref.referencia_semantica.lower()
        t_nom_lower = clase_ref.nombre.strip().lower()

        for r in relaciones:
            orig = r.origen_ref.strip().lower()
            dest = r.destino_ref.strip().lower()
            tipo_r = cls.normalizar_tipo_relacion(r.tipo)

            if orig in (c_ref_lower, c_nom_lower) and dest in (t_ref_lower, t_nom_lower):
                # Relación sale de clase_c hacia clase_ref
                if tipo_r in {"agregacion", "composicion"}:
                    # Si el rombo está en el destino, clase_c es la parte
                    score += 3
                elif cls.es_cardinalidad_muchos(r.cardinalidad_origen):
                    score += 3
                else:
                    score += 2
                break
            elif dest in (c_ref_lower, c_nom_lower) and orig in (t_ref_lower, t_nom_lower):
                # Relación llega a clase_c desde clase_ref
                if tipo_r in {"agregacion", "composicion"}:
                    # Si el rombo está en clase_c (destino), clase_c es el todo (padre), NO la clase intermedia
                    score += 0
                elif cls.es_cardinalidad_muchos(r.cardinalidad_destino):
                    score += 3
                else:
                    score += 2
                break

        return score, candidato_attr

    @classmethod
    def evaluar_candidato_intermedia_nm(
        cls,
        clase_c: ClaseReconocidaIa,
        clase_a: ClaseReconocidaIa,
        clase_b: ClaseReconocidaIa,
        relaciones: Sequence[RelacionReconocidaIa],
    ) -> tuple[bool, int, AtributoReconocidoIa | None, AtributoReconocidoIa | None]:
        """
        Evalúa si clase_c es una candidata válida para ser la clase intermedia de una N:M entre clase_a y clase_b.
        Retorna (es_candidata, score_total, attr_fk_a, attr_fk_b).
        """
        c_ref = clase_c.referencia_semantica.lower()
        c_nom = clase_c.nombre.strip().lower()
        if c_ref in (clase_a.referencia_semantica.lower(), clase_b.referencia_semantica.lower()) or (
            c_nom in (clase_a.nombre.strip().lower(), clase_b.nombre.strip().lower())
        ):
            return False, 0, None, None

        score_a, attr_a = cls.evaluar_evidencia_referencia_clase(clase_c, clase_a, relaciones)
        score_b, attr_b = cls.evaluar_evidencia_referencia_clase(clase_c, clase_b, relaciones)

        name_c = clase_c.nombre.lower().replace("-", "_").replace(" ", "_")
        name_a = cls.normalizar_nombre_base(clase_a.nombre).replace("-", "_").replace(" ", "_")
        name_b = cls.normalizar_nombre_base(clase_b.nombre).replace("-", "_").replace(" ", "_")

        # Exigencia estructural: debe tener al menos una FK a los extremos o un nombre compuesto
        tiene_fk = (attr_a is not None) or (attr_b is not None)
        nombre_compuesto = (name_a in name_c and name_b in name_c) or (
            "_" in name_c and (name_a in name_c or name_b in name_c)
        )
        if not tiene_fk and not nombre_compuesto:
            return False, 0, None, None

        # Se exige evidencia estructural mínima hacia AMBOS lados
        if score_a < 3 or score_b < 3:
            return False, 0, None, None

        if attr_a is not None and attr_b is not None and attr_a.nombre.strip().lower() == attr_b.nombre.strip().lower():
            return False, 0, None, None

        score_pos = 0
        if (
            clase_c.posicion_relativa_x is not None
            and clase_a.posicion_relativa_x is not None
            and clase_b.posicion_relativa_x is not None
        ):
            mid_x = (clase_a.posicion_relativa_x + clase_b.posicion_relativa_x) / 2.0
            mid_y = ((clase_a.posicion_relativa_y or 0.5) + (clase_b.posicion_relativa_y or 0.5)) / 2.0
            dist = (
                (clase_c.posicion_relativa_x - mid_x) ** 2
                + ((clase_c.posicion_relativa_y or 0.5) - mid_y) ** 2
            ) ** 0.5
            if dist <= 0.45:
                score_pos = 1

        score_name = 0
        if name_a in name_c and name_b in name_c:
            score_name = 2
        elif name_a in name_c or name_b in name_c:
            score_name = 1

        total_score = score_a + score_b + score_pos + score_name
        return True, total_score, attr_a, attr_b

    @classmethod
    def construir_plan(
        cls,
        diagrama_reconocido: DiagramaReconocidoIa,
        diagrama_existente: DiagramaDetalleDTO | None,
        posiciones_layout: dict[str, tuple[int, int]],
    ) -> PlanImportacionImagen:
        plan = PlanImportacionImagen()
        plan.advertencias.extend(diagrama_reconocido.advertencias)

        clases_existentes_lista = (
            diagrama_existente.clases if diagrama_existente else ()
        )

        # Mapa de clases existentes por nombre normalizado y por id
        mapa_existentes_por_nombre: dict[str, Any] = {
            c.nombre.strip().lower(): c for c in clases_existentes_lista
        }
        mapa_existentes_por_id: dict[UUID, Any] = {
            c.id: c for c in clases_existentes_lista
        }

        # Indexar clases reconocidas por referencia semántica y por nombre
        clases_reconocidas_map: dict[str, ClaseReconocidaIa] = {}
        for c in diagrama_reconocido.clases:
            clases_reconocidas_map[c.referencia_semantica.strip().lower()] = c
            clases_reconocidas_map[c.nombre.strip().lower()] = c

        # Mapear relaciones y N:M existentes en el diagrama para evitar duplicados
        relaciones_existentes_set: set[tuple[UUID, UUID, str]] = set()
        estructuras_nm_existentes_set: set[tuple[UUID, UUID]] = set()
        mapa_estructura_nm_existente_por_par: dict[tuple[UUID, UUID], Any] = {}
        if diagrama_existente:
            for r in diagrama_existente.relaciones:
                relaciones_existentes_set.add(
                    (r.id_clase_origen, r.id_clase_destino, r.tipo_relacion.lower())
                )
            for nm in diagrama_existente.estructuras_nm:
                estructuras_nm_existentes_set.add(
                    (nm.id_clase_origen, nm.id_clase_destino)
                )
                estructuras_nm_existentes_set.add(
                    (nm.id_clase_destino, nm.id_clase_origen)
                )
                mapa_estructura_nm_existente_por_par[(nm.id_clase_origen, nm.id_clase_destino)] = nm
                mapa_estructura_nm_existente_por_par[(nm.id_clase_destino, nm.id_clase_origen)] = nm

        # Paso 1: Reconciliación de N:M e identificación de clases intermedias explícitas
        clases_intermedias_nm_asignadas: dict[
            str, tuple[RelacionReconocidaIa | None, AtributoReconocidoIa | None, AtributoReconocidoIa | None, ClaseReconocidaIa, ClaseReconocidaIa | None, ClaseReconocidaIa | None]
        ] = {}
        acciones_nm: list[AccionCrearEstructuraNmSchema] = []
        relaciones_a_omitir: set[int] = set()
        pares_nm_procesados: set[tuple[str, str]] = set()

        # 1.1 Analizar relaciones del diagrama (incluyendo relaciones marcadas erróneamente como 1:N con intermedia visible)
        for rel_idx, rel in enumerate(diagrama_reconocido.relaciones):
            orig_ref = rel.origen_ref.strip()
            dest_ref = rel.destino_ref.strip()
            orig_obj = clases_reconocidas_map.get(orig_ref.lower())
            dest_obj = clases_reconocidas_map.get(dest_ref.lower())

            orig_nombre = (orig_obj.nombre if orig_obj else orig_ref).strip().lower()
            dest_nombre = (dest_obj.nombre if dest_obj else dest_ref).strip().lower()

            # Comprobar si hay una clase intermedia en el diagrama que vincule a orig_obj y dest_obj
            tiene_intermedia_evidente = False
            if orig_obj and dest_obj and orig_obj.referencia_semantica.lower() != dest_obj.referencia_semantica.lower():
                for c_cand in diagrama_reconocido.clases:
                    es_c, _, _, _ = cls.evaluar_candidato_intermedia_nm(
                        c_cand, orig_obj, dest_obj, diagrama_reconocido.relaciones
                    )
                    if es_c:
                        tiene_intermedia_evidente = True
                        break

            es_nm_detectado = rel.es_nm or (
                cls.es_cardinalidad_muchos(rel.cardinalidad_origen)
                and cls.es_cardinalidad_muchos(rel.cardinalidad_destino)
            ) or tiene_intermedia_evidente

            if not es_nm_detectado:
                continue

            par_clave = (orig_nombre, dest_nombre)
            par_clave_inv = (dest_nombre, orig_nombre)
            if par_clave in pares_nm_procesados or par_clave_inv in pares_nm_procesados:
                relaciones_a_omitir.add(rel_idx)
                continue

            # Verificar si la relación N:M ya existe en el diagrama existente
            id_orig_ex = plan.clases_existentes_mapeo.get(orig_nombre) or plan.clases_existentes_mapeo.get(orig_ref.lower()) or (mapa_existentes_por_nombre.get(orig_nombre).id if orig_nombre in mapa_existentes_por_nombre else None)
            id_dest_ex = plan.clases_existentes_mapeo.get(dest_nombre) or plan.clases_existentes_mapeo.get(dest_ref.lower()) or (mapa_existentes_por_nombre.get(dest_nombre).id if dest_nombre in mapa_existentes_por_nombre else None)

            if id_orig_ex and id_dest_ex and (id_orig_ex, id_dest_ex) in estructuras_nm_existentes_set:
                relaciones_a_omitir.add(rel_idx)
                pares_nm_procesados.add(par_clave)
                plan.advertencias.append(
                    f"Estructura N:M entre '{orig_nombre}' y '{dest_nombre}' ya existe en el diagrama; omitida para evitar duplicados."
                )
                nm_ex = mapa_estructura_nm_existente_por_par.get((id_orig_ex, id_dest_ex))
                if nm_ex and orig_obj and dest_obj:
                    for c_cand in diagrama_reconocido.clases:
                        es_c, _, _, _ = cls.evaluar_candidato_intermedia_nm(c_cand, orig_obj, dest_obj, diagrama_reconocido.relaciones)
                        if es_c:
                            plan.clases_existentes_mapeo[c_cand.referencia_semantica.lower()] = nm_ex.id_clase_intermedia
                            plan.clases_existentes_mapeo[c_cand.nombre.strip().lower()] = nm_ex.id_clase_intermedia
                            plan.clases_reutilizadas.append(c_cand.nombre)
                            for attr in c_cand.atributos:
                                plan.atributos_omitidos.append(
                                    f"Atributo '{attr.nombre}' omitido: la clase intermedia de la relación N:M ya existe en el diagrama."
                                )
                            clases_intermedias_nm_asignadas[c_cand.referencia_semantica.lower()] = (rel, None, None, c_cand, orig_obj, dest_obj)
                            break
                continue

            if not orig_obj or not dest_obj:
                continue

            pares_nm_procesados.add(par_clave)
            relaciones_a_omitir.add(rel_idx)

            # Buscar candidatas a clase intermedia en las clases reconocidas
            candidatos: list[tuple[ClaseReconocidaIa, int, AtributoReconocidoIa | None, AtributoReconocidoIa | None]] = []
            for c_cand in diagrama_reconocido.clases:
                if c_cand.referencia_semantica.lower() in clases_intermedias_nm_asignadas:
                    continue
                es_cand, score_cand, attr_a, attr_b = cls.evaluar_candidato_intermedia_nm(
                    c_cand, orig_obj, dest_obj, diagrama_reconocido.relaciones
                )
                if es_cand:
                    candidatos.append((c_cand, score_cand, attr_a, attr_b))

            if len(candidatos) == 0:
                accion_nm = AccionCrearEstructuraNmSchema(
                    clase_origen_referencia=orig_ref,
                    clase_destino_referencia=dest_ref,
                    nombre_intermedia=rel.nombre.strip() if rel.nombre else None,
                )
                acciones_nm.append(accion_nm)
            elif len(candidatos) == 1:
                c_sel, score_sel, attr_a_sel, attr_b_sel = candidatos[0]
                clases_intermedias_nm_asignadas[c_sel.referencia_semantica.lower()] = (
                    rel, attr_a_sel, attr_b_sel, c_sel, orig_obj, dest_obj
                )
                pos_x, pos_y = posiciones_layout.get(c_sel.referencia_semantica, (200, 200))
                accion_nm = AccionCrearEstructuraNmSchema(
                    clase_origen_referencia=orig_ref,
                    clase_destino_referencia=dest_ref,
                    nombre_intermedia=c_sel.nombre.strip(),
                    referencia_intermedia=c_sel.referencia_semantica.strip(),
                    posicion=PosicionSchema(x=float(pos_x), y=float(pos_y)),
                    ancho=280.0,
                )
                acciones_nm.append(accion_nm)
                plan.clases_creadas_referencias.append(c_sel.referencia_semantica)
            else:
                candidatos.sort(key=lambda x: x[1], reverse=True)
                s1 = candidatos[0][1]
                s2 = candidatos[1][1]
                if s1 == s2 or (s1 - s2 <= 1):
                    nombres_cand = ", ".join(repr(c[0].nombre) for c in candidatos)
                    plan.advertencias.append(
                        f"Ambigüedad detectada en relación N:M entre '{orig_obj.nombre}' y '{dest_obj.nombre}': múltiples clases intermedias candidatas ({nombres_cand}) con evidencia similar. Se omite la vinculación automática de la clase intermedia para evitar mutaciones erróneas."
                    )
                    accion_nm = AccionCrearEstructuraNmSchema(
                        clase_origen_referencia=orig_ref,
                        clase_destino_referencia=dest_ref,
                        nombre_intermedia=rel.nombre.strip() if rel.nombre else None,
                    )
                    acciones_nm.append(accion_nm)
                else:
                    c_sel, score_sel, attr_a_sel, attr_b_sel = candidatos[0]
                    clases_intermedias_nm_asignadas[c_sel.referencia_semantica.lower()] = (
                        rel, attr_a_sel, attr_b_sel, c_sel, orig_obj, dest_obj
                    )
                    pos_x, pos_y = posiciones_layout.get(c_sel.referencia_semantica, (200, 200))
                    accion_nm = AccionCrearEstructuraNmSchema(
                        clase_origen_referencia=orig_ref,
                        clase_destino_referencia=dest_ref,
                        nombre_intermedia=c_sel.nombre.strip(),
                        referencia_intermedia=c_sel.referencia_semantica.strip(),
                        posicion=PosicionSchema(x=float(pos_x), y=float(pos_y)),
                        ancho=280.0,
                    )
                    acciones_nm.append(accion_nm)
                    plan.clases_creadas_referencias.append(c_sel.referencia_semantica)

        # 1.2 Detectar clases intermedias estructurales que no tenían relación directa A-B
        for c_cand in diagrama_reconocido.clases:
            if c_cand.referencia_semantica.lower() in clases_intermedias_nm_asignadas:
                continue

            hallazgos_par: list[tuple[ClaseReconocidaIa, ClaseReconocidaIa, int, AtributoReconocidoIa | None, AtributoReconocidoIa | None]] = []
            todas_clases = [c for c in diagrama_reconocido.clases if c.referencia_semantica.lower() != c_cand.referencia_semantica.lower()]

            for i in range(len(todas_clases)):
                for j in range(i + 1, len(todas_clases)):
                    cl_a = todas_clases[i]
                    cl_b = todas_clases[j]
                    es_c, score_c, attr_a, attr_b = cls.evaluar_candidato_intermedia_nm(
                        c_cand, cl_a, cl_b, diagrama_reconocido.relaciones
                    )
                    if es_c:
                        hallazgos_par.append((cl_a, cl_b, score_c, attr_a, attr_b))

            if len(hallazgos_par) == 1:
                cl_a, cl_b, score_c, attr_a, attr_b = hallazgos_par[0]
                par_k = (cl_a.nombre.strip().lower(), cl_b.nombre.strip().lower())
                par_k_inv = (cl_b.nombre.strip().lower(), cl_a.nombre.strip().lower())

                if par_k not in pares_nm_procesados and par_k_inv not in pares_nm_procesados:
                    pares_nm_procesados.add(par_k)
                    clases_intermedias_nm_asignadas[c_cand.referencia_semantica.lower()] = (
                        None, attr_a, attr_b, c_cand, cl_a, cl_b
                    )
                    pos_x, pos_y = posiciones_layout.get(c_cand.referencia_semantica, (200, 200))
                    accion_nm = AccionCrearEstructuraNmSchema(
                        clase_origen_referencia=cl_a.referencia_semantica,
                        clase_destino_referencia=cl_b.referencia_semantica,
                        nombre_intermedia=c_cand.nombre.strip(),
                        referencia_intermedia=c_cand.referencia_semantica.strip(),
                        posicion=PosicionSchema(x=float(pos_x), y=float(pos_y)),
                        ancho=280.0,
                    )
                    acciones_nm.append(accion_nm)
                    plan.clases_creadas_referencias.append(c_cand.referencia_semantica)

        # Paso 2: Reconciliar clases regulares
        acciones_clases: list[AccionCrearClaseSchema] = []
        for clase_rec in diagrama_reconocido.clases:
            ref_semantica = clase_rec.referencia_semantica.strip()
            nombre_norm = clase_rec.nombre.strip().lower()

            if ref_semantica.lower() in clases_intermedias_nm_asignadas:
                continue

            if nombre_norm in mapa_existentes_por_nombre:
                clase_ex = mapa_existentes_por_nombre[nombre_norm]
                plan.clases_reutilizadas.append(clase_ex.nombre)
                plan.clases_existentes_mapeo[ref_semantica.lower()] = clase_ex.id
                plan.clases_existentes_mapeo[nombre_norm] = clase_ex.id
                plan.clases_existentes_mapeo[str(clase_ex.id).lower()] = clase_ex.id
            else:
                pos_x, pos_y = posiciones_layout.get(ref_semantica, (200, 200))
                accion_clase = AccionCrearClaseSchema(
                    referencia=ref_semantica,
                    nombre=clase_rec.nombre.strip(),
                    posicion=PosicionSchema(x=float(pos_x), y=float(pos_y)),
                    ancho=280.0,
                )
                acciones_clases.append(accion_clase)
                plan.clases_creadas_referencias.append(ref_semantica)

        # Paso 3: Reconciliar relaciones 1:1 y 1:N e identificar FKs estructurales
        atributos_fk_excluidos: set[tuple[str, str]] = set()
        info_fk_por_relacion: dict[int, tuple[str, str]] = {}
        acciones_relaciones: list[AccionIaUnion] = []

        for rel_idx, rel in enumerate(diagrama_reconocido.relaciones):
            if rel_idx in relaciones_a_omitir:
                continue

            es_nm_detectado = rel.es_nm or (
                cls.es_cardinalidad_muchos(rel.cardinalidad_origen)
                and cls.es_cardinalidad_muchos(rel.cardinalidad_destino)
            )
            if es_nm_detectado:
                continue

            orig_ref = rel.origen_ref.strip()
            dest_ref = rel.destino_ref.strip()

            if orig_ref.lower() in clases_intermedias_nm_asignadas or dest_ref.lower() in clases_intermedias_nm_asignadas:
                continue

            orig_obj = clases_reconocidas_map.get(orig_ref.lower())
            dest_obj = clases_reconocidas_map.get(dest_ref.lower())

            orig_nombre = (orig_obj.nombre if orig_obj else orig_ref).strip().lower()
            dest_nombre = (dest_obj.nombre if dest_obj else dest_ref).strip().lower()

            par_nm = (orig_nombre, dest_nombre)
            par_nm_inv = (dest_nombre, orig_nombre)
            if par_nm in pares_nm_procesados or par_nm_inv in pares_nm_procesados:
                relaciones_a_omitir.add(rel_idx)
                continue

            id_orig_ex = plan.clases_existentes_mapeo.get(orig_nombre) or plan.clases_existentes_mapeo.get(orig_ref.lower())
            id_dest_ex = plan.clases_existentes_mapeo.get(dest_nombre) or plan.clases_existentes_mapeo.get(dest_ref.lower())

            if id_orig_ex and id_dest_ex:
                tipo_rel_norm = cls.normalizar_tipo_relacion(rel.tipo)
                if (id_orig_ex, id_dest_ex, tipo_rel_norm) in relaciones_existentes_set or (
                    id_dest_ex, id_orig_ex, tipo_rel_norm
                ) in relaciones_existentes_set:
                    relaciones_a_omitir.add(rel_idx)
                    plan.advertencias.append(
                        f"Relación entre '{orig_nombre}' y '{dest_nombre}' ya existe en el diagrama; omitida para evitar duplicados."
                    )
                    continue

            clase_fk_ref, clase_ref_ref, requiere_fk = cls.determinar_lado_fk_relacion(
                rel, clases_reconocidas_map
            )

            if requiere_fk and clase_fk_ref and clase_ref_ref:
                clase_fk_obj = clases_reconocidas_map.get(clase_fk_ref.lower())
                clase_ref_obj = clases_reconocidas_map.get(clase_ref_ref.lower())
                nombre_clase_ref = clase_ref_obj.nombre if clase_ref_obj else clase_ref_ref
                es_rec = rel.es_recursiva or (orig_ref.lower() == dest_ref.lower())

                if clase_fk_obj:
                    candidato: AtributoReconocidoIa | None = None

                    for a in clase_fk_obj.atributos:
                        nombre_limpio_a = cls.limpiar_nombre_atributo(a.nombre)
                        if a.es_pk or nombre_limpio_a.lower() == "id":
                            continue
                        if (
                            a.fk_destino_ref
                            and a.fk_destino_ref.strip().lower()
                            in (clase_ref_ref.lower(), nombre_clase_ref.lower())
                        ):
                            candidato = a
                            break

                    if not candidato:
                        for a in clase_fk_obj.atributos:
                            nombre_limpio_a = cls.limpiar_nombre_atributo(a.nombre)
                            if a.es_pk or nombre_limpio_a.lower() == "id":
                                continue
                            if a.es_fk and cls.coincide_nombre_fk(
                                nombre_limpio_a, nombre_clase_ref, es_rec
                            ):
                                candidato = a
                                break

                    if not candidato:
                        for a in clase_fk_obj.atributos:
                            nombre_limpio_a = cls.limpiar_nombre_atributo(a.nombre)
                            if a.es_pk or nombre_limpio_a.lower() == "id":
                                continue
                            if cls.coincide_nombre_fk(
                                nombre_limpio_a, nombre_clase_ref, es_rec
                            ):
                                candidato = a
                                break

                    if not candidato:
                        fk_attrs = [
                            a
                            for a in clase_fk_obj.atributos
                            if a.es_fk and not a.es_pk and cls.limpiar_nombre_atributo(a.nombre).lower() != "id"
                        ]
                        if len(fk_attrs) == 1:
                            candidato = fk_attrs[0]

                    if candidato:
                        cand_nom_limpio = cls.limpiar_nombre_atributo(candidato.nombre)
                        clave_attr = (
                            clase_fk_obj.referencia_semantica.lower(),
                            cand_nom_limpio.lower(),
                        )
                        atributos_fk_excluidos.add(clave_attr)
                        info_fk_por_relacion[rel_idx] = (
                            cand_nom_limpio,
                            clase_fk_ref,
                        )

            # Proactivamente excluir cualquier atributo que coincida con patrón FK de las clases vinculadas
            if orig_obj and dest_obj:
                for a in orig_obj.atributos:
                    a_limpio = cls.limpiar_nombre_atributo(a.nombre)
                    if cls.coincide_nombre_fk(a_limpio, dest_obj.nombre):
                        atributos_fk_excluidos.add((orig_obj.referencia_semantica.lower(), a_limpio.lower()))
                for a in dest_obj.atributos:
                    a_limpio = cls.limpiar_nombre_atributo(a.nombre)
                    if cls.coincide_nombre_fk(a_limpio, orig_obj.nombre):
                        atributos_fk_excluidos.add((dest_obj.referencia_semantica.lower(), a_limpio.lower()))

            card_orig = cls.normalizar_cardinalidad(
                rel.cardinalidad_origen, default="1"
            )
            card_dest = cls.normalizar_cardinalidad(
                rel.cardinalidad_destino, default="0..*"
            )
            tipo_rel = cls.normalizar_tipo_relacion(rel.tipo)
            nombre_fk, clase_fk_ref = info_fk_por_relacion.get(
                rel_idx, (None, None)
            )

            accion_rel = AccionCrearRelacionSchema(
                clase_origen_referencia=orig_ref,
                clase_destino_referencia=dest_ref,
                tipo_relacion=tipo_rel,
                cardinalidad_origen=card_orig,
                cardinalidad_destino=card_dest,
                nombre=rel.nombre.strip() if rel.nombre else None,
                nombre_fk=nombre_fk,
                clase_fk_referencia=clase_fk_ref,
            )
            acciones_relaciones.append(accion_rel)

        # Paso 4: Reconciliar atributos separando clases regulares de intermedias N:M
        acciones_atributos_regulares: list[AccionIaUnion] = []
        acciones_atributos_intermedias: list[AccionIaUnion] = []

        for clase_rec in diagrama_reconocido.clases:
            nombre_norm = clase_rec.nombre.strip().lower()
            ref_semantica = clase_rec.referencia_semantica.strip()

            if nombre_norm in mapa_existentes_por_nombre:
                clase_ex = mapa_existentes_por_nombre[nombre_norm]
                nombres_existentes = {
                    cls.limpiar_nombre_atributo(a.nombre).lower() for a in clase_ex.atributos
                }
                nombres_registrados_clase = set(nombres_existentes)

                for attr in clase_rec.atributos:
                    tipo_norm = cls.normalizar_tipo_dato(attr.tipo_detectado)
                    nombre_attr = cls.limpiar_nombre_atributo(attr.nombre)
                    nombre_attr_norm = nombre_attr.lower()

                    if nombre_attr_norm in nombres_existentes:
                        plan.atributos_omitidos.append(
                            f"Atributo '{nombre_attr}' ya existe en la clase '{clase_ex.nombre}'."
                        )
                        continue

                    # Si es una FK que se materializará mediante una relación de la imagen, omitir
                    if (ref_semantica.lower(), nombre_attr_norm) in atributos_fk_excluidos:
                        continue

                    # Si es PK o identificador primario, la clase existente en el diagrama ya cuenta con su identidad propia
                    if attr.es_pk or cls.es_identificador_pk(nombre_attr, clase_ex.nombre) or nombre_attr_norm in {"id", "pk"}:
                        plan.atributos_omitidos.append(
                            f"Atributo PK '{nombre_attr}' omitido: la clase '{clase_ex.nombre}' ya cuenta con llave primaria."
                        )
                        continue

                    if nombre_attr_norm in nombres_registrados_clase:
                        continue

                    nombres_registrados_clase.add(nombre_attr_norm)
                    accion_attr = AccionCrearAtributoSchema(
                        clase_referencia=ref_semantica,
                        nombre=nombre_attr,
                        tipo_dato=tipo_norm,
                        permite_nulo=attr.permite_nulo,
                        es_unico=False,
                        es_llave_primaria=False,
                    )
                    acciones_atributos_regulares.append(accion_attr)
                continue

            if ref_semantica.lower() in clases_intermedias_nm_asignadas:
                rel_nm, attr_fk_a, attr_fk_b, c_obj, orig_nm, dest_nm = clases_intermedias_nm_asignadas[
                    ref_semantica.lower()
                ]
                nombres_fk_excluir: set[str] = set()
                if attr_fk_a:
                    nombres_fk_excluir.add(cls.limpiar_nombre_atributo(attr_fk_a.nombre).lower())
                if attr_fk_b:
                    nombres_fk_excluir.add(cls.limpiar_nombre_atributo(attr_fk_b.nombre).lower())

                nombres_creados_en_clase: set[str] = {"id", "pk"}

                for attr in clase_rec.atributos:
                    tipo_norm = cls.normalizar_tipo_dato(attr.tipo_detectado)
                    attr_name = cls.limpiar_nombre_atributo(attr.nombre)
                    attr_name_norm = attr_name.lower()

                    # Omitir cualquier PK (la tabla intermedia nace con su ID por defecto)
                    if attr.es_pk or cls.es_identificador_pk(attr_name, clase_rec.nombre) or attr_name_norm in {"id", "pk"}:
                        continue

                    # Omitir foráneas hacia origen o destino (se materializan con CrearEstructuraNm)
                    if attr_name_norm in nombres_fk_excluir or attr_name_norm in nombres_creados_en_clase:
                        continue
                    if orig_nm and cls.coincide_nombre_fk(attr_name, orig_nm.nombre):
                        continue
                    if dest_nm and cls.coincide_nombre_fk(attr_name, dest_nm.nombre):
                        continue

                    nombres_creados_en_clase.add(attr_name_norm)
                    accion_attr = AccionCrearAtributoSchema(
                        clase_referencia=ref_semantica,
                        nombre=attr_name,
                        tipo_dato=tipo_norm,
                        permite_nulo=attr.permite_nulo,
                        es_unico=False,
                        es_llave_primaria=False,
                    )
                    acciones_atributos_intermedias.append(accion_attr)
                continue

            # Clases regulares nuevas: omitir PK (nace con id PK) y FKs de relaciones
            nombres_creados_en_clase: set[str] = {"id", "pk"}

            for attr in clase_rec.atributos:
                tipo_norm = cls.normalizar_tipo_dato(attr.tipo_detectado)
                nombre_attr = cls.limpiar_nombre_atributo(attr.nombre)
                nombre_attr_norm = nombre_attr.lower()

                # Omitir PK (la clase nace con su 'id' PK por defecto)
                if attr.es_pk or cls.es_identificador_pk(nombre_attr, clase_rec.nombre) or nombre_attr_norm in {"id", "pk"}:
                    continue

                # Omitir FKs hacia relaciones vinculadas
                if (ref_semantica.lower(), nombre_attr_norm) in atributos_fk_excluidos:
                    continue
                if nombre_attr_norm in nombres_creados_en_clase:
                    continue

                nombres_creados_en_clase.add(nombre_attr_norm)
                accion_attr = AccionCrearAtributoSchema(
                    clase_referencia=ref_semantica,
                    nombre=nombre_attr,
                    tipo_dato=tipo_norm,
                    permite_nulo=attr.permite_nulo,
                    es_unico=False,
                    es_llave_primaria=False,
                )
                acciones_atributos_regulares.append(accion_attr)

        # Paso 5: Ensamblar plan en orden estricto de dependencias
        plan.acciones.extend(acciones_clases)
        plan.acciones.extend(acciones_atributos_regulares)
        plan.acciones.extend(acciones_nm)
        plan.acciones.extend(acciones_atributos_intermedias)
        plan.acciones.extend(acciones_relaciones)

        return plan
