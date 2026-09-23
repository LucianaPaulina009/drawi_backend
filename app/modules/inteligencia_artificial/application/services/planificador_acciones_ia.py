from __future__ import annotations

import re
from typing import Any
from uuid import UUID

from app.modules.inteligencia_artificial.application.services.validador_respuesta_ia import (
    AccionActualizarAtributoSchema,
    AccionActualizarClaseSchema,
    AccionActualizarRelacionSchema,
    AccionCrearAtributoSchema,
    AccionCrearClaseSchema,
    AccionCrearEstructuraNmSchema,
    AccionCrearRelacionSchema,
    AccionEliminarAtributoSchema,
    AccionEliminarClaseSchema,
    AccionEliminarEstructuraNmSchema,
    AccionEliminarRelacionSchema,
    AccionIaUnion,
)
from app.modules.inteligencia_artificial.domain.exceptions import PlanIaInvalidoException


class PlanificadorAccionesIa:
    """Valida referencias, depura redundancias de PKs y FKs, y ordena las acciones generadas por la IA:
    Para creaciones: Clases -> Atributos Base -> Estructuras N:M -> Relaciones (1:1 / 1:N con materialización FK) -> Atributos Intermedias -> Otras.
    Para actualizaciones y eliminaciones: valida dependencias de existencia y recursos eliminados.
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
    def es_identificador_pk(cls, nombre_attr: str, nombre_clase: str = "") -> bool:
        """
        Determina si un nombre de atributo representa la clave primaria propia de una clase
        (ej. id, pk, id_producto, producto_id, cod_producto, etc.).
        """
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
    def coincide_nombre_fk(
        cls, nombre_attr: str, nombre_clase_ref: str, es_recursiva: bool = False
    ) -> bool:
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
    def _es_cardinalidad_muchos(cls, card: str | None) -> bool:
        if not card:
            return False
        c = card.strip().lower()
        return c in {"*", "0..*", "1..*", "n", "m", "0..n", "1..n", "0..m", "1..m"}

    @classmethod
    def planificar(
        cls,
        acciones: list[AccionIaUnion],
        clases_existentes: dict[str, UUID] | None = None,
    ) -> list[AccionIaUnion]:
        clases_disponibles: dict[str, str | UUID] = {}
        mapa_nombres_clases: dict[str, str] = {}

        if clases_existentes:
            for clave, uid in clases_existentes.items():
                clave_norm = clave.strip().lower()
                clases_disponibles[clave_norm] = uid
                clases_disponibles[str(uid).lower()] = uid
                mapa_nombres_clases[clave_norm] = clave.strip()
                mapa_nombres_clases[str(uid).lower()] = clave.strip()

        # 1. Agrupar creaciones para ordenarlas según dependencias estructurales
        acciones_crear_clases: list[AccionCrearClaseSchema] = []
        acciones_crear_estructuras_nm: list[AccionCrearEstructuraNmSchema] = []
        acciones_crear_atributos: list[AccionCrearAtributoSchema] = []
        acciones_crear_relaciones: list[AccionCrearRelacionSchema] = []
        otras_acciones: list[AccionIaUnion] = []

        alias_clases_base: set[str] = set(clases_disponibles.keys())
        alias_clases_intermedias: set[str] = set()
        info_estructuras_nm: list[dict[str, str]] = []

        # Registrar alias de nuevas clases y estructuras N:M
        for accion in acciones:
            if isinstance(accion, AccionCrearClaseSchema):
                ref = accion.referencia.strip().lower()
                if not ref:
                    raise PlanIaInvalidoException("La referencia de la clase no puede estar vacía.")
                clases_disponibles[ref] = ref
                clases_disponibles[accion.nombre.strip().lower()] = ref
                mapa_nombres_clases[ref] = accion.nombre.strip()
                mapa_nombres_clases[accion.nombre.strip().lower()] = accion.nombre.strip()
                alias_clases_base.add(ref)
                alias_clases_base.add(accion.nombre.strip().lower())
                acciones_crear_clases.append(accion)
            elif isinstance(accion, AccionCrearEstructuraNmSchema):
                orig_ref = accion.clase_origen_referencia.strip()
                dest_ref = accion.clase_destino_referencia.strip()
                orig_name = mapa_nombres_clases.get(orig_ref.lower(), orig_ref)
                dest_name = mapa_nombres_clases.get(dest_ref.lower(), dest_ref)

                nombre_inter = accion.nombre_intermedia.strip() if accion.nombre_intermedia else f"{orig_name}_{dest_name}"
                ref_inter = accion.referencia_intermedia.strip().lower() if accion.referencia_intermedia else nombre_inter.lower()

                clases_disponibles[ref_inter] = ref_inter
                clases_disponibles[nombre_inter.lower()] = ref_inter
                mapa_nombres_clases[ref_inter] = nombre_inter
                mapa_nombres_clases[nombre_inter.lower()] = nombre_inter

                default_name = f"{orig_ref}_{dest_ref}".lower()
                clases_disponibles[default_name] = default_name
                clases_disponibles[f"{dest_ref}_{orig_ref}".lower()] = default_name
                clases_disponibles[f"{orig_ref}{dest_ref}".lower()] = default_name
                clases_disponibles[f"{dest_ref}{orig_ref}".lower()] = default_name
                clases_disponibles["intermedia"] = default_name
                clases_disponibles["tabla intermedia"] = default_name
                clases_disponibles["tabla de muchos a muchos"] = default_name

                alias_clases_intermedias.add(ref_inter)
                alias_clases_intermedias.add(nombre_inter.lower())
                alias_clases_intermedias.add(default_name)
                alias_clases_intermedias.add(f"{dest_ref}_{orig_ref}".lower())
                alias_clases_intermedias.add(f"{orig_ref}{dest_ref}".lower())
                alias_clases_intermedias.add(f"{dest_ref}{orig_ref}".lower())
                alias_clases_intermedias.add("intermedia")
                alias_clases_intermedias.add("tabla intermedia")
                alias_clases_intermedias.add("tabla de muchos a muchos")

                info_estructuras_nm.append({
                    "ref_intermedia": ref_inter,
                    "nombre_intermedia": nombre_inter,
                    "origen_ref": orig_ref,
                    "destino_ref": dest_ref,
                    "origen_nombre": orig_name,
                    "destino_nombre": dest_name,
                })

                acciones_crear_estructuras_nm.append(accion)
            elif isinstance(accion, AccionCrearAtributoSchema):
                acciones_crear_atributos.append(accion)
            elif isinstance(accion, AccionCrearRelacionSchema):
                acciones_crear_relaciones.append(accion)
            else:
                otras_acciones.append(accion)

        # Validar dependencias de estructuras N:M a crear
        for struct in acciones_crear_estructuras_nm:
            origen = struct.clase_origen_referencia.strip().lower()
            destino = struct.clase_destino_referencia.strip().lower()
            if origen not in clases_disponibles:
                raise PlanIaInvalidoException(
                    f"La estructura N:M referencia un origen desconocido: '{struct.clase_origen_referencia}'."
                )
            if destino not in clases_disponibles:
                raise PlanIaInvalidoException(
                    f"La estructura N:M referencia un destino desconocido: '{struct.clase_destino_referencia}'."
                )

        # Validar dependencias de relaciones a crear
        for rel in acciones_crear_relaciones:
            origen = rel.clase_origen_referencia.strip().lower()
            destino = rel.clase_destino_referencia.strip().lower()
            if origen not in clases_disponibles:
                raise PlanIaInvalidoException(
                    f"La relación '{rel.nombre or 'rel'}' referencia un origen desconocido: '{rel.clase_origen_referencia}'."
                )
            if destino not in clases_disponibles:
                raise PlanIaInvalidoException(
                    f"La relación '{rel.nombre or 'rel'}' referencia un destino desconocido: '{rel.clase_destino_referencia}'."
                )

        # 2. Reconciliar FKs de relaciones 1:1 y 1:N con posibles acciones crear_atributo redundantes
        atributos_fk_relaciones_excluidos: set[tuple[str, str]] = set()

        for rel in acciones_crear_relaciones:
            orig_ref = rel.clase_origen_referencia.strip().lower()
            dest_ref = rel.clase_destino_referencia.strip().lower()
            orig_name = mapa_nombres_clases.get(orig_ref, rel.clase_origen_referencia)
            dest_name = mapa_nombres_clases.get(dest_ref, rel.clase_destino_referencia)

            es_muchos_orig = cls._es_cardinalidad_muchos(rel.cardinalidad_origen)
            es_muchos_dest = cls._es_cardinalidad_muchos(rel.cardinalidad_destino)

            # Determinar en qué clase se aloja la llave foránea
            if rel.clase_fk_referencia:
                clase_fk_ref = rel.clase_fk_referencia.strip().lower()
                clase_fk_nombre = mapa_nombres_clases.get(clase_fk_ref, rel.clase_fk_referencia)
                clase_ref_nombre = orig_name if clase_fk_ref == dest_ref else dest_name
            elif es_muchos_dest and not es_muchos_orig:
                clase_fk_ref = dest_ref
                clase_fk_nombre = dest_name
                clase_ref_nombre = orig_name
            elif es_muchos_orig and not es_muchos_dest:
                clase_fk_ref = orig_ref
                clase_fk_nombre = orig_name
                clase_ref_nombre = dest_name
            else:
                # 1:1 o default: FK en destino
                clase_fk_ref = dest_ref
                clase_fk_nombre = dest_name
                clase_ref_nombre = orig_name

            es_rec = orig_ref == dest_ref

            # Buscar si el usuario / IA envió una acción crear_atributo que coincida con la FK de esta relación
            for attr in acciones_crear_atributos:
                attr_clase_ref = attr.clase_referencia.strip().lower()
                # Verificar si el atributo va dirigido a la clase donde reside la FK
                if attr_clase_ref in {clase_fk_ref, clase_fk_nombre.lower()}:
                    attr_nombre_limpio = cls.limpiar_nombre_atributo(attr.nombre)
                    if cls.coincide_nombre_fk(attr_nombre_limpio, clase_ref_nombre, es_rec):
                        # Asociar el nombre exacto de la FK a la relación si no estaba definido
                        if not rel.nombre_fk:
                            rel.nombre_fk = attr_nombre_limpio
                        if not rel.clase_fk_referencia:
                            rel.clase_fk_referencia = rel.clase_destino_referencia if clase_fk_ref == dest_ref else rel.clase_origen_referencia
                        atributos_fk_relaciones_excluidos.add((attr_clase_ref, attr_nombre_limpio.lower()))

        # 3. Filtrar y clasificar atributos
        atributos_clases_base: list[AccionCrearAtributoSchema] = []
        atributos_clases_intermedias: list[AccionCrearAtributoSchema] = []

        for attr in acciones_crear_atributos:
            ref = attr.clase_referencia.strip().lower()
            if ref not in clases_disponibles:
                raise PlanIaInvalidoException(
                    f"El atributo '{attr.nombre}' referencia una clase desconocida: '{attr.clase_referencia}'."
                )

            nombre_clase = mapa_nombres_clases.get(ref, attr.clase_referencia)
            attr_limpio = cls.limpiar_nombre_atributo(attr.nombre)
            attr_norm = attr_limpio.lower()

            es_intermedia = ref in alias_clases_intermedias and ref not in alias_clases_base

            # A) Ignorar llaves primarias redundantes ('id', 'pk', o marcadas como PK)
            if (
                attr.es_llave_primaria
                or attr_norm in {"id", "pk", "id_pk", "pk_id"}
                or cls.es_identificador_pk(attr_limpio, nombre_clase)
            ):
                continue

            # B) Si es para una clase intermedia N:M, filtrar FKs redundantes generadas por crear_estructura_nm
            if es_intermedia:
                # Buscar información de la estructura N:M correspondiente
                es_fk_intermedia = False
                for struct_info in info_estructuras_nm:
                    if ref in {
                        struct_info["ref_intermedia"],
                        struct_info["nombre_intermedia"].lower(),
                    }:
                        if cls.coincide_nombre_fk(
                            attr_limpio, struct_info["origen_nombre"]
                        ) or cls.coincide_nombre_fk(
                            attr_limpio, struct_info["destino_nombre"]
                        ):
                            es_fk_intermedia = True
                            break
                if es_fk_intermedia:
                    continue

                # Atributo de payload válido en tabla intermedia
                attr.es_llave_primaria = False
                atributos_clases_intermedias.append(attr)
                continue

            # C) Si coincide con una FK materializada por una relación 1:1 o 1:N, omitir
            if (ref, attr_norm) in atributos_fk_relaciones_excluidos:
                continue

            # D) Atributo regular en clase base
            attr.es_llave_primaria = False
            atributos_clases_base.append(attr)

        # Validar referencias de otras acciones
        for act in otras_acciones:
            if isinstance(act, (AccionActualizarClaseSchema, AccionEliminarClaseSchema)):
                ref = act.clase_referencia.strip().lower()
                if ref not in clases_disponibles:
                    raise PlanIaInvalidoException(f"La acción referencia una clase desconocida: '{act.clase_referencia}'.")
            elif isinstance(act, (AccionActualizarAtributoSchema, AccionEliminarAtributoSchema)):
                ref = act.clase_referencia.strip().lower()
                if ref not in clases_disponibles:
                    raise PlanIaInvalidoException(f"La acción de atributo referencia una clase desconocida: '{act.clase_referencia}'.")
            elif isinstance(act, (AccionActualizarRelacionSchema, AccionEliminarRelacionSchema, AccionEliminarEstructuraNmSchema)):
                origen = act.clase_origen_referencia.strip().lower()
                destino = act.clase_destino_referencia.strip().lower()
                if origen not in clases_disponibles:
                    raise PlanIaInvalidoException(f"La relación referencia un origen desconocido: '{act.clase_origen_referencia}'.")
                if destino not in clases_disponibles:
                    raise PlanIaInvalidoException(f"La relación referencia un destino desconocido: '{act.clase_destino_referencia}'.")

        # 4. Ensamblar plan en orden topológico estricto:
        # 1) Clases base
        # 2) Atributos de clases base
        # 3) Estructuras N:M (crean la clase intermedia + FKs)
        # 4) Relaciones 1:1 y 1:N (materializan FKs)
        # 5) Atributos de clases intermedias (payload adicional como 'cantidad')
        # 6) Otras acciones (actualizaciones, eliminaciones)
        resultado: list[AccionIaUnion] = []
        resultado.extend(acciones_crear_clases)
        resultado.extend(atributos_clases_base)
        resultado.extend(acciones_crear_estructuras_nm)
        resultado.extend(acciones_crear_relaciones)
        resultado.extend(atributos_clases_intermedias)
        resultado.extend(otras_acciones)

        return resultado
