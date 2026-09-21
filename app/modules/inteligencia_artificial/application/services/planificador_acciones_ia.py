from __future__ import annotations

from typing import Any
from uuid import UUID

from app.modules.inteligencia_artificial.application.services.validador_respuesta_ia import (
    AccionCrearAtributoSchema,
    AccionCrearClaseSchema,
    AccionCrearRelacionSchema,
    AccionIaUnion,
)
from app.modules.inteligencia_artificial.domain.exceptions import PlanIaInvalidoException


class PlanificadorAccionesIa:
    """Valida referencias y ordena las acciones generadas por la IA: Clases -> Atributos -> Relaciones."""

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

        acciones_clases: list[AccionCrearClaseSchema] = []
        acciones_atributos: list[AccionCrearAtributoSchema] = []
        acciones_relaciones: list[AccionCrearRelacionSchema] = []

        # Separar por tipo y registrar alias de nuevas clases
        for accion in acciones:
            if isinstance(accion, AccionCrearClaseSchema):
                ref = accion.referencia.strip().lower()
                if not ref:
                    raise PlanIaInvalidoException("La referencia de la clase no puede estar vacía.")
                if ref in clases_disponibles and not clases_existentes:
                    raise PlanIaInvalidoException(f"Referencia de clase duplicada en el plan: {ref}")
                clases_disponibles[ref] = ref
                clases_disponibles[accion.nombre.strip().lower()] = ref
                acciones_clases.append(accion)
            elif isinstance(accion, AccionCrearAtributoSchema):
                acciones_atributos.append(accion)
            elif isinstance(accion, AccionCrearRelacionSchema):
                acciones_relaciones.append(accion)

        # Validar dependencias de atributos
        for attr in acciones_atributos:
            ref = attr.clase_referencia.strip().lower()
            if ref not in clases_disponibles:
                raise PlanIaInvalidoException(
                    f"El atributo '{attr.nombre}' referencia una clase desconocida: '{attr.clase_referencia}'."
                )

        # Validar dependencias de relaciones
        for rel in acciones_relaciones:
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

        # Retornar en orden estricto de resolución de dependencias
        resultado: list[AccionIaUnion] = []
        resultado.extend(acciones_clases)
        resultado.extend(acciones_atributos)
        resultado.extend(acciones_relaciones)
        return resultado
