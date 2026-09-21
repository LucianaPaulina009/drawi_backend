from __future__ import annotations

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
    """Valida referencias y ordena las acciones generadas por la IA:
    Para creaciones: Clases -> Estructuras N:M (con clase intermedia) -> Atributos -> Relaciones.
    Para actualizaciones y eliminaciones: valida dependencias de existencia y recursos eliminados.
    """

    @classmethod
    def planificar(
        cls,
        acciones: list[AccionIaUnion],
        clases_existentes: dict[str, UUID] | None = None,
    ) -> list[AccionIaUnion]:
        clases_disponibles: dict[str, str | UUID] = {}
        if clases_existentes:
            for clave, uid in clases_existentes.items():
                clases_disponibles[clave.lower()] = uid
                clases_disponibles[str(uid).lower()] = uid

        # 1. Agrupar creaciones para ordenarlas según dependencias estructurales
        acciones_crear_clases: list[AccionCrearClaseSchema] = []
        acciones_crear_estructuras_nm: list[AccionCrearEstructuraNmSchema] = []
        acciones_crear_atributos: list[AccionCrearAtributoSchema] = []
        acciones_crear_relaciones: list[AccionCrearRelacionSchema] = []
        otras_acciones: list[AccionIaUnion] = []

        # Registrar alias de nuevas clases y estructuras N:M
        for accion in acciones:
            if isinstance(accion, AccionCrearClaseSchema):
                ref = accion.referencia.strip().lower()
                if not ref:
                    raise PlanIaInvalidoException("La referencia de la clase no puede estar vacía.")
                clases_disponibles[ref] = ref
                clases_disponibles[accion.nombre.strip().lower()] = ref
                acciones_crear_clases.append(accion)
            elif isinstance(accion, AccionCrearEstructuraNmSchema):
                orig_ref = accion.clase_origen_referencia.strip()
                dest_ref = accion.clase_destino_referencia.strip()
                default_name = f"{orig_ref}_{dest_ref}".lower()
                if accion.referencia_intermedia:
                    ref_inter = accion.referencia_intermedia.strip().lower()
                    clases_disponibles[ref_inter] = ref_inter
                if accion.nombre_intermedia:
                    nom_inter = accion.nombre_intermedia.strip().lower()
                    clases_disponibles[nom_inter] = nom_inter
                clases_disponibles[default_name] = default_name
                clases_disponibles[f"{dest_ref}_{orig_ref}".lower()] = default_name
                clases_disponibles[f"{orig_ref}{dest_ref}".lower()] = default_name
                clases_disponibles[f"{dest_ref}{orig_ref}".lower()] = default_name
                clases_disponibles["intermedia"] = default_name
                clases_disponibles["tabla intermedia"] = default_name
                clases_disponibles["tabla de muchos a muchos"] = default_name
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

        # Validar dependencias de atributos a crear
        for attr in acciones_crear_atributos:
            ref = attr.clase_referencia.strip().lower()
            if ref not in clases_disponibles:
                raise PlanIaInvalidoException(
                    f"El atributo '{attr.nombre}' referencia una clase desconocida: '{attr.clase_referencia}'."
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

        # 2. Ensamblar plan:
        # En planes mixtos, las creaciones se ordenan:
        # clases -> estructuras N:M (clases intermedias) -> atributos -> relaciones,
        # seguidas de las demás acciones (actualizaciones, eliminaciones).
        resultado: list[AccionIaUnion] = []
        resultado.extend(acciones_crear_clases)
        resultado.extend(acciones_crear_estructuras_nm)
        resultado.extend(acciones_crear_atributos)
        resultado.extend(acciones_crear_relaciones)
        resultado.extend(otras_acciones)

        return resultado
