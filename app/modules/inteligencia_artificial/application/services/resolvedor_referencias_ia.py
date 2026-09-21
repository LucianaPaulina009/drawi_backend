from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID


@dataclass(slots=True)
class ResultadoResolucion:
    exito: bool
    id: UUID | None = None
    es_ambiguo: bool = False
    motivo: str | None = None
    metadatos: dict[str, Any] | None = None


class ResolvedorReferenciasIa:
    """
    Resuelve deterministamente referencias semánticas (nombres, alias)
    contra el estado real y autorizado del diagrama.
    No realiza conjeturas difusas ni elecciones arbitrarias.
    """

    @staticmethod
    def resolver_clase(
        referencia: str,
        clases: list[Any],
        mapa_alias: dict[str, UUID] | None = None,
    ) -> ResultadoResolucion:
        ref = referencia.strip().lower()
        if not ref:
            return ResultadoResolucion(
                exito=False,
                es_ambiguo=False,
                motivo="La referencia de clase no puede estar vacía.",
            )

        # 1. Alias o mapa en memoria previo
        if mapa_alias and ref in mapa_alias:
            return ResultadoResolucion(exito=True, id=mapa_alias[ref])

        # 2. Búsqueda por UUID directo
        for c in clases:
            if str(getattr(c, "id", "")).lower() == ref:
                return ResultadoResolucion(exito=True, id=c.id)

        # 3. Búsqueda por nombre de clase exacto
        coincidencias = [c for c in clases if getattr(c, "nombre", "").strip().lower() == ref]

        if len(coincidencias) == 1:
            return ResultadoResolucion(exito=True, id=coincidencias[0].id)
        if len(coincidencias) > 1:
            return ResultadoResolucion(
                exito=False,
                es_ambiguo=True,
                motivo=f"Existen múltiples clases con el nombre '{referencia}'. Se requiere aclaración.",
            )

        return ResultadoResolucion(
            exito=False,
            es_ambiguo=False,
            motivo=f"No se encontró la clase '{referencia}' en el diagrama.",
        )

    @classmethod
    def resolver_atributo(
        cls,
        referencia_clase: str | None,
        referencia_atributo: str,
        clases: list[Any],
        mapa_alias: dict[str, UUID] | None = None,
    ) -> ResultadoResolucion:
        ref_attr = referencia_atributo.strip().lower()
        if not ref_attr:
            return ResultadoResolucion(
                exito=False,
                es_ambiguo=False,
                motivo="La referencia de atributo no puede estar vacía.",
            )

        if referencia_clase and referencia_clase.strip():
            res_clase = cls.resolver_clase(referencia_clase, clases, mapa_alias)
            if not res_clase.exito:
                return res_clase

            id_clase = res_clase.id
            clase_obj = next((c for c in clases if c.id == id_clase), None)
            if not clase_obj:
                return ResultadoResolucion(
                    exito=False,
                    es_ambiguo=False,
                    motivo=f"No se encontró la clase '{referencia_clase}'.",
                )

            attrs = getattr(clase_obj, "atributos", [])
            # Coincidencia por id
            for a in attrs:
                if str(getattr(a, "id", "")).lower() == ref_attr:
                    return ResultadoResolucion(
                        exito=True,
                        id=a.id,
                        metadatos={"id_clase": id_clase, "procedencia": getattr(a, "procedencia", None)},
                    )

            # Coincidencia por nombre
            coincidencias = [a for a in attrs if getattr(a, "nombre", "").strip().lower() == ref_attr]
            if len(coincidencias) == 1:
                return ResultadoResolucion(
                    exito=True,
                    id=coincidencias[0].id,
                    metadatos={"id_clase": id_clase, "procedencia": getattr(coincidencias[0], "procedencia", None)},
                )
            if len(coincidencias) > 1:
                return ResultadoResolucion(
                    exito=False,
                    es_ambiguo=True,
                    motivo=f"Existen múltiples atributos con el nombre '{referencia_atributo}' en la clase '{clase_obj.nombre}'.",
                )

            return ResultadoResolucion(
                exito=False,
                es_ambiguo=False,
                motivo=f"No se encontró el atributo '{referencia_atributo}' en la clase '{clase_obj.nombre}'.",
            )

        # Si no se especifica la clase, buscar en todo el diagrama
        hallazgos: list[tuple[Any, Any]] = []
        for c in clases:
            for a in getattr(c, "atributos", []):
                if getattr(a, "nombre", "").strip().lower() == ref_attr or str(getattr(a, "id", "")).lower() == ref_attr:
                    hallazgos.append((c, a))

        if len(hallazgos) == 1:
            clase_obj, attr_obj = hallazgos[0]
            return ResultadoResolucion(
                exito=True,
                id=attr_obj.id,
                metadatos={"id_clase": clase_obj.id, "procedencia": getattr(attr_obj, "procedencia", None)},
            )
        if len(hallazgos) > 1:
            clases_nombres = ", ".join(repr(c.nombre) for c, _ in hallazgos)
            return ResultadoResolucion(
                exito=False,
                es_ambiguo=True,
                motivo=f"El atributo '{referencia_atributo}' existe en múltiples clases ({clases_nombres}). Por favor indica de qué clase deseas operarlo.",
            )

        return ResultadoResolucion(
            exito=False,
            es_ambiguo=False,
            motivo=f"No se encontró el atributo '{referencia_atributo}' en ninguna clase del diagrama.",
        )

    @classmethod
    def resolver_relacion(
        cls,
        referencia_origen: str,
        referencia_destino: str,
        relaciones: list[Any],
        clases: list[Any],
        nombre_relacion: str | None = None,
        mapa_alias: dict[str, UUID] | None = None,
    ) -> ResultadoResolucion:
        res_orig = cls.resolver_clase(referencia_origen, clases, mapa_alias)
        if not res_orig.exito:
            return res_orig

        res_dest = cls.resolver_clase(referencia_destino, clases, mapa_alias)
        if not res_dest.exito:
            return res_dest

        orig_id = res_orig.id
        dest_id = res_dest.id

        coincidencias = []
        for r in relaciones:
            c_orig = getattr(r, "id_clase_origen", None)
            c_dest = getattr(r, "id_clase_destino", None)
            es_par = (c_orig == orig_id and c_dest == dest_id) or (c_orig == dest_id and c_dest == orig_id)
            if es_par:
                if nombre_relacion and nombre_relacion.strip():
                    if getattr(r, "nombre", "").strip().lower() == nombre_relacion.strip().lower():
                        coincidencias.append(r)
                else:
                    coincidencias.append(r)

        if len(coincidencias) == 1:
            return ResultadoResolucion(exito=True, id=coincidencias[0].id)
        if len(coincidencias) > 1:
            return ResultadoResolucion(
                exito=False,
                es_ambiguo=True,
                motivo=f"Existen múltiples relaciones entre '{referencia_origen}' y '{referencia_destino}'. Por favor especifica el nombre de la relación.",
            )

        return ResultadoResolucion(
            exito=False,
            es_ambiguo=False,
            motivo=f"No se encontró ninguna relación entre '{referencia_origen}' y '{referencia_destino}'.",
        )

    @classmethod
    def resolver_estructura_nm(
        cls,
        referencia_origen: str,
        referencia_destino: str,
        estructuras_nm: list[Any],
        clases: list[Any],
        mapa_alias: dict[str, UUID] | None = None,
    ) -> ResultadoResolucion:
        res_orig = cls.resolver_clase(referencia_origen, clases, mapa_alias)
        if not res_orig.exito:
            return res_orig

        res_dest = cls.resolver_clase(referencia_destino, clases, mapa_alias)
        if not res_dest.exito:
            return res_dest

        orig_id = res_orig.id
        dest_id = res_dest.id

        coincidencias = [
            s for s in estructuras_nm
            if (s.id_clase_origen == orig_id and s.id_clase_destino == dest_id)
            or (s.id_clase_origen == dest_id and s.id_clase_destino == orig_id)
        ]

        if len(coincidencias) == 1:
            return ResultadoResolucion(exito=True, id=coincidencias[0].id)
        if len(coincidencias) > 1:
            return ResultadoResolucion(
                exito=False,
                es_ambiguo=True,
                motivo=f"Existen múltiples estructuras N:M entre '{referencia_origen}' y '{referencia_destino}'.",
            )

        return ResultadoResolucion(
            exito=False,
            es_ambiguo=False,
            motivo=f"No se encontró estructura N:M entre '{referencia_origen}' y '{referencia_destino}'.",
        )
