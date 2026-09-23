from __future__ import annotations

import re
from uuid import UUID

from app.modules.generacion_backend.application.dtos.diagrama_generable_dto import (
    DiagramaGenerable,
)
from app.modules.generacion_backend.application.dtos.diagnostico_generacion_dto import (
    DiagnosticoGeneracion,
    ErrorGeneracion,
)

TIPOS_DATOS_VALIDOS = {
    "integer",
    "bigint",
    "varchar",
    "text",
    "decimal",
    "boolean",
    "date",
    "timestamp",
}

JAVA_KEYWORDS = {
    "abstract", "assert", "boolean", "break", "byte", "case", "catch", "char",
    "class", "const", "continue", "default", "do", "double", "else", "enum",
    "extends", "final", "finally", "float", "for", "goto", "if", "implements",
    "import", "instanceof", "int", "interface", "long", "native", "new",
    "package", "private", "protected", "public", "return", "short", "static",
    "strictfp", "super", "switch", "synchronized", "this", "throw", "throws",
    "transient", "try", "void", "volatile", "while", "record", "yield",
    "sealed", "non-sealed", "permits",
}

RE_IDENTIFIER = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


def a_pascal_case(nombre: str) -> str:
    limpio = re.sub(r"[^a-zA-Z0-9_]", "_", nombre.strip())
    partes = [p for p in re.split(r"_+", limpio) if p]
    if not partes:
        return ""
    return "".join(p[0].upper() + p[1:] if len(p) > 1 else p.upper() for p in partes)


def a_camel_case(nombre: str) -> str:
    pascal = a_pascal_case(nombre)
    if not pascal:
        return ""
    return pascal[0].lower() + pascal[1:]


class ValidadorDiagramaGenerable:
    """Valida que un snapshot DiagramaGenerable sea transformable a un proyecto backend Spring Boot."""

    def validar(self, diagrama: DiagramaGenerable) -> DiagnosticoGeneracion:
        diagnostico = DiagnosticoGeneracion.exitoso()

        # Regla 1: Diagrama no vacío
        if not diagrama.clases:
            diagnostico.agregar_error(
                ErrorGeneracion(
                    codigo="DIAGRAMA_VACIO",
                    mensaje="El diagrama no contiene clases. Debe contener al menos una clase.",
                    elemento_tipo="diagrama",
                    elemento=diagrama.nombre or "Diagrama",
                    elemento_id=str(diagrama.id),
                )
            )
            return diagnostico

        clases_por_id = {c.id: c for c in diagrama.clases}
        nombres_clases_normalizados: dict[str, UUID] = {}

        # Regla 2, 3, 4: Validaciones por clase y atributos
        for clase in diagrama.clases:
            # Validación nombre clase
            if not clase.nombre or not clase.nombre.strip():
                diagnostico.agregar_error(
                    ErrorGeneracion(
                        codigo="CLASE_NOMBRE_VACIO",
                        mensaje="La clase tiene un nombre vacío.",
                        elemento_tipo="clase",
                        elemento="Clase sin nombre",
                        elemento_id=str(clase.id),
                    )
                )
                continue

            nombre_normalizado = a_pascal_case(clase.nombre)
            if not nombre_normalizado or not RE_IDENTIFIER.match(nombre_normalizado):
                diagnostico.agregar_error(
                    ErrorGeneracion(
                        codigo="CLASE_NOMBRE_INVALIDO",
                        mensaje=f"El nombre de clase '{clase.nombre}' no produce un identificador Java válido.",
                        elemento_tipo="clase",
                        elemento=clase.nombre,
                        elemento_id=str(clase.id),
                    )
                )
            elif nombre_normalizado.lower() in JAVA_KEYWORDS:
                diagnostico.agregar_error(
                    ErrorGeneracion(
                        codigo="CLASE_PALABRA_RESERVADA",
                        mensaje=f"El nombre de clase '{clase.nombre}' coincide con una palabra reservada de Java.",
                        elemento_tipo="clase",
                        elemento=clase.nombre,
                        elemento_id=str(clase.id),
                    )
                )

            if nombre_normalizado in nombres_clases_normalizados:
                diagnostico.agregar_error(
                    ErrorGeneracion(
                        codigo="CLASE_NOMBRE_DUPLICADO",
                        mensaje=f"Existe más de una clase con el nombre normalizado '{nombre_normalizado}'.",
                        elemento_tipo="clase",
                        elemento=clase.nombre,
                        elemento_id=str(clase.id),
                    )
                )
            else:
                nombres_clases_normalizados[nombre_normalizado] = clase.id

            # Validar atributos de la clase
            if not clase.atributos:
                diagnostico.agregar_error(
                    ErrorGeneracion(
                        codigo="CLASE_SIN_ATRIBUTOS",
                        mensaje=f"La clase '{clase.nombre}' no tiene atributos definidos.",
                        elemento_tipo="clase",
                        elemento=clase.nombre,
                        elemento_id=str(clase.id),
                    )
                )
                continue

            nombres_atributos_normalizados: dict[str, UUID] = {}
            pks_encontradas = []

            for atributo in clase.atributos:
                # Nombre atributo
                if not atributo.nombre or not atributo.nombre.strip():
                    diagnostico.agregar_error(
                        ErrorGeneracion(
                            codigo="ATRIBUTO_NOMBRE_VACIO",
                            mensaje=f"Un atributo en la clase '{clase.nombre}' tiene nombre vacío.",
                            elemento_tipo="atributo",
                            elemento=f"{clase.nombre}.(sin nombre)",
                            elemento_id=str(atributo.id),
                        )
                    )
                    continue

                attr_normalizado = a_camel_case(atributo.nombre)
                if not attr_normalizado or not RE_IDENTIFIER.match(attr_normalizado):
                    diagnostico.agregar_error(
                        ErrorGeneracion(
                            codigo="ATRIBUTO_NOMBRE_INVALIDO",
                            mensaje=f"El atributo '{atributo.nombre}' de la clase '{clase.nombre}' no produce un identificador válido.",
                            elemento_tipo="atributo",
                            elemento=f"{clase.nombre}.{atributo.nombre}",
                            elemento_id=str(atributo.id),
                        )
                    )
                elif attr_normalizado.lower() in JAVA_KEYWORDS:
                    diagnostico.agregar_error(
                        ErrorGeneracion(
                            codigo="ATRIBUTO_PALABRA_RESERVADA",
                            mensaje=f"El atributo '{atributo.nombre}' de la clase '{clase.nombre}' es palabra reservada Java.",
                            elemento_tipo="atributo",
                            elemento=f"{clase.nombre}.{atributo.nombre}",
                            elemento_id=str(atributo.id),
                        )
                    )

                if attr_normalizado in nombres_atributos_normalizados:
                    diagnostico.agregar_error(
                        ErrorGeneracion(
                            codigo="ATRIBUTO_NOMBRE_DUPLICADO",
                            mensaje=f"El atributo normalizado '{attr_normalizado}' está duplicado en la clase '{clase.nombre}'.",
                            elemento_tipo="atributo",
                            elemento=f"{clase.nombre}.{atributo.nombre}",
                            elemento_id=str(atributo.id),
                        )
                    )
                else:
                    nombres_atributos_normalizados[attr_normalizado] = atributo.id

                # Regla 3: Tipos de dato válidos y límites
                tipo_normalizado = (atributo.tipo_dato or "").strip().lower()
                if tipo_normalizado not in TIPOS_DATOS_VALIDOS:
                    diagnostico.agregar_error(
                        ErrorGeneracion(
                            codigo="TIPO_DATO_NO_SOPORTADO",
                            mensaje=f"El atributo '{atributo.nombre}' tiene un tipo de dato no soportado: '{atributo.tipo_dato}'.",
                            elemento_tipo="atributo",
                            elemento=f"{clase.nombre}.{atributo.nombre}",
                            elemento_id=str(atributo.id),
                        )
                    )
                else:
                    if tipo_normalizado == "varchar" and atributo.longitud is not None:
                        if atributo.longitud <= 0 or atributo.longitud > 65535:
                            diagnostico.agregar_error(
                                ErrorGeneracion(
                                    codigo="VARCHAR_LONGITUD_INVALIDA",
                                    mensaje=f"El atributo '{atributo.nombre}' tiene una longitud varchar inválida ({atributo.longitud}).",
                                    elemento_tipo="atributo",
                                    elemento=f"{clase.nombre}.{atributo.nombre}",
                                    elemento_id=str(atributo.id),
                                )
                            )
                    elif tipo_normalizado == "decimal":
                        if atributo.precision is not None and atributo.precision <= 0:
                            diagnostico.agregar_error(
                                ErrorGeneracion(
                                    codigo="DECIMAL_PRECISION_INVALIDA",
                                    mensaje=f"El atributo '{atributo.nombre}' tiene precisión decimal inválida ({atributo.precision}).",
                                    elemento_tipo="atributo",
                                    elemento=f"{clase.nombre}.{atributo.nombre}",
                                    elemento_id=str(atributo.id),
                                )
                            )
                        if (
                            atributo.precision is not None
                            and atributo.escala is not None
                            and (atributo.escala < 0 or atributo.escala > atributo.precision)
                        ):
                            diagnostico.agregar_error(
                                ErrorGeneracion(
                                    codigo="DECIMAL_ESCALA_INVALIDA",
                                    mensaje=f"El atributo '{atributo.nombre}' tiene escala decimal mayor que su precisión ({atributo.escala} > {atributo.precision}).",
                                    elemento_tipo="atributo",
                                    elemento=f"{clase.nombre}.{atributo.nombre}",
                                    elemento_id=str(atributo.id),
                                )
                            )

                # Regla 4: PK canónica
                if atributo.es_llave_primaria:
                    pks_encontradas.append(atributo)
                    if atributo.permite_nulo:
                        diagnostico.agregar_error(
                            ErrorGeneracion(
                                codigo="PK_NULLABLE",
                                mensaje=f"La clave primaria '{atributo.nombre}' en la clase '{clase.nombre}' no puede permitir valores nulos.",
                                elemento_tipo="atributo",
                                elemento=f"{clase.nombre}.{atributo.nombre}",
                                elemento_id=str(atributo.id),
                            )
                        )

            if len(pks_encontradas) == 0:
                diagnostico.agregar_error(
                    ErrorGeneracion(
                        codigo="CLASE_SIN_PK",
                        mensaje=f"La clase '{clase.nombre}' no tiene una clave primaria (PK) definida.",
                        elemento_tipo="clase",
                        elemento=clase.nombre,
                        elemento_id=str(clase.id),
                    )
                )

        # Mapeo de atributos global para validar FKs
        atributos_por_id = {}
        for c in diagrama.clases:
            for a in c.atributos:
                atributos_por_id[a.id] = (c, a)

        # Regla 5 y 6: Validación de Relaciones y Referencias FK
        for relacion in diagrama.relaciones:
            clase_orig = clases_por_id.get(relacion.id_clase_origen)
            clase_dest = clases_por_id.get(relacion.id_clase_destino)
            desc_rel = (
                f"{clase_orig.nombre} - {clase_dest.nombre}"
                if clase_orig and clase_dest
                else f"Relación {relacion.id}"
            )

            if relacion.id_clase_origen not in clases_por_id:
                diagnostico.agregar_error(
                    ErrorGeneracion(
                        codigo="RELACION_CLASE_ORIGEN_INEXISTENTE",
                        mensaje=f"La relación '{relacion.id}' apunta a una clase origen inexistente en el diagrama.",
                        elemento_tipo="relacion",
                        elemento=desc_rel,
                        elemento_id=str(relacion.id),
                    )
                )
                continue

            if relacion.id_clase_destino not in clases_por_id:
                diagnostico.agregar_error(
                    ErrorGeneracion(
                        codigo="RELACION_CLASE_DESTINO_INEXISTENTE",
                        mensaje=f"La relación '{relacion.id}' apunta a una clase destino inexistente en el diagrama.",
                        elemento_tipo="relacion",
                        elemento=desc_rel,
                        elemento_id=str(relacion.id),
                    )
                )
                continue

            # Validar referencias FK de la relación
            for rf in relacion.referencias_fk:
                if rf.id_atributo_fk not in atributos_por_id:
                    diagnostico.agregar_error(
                        ErrorGeneracion(
                            codigo="FK_ATRIBUTO_INEXISTENTE",
                            mensaje="La referencia FK apunta a un atributo local inexistente.",
                            elemento_tipo="referencia_fk",
                            elemento=desc_rel,
                            elemento_id=str(rf.id),
                        )
                    )
                    continue

                if rf.id_atributo_referenciado not in atributos_por_id:
                    diagnostico.agregar_error(
                        ErrorGeneracion(
                            codigo="FK_REFERENCIADO_INEXISTENTE",
                            mensaje="La referencia FK apunta a un atributo referenciado inexistente.",
                            elemento_tipo="referencia_fk",
                            elemento=desc_rel,
                            elemento_id=str(rf.id),
                        )
                    )
                    continue

                clase_fk, attr_fk = atributos_por_id[rf.id_atributo_fk]
                clase_ref, attr_ref = atributos_por_id[rf.id_atributo_referenciado]

                # Validar compatibilidad de tipos FK
                tipo_fk = (attr_fk.tipo_dato or "").strip().lower()
                tipo_ref = (attr_ref.tipo_dato or "").strip().lower()
                if tipo_fk != tipo_ref:
                    diagnostico.agregar_error(
                        ErrorGeneracion(
                            codigo="FK_TIPOS_INCOMPATIBLES",
                            mensaje=f"La relación {desc_rel} tiene una FK inconsistente: '{attr_fk.nombre}' ({tipo_fk}) y '{attr_ref.nombre}' ({tipo_ref}) tienen tipos incompatibles.",
                            elemento_tipo="referencia_fk",
                            elemento=f"{clase_fk.nombre}.{attr_fk.nombre} -> {clase_ref.nombre}.{attr_ref.nombre}",
                            elemento_id=str(rf.id),
                        )
                    )

        # Regla 7: Validar estructuras N:M
        for nm in diagrama.estructuras_nm:
            clase_inter = clases_por_id.get(nm.id_clase_intermedia)
            desc_nm = clase_inter.nombre if clase_inter else f"Estructura N:M {nm.id}"

            if nm.id_clase_intermedia not in clases_por_id:
                diagnostico.agregar_error(
                    ErrorGeneracion(
                        codigo="NM_CLASE_INTERMEDIA_INEXISTENTE",
                        mensaje="La estructura N:M referencia una clase intermedia que no existe en el diagrama.",
                        elemento_tipo="estructura_nm",
                        elemento=desc_nm,
                        elemento_id=str(nm.id),
                    )
                )
            if nm.id_clase_origen not in clases_por_id or nm.id_clase_destino not in clases_por_id:
                diagnostico.agregar_error(
                    ErrorGeneracion(
                        codigo="NM_CLASES_EXTREMOS_INEXISTENTES",
                        mensaje="La estructura N:M referencia clases en los extremos que no existen.",
                        elemento_tipo="estructura_nm",
                        elemento=desc_nm,
                        elemento_id=str(nm.id),
                    )
                )

        return diagnostico
