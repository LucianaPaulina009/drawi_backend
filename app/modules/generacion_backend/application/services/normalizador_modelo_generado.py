from __future__ import annotations

import re
from uuid import UUID

from app.modules.generacion_backend.application.dtos.diagrama_generable_dto import (
    AtributoGenerable,
    ClaseGenerable,
    DiagramaGenerable,
    RelacionGenerable,
)
from app.modules.generacion_backend.application.dtos.modelo_spring_dto import (
    AsociacionSpring,
    CampoSpring,
    EntidadSpring,
    ProyectoSpring,
)


def a_pascal_case(nombre: str) -> str:
    limpio = re.sub(r"[^a-zA-Z0-9_]", "_", nombre.strip())
    partes = [p for p in re.split(r"_+", limpio) if p]
    if not partes:
        return "Clase"
    return "".join(p[0].upper() + p[1:] if len(p) > 1 else p.upper() for p in partes)


def a_camel_case(nombre: str) -> str:
    pascal = a_pascal_case(nombre)
    if not pascal:
        return "campo"
    return pascal[0].lower() + pascal[1:]


def a_snake_case(nombre: str) -> str:
    limpio = re.sub(r"[^a-zA-Z0-9_]", "_", nombre.strip())
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", limpio)
    s2 = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()
    return re.sub(r"_+", "_", s2).strip("_")


def a_kebab_case(nombre: str) -> str:
    snake = a_snake_case(nombre)
    return snake.replace("_", "-")


class NormalizadorModeloGenerado:
    """Transforma un DiagramaGenerable validado en un ProyectoSpring normalizado para renderizado."""

    def normalizar(
        self,
        diagrama: DiagramaGenerable,
        version_plantilla: str = "1.0.0",
        package_base: str = "com.drawi.app",
    ) -> ProyectoSpring:
        slug_proyecto = a_kebab_case(diagrama.nombre or "backend-app")
        if not slug_proyecto:
            slug_proyecto = "drawi-backend"

        package_path = package_base.replace(".", "/")

        entidades: list[EntidadSpring] = []
        clases_map: dict[UUID, ClaseGenerable] = {c.id: c for c in diagrama.clases}

        for clase in diagrama.clases:
            entidad = self._normalizar_clase(clase)
            entidades.append(entidad)

        # Mapear relaciones entre entidades
        entidades_por_id = {e.id: e for e in entidades}
        self._mapear_relaciones(diagrama.relaciones, entidades_por_id, clases_map)

        return ProyectoSpring(
            nombre_proyecto=diagrama.nombre or "drawi-backend",
            slug=slug_proyecto,
            package_name=package_base,
            package_path=package_path,
            version_plantilla=version_plantilla,
            java_version="17",
            spring_boot_version="3.3.4",
            entidades=entidades,
        )

    def _normalizar_clase(self, clase: ClaseGenerable) -> EntidadSpring:
        nombre_clase = a_pascal_case(clase.nombre)
        nombre_camel = a_camel_case(clase.nombre)
        nombre_tabla = a_snake_case(clase.nombre)
        endpoint_path = a_kebab_case(clase.nombre)

        campos: list[CampoSpring] = []
        pk_campo: CampoSpring | None = None

        necesita_bigdecimal = False
        necesita_localdate = False
        necesita_localdatetime = False
        necesita_uuid = False

        for attr in clase.atributos:
            campo = self._normalizar_atributo(attr)
            campos.append(campo)
            if campo.es_pk and pk_campo is None:
                pk_campo = campo

            if campo.tipo_java == "BigDecimal":
                necesita_bigdecimal = True
            elif campo.tipo_java == "LocalDate":
                necesita_localdate = True
            elif campo.tipo_java == "LocalDateTime":
                necesita_localdatetime = True
            elif campo.tipo_java == "UUID":
                necesita_uuid = True

        if pk_campo is None and campos:
            # Fallback seguro: primer campo como PK
            pk_campo = campos[0]

        return EntidadSpring(
            id=clase.id,
            nombre_clase=nombre_clase,
            nombre_camel=nombre_camel,
            nombre_tabla=nombre_tabla,
            endpoint_path=endpoint_path,
            campos=campos,
            pk=pk_campo,  # type: ignore
            asociaciones=[],
            necesita_bigdecimal=necesita_bigdecimal,
            necesita_localdate=necesita_localdate,
            necesita_localdatetime=necesita_localdatetime,
            necesita_uuid=necesita_uuid,
        )

    def _normalizar_atributo(self, attr: AtributoGenerable) -> CampoSpring:
        nombre_java = a_camel_case(attr.nombre)
        nombre_sql = a_snake_case(attr.nombre)
        pascal = a_pascal_case(attr.nombre)
        nombre_getter = f"get{pascal}"
        nombre_setter = f"set{pascal}"

        tipo_normalizado = (attr.tipo_dato or "").strip().lower()

        if tipo_normalizado == "integer":
            tipo_java = "Integer"
            tipo_sql = "integer"
        elif tipo_normalizado == "bigint":
            tipo_java = "Long"
            tipo_sql = "bigint"
        elif tipo_normalizado == "varchar":
            tipo_java = "String"
            longitud = attr.longitud if attr.longitud and attr.longitud > 0 else 255
            tipo_sql = f"varchar({longitud})"
        elif tipo_normalizado == "text":
            tipo_java = "String"
            tipo_sql = "text"
        elif tipo_normalizado == "decimal":
            tipo_java = "BigDecimal"
            p = attr.precision or 10
            e = attr.escala or 2
            tipo_sql = f"numeric({p},{e})"
        elif tipo_normalizado == "boolean":
            tipo_java = "Boolean"
            tipo_sql = "boolean"
        elif tipo_normalizado == "date":
            tipo_java = "LocalDate"
            tipo_sql = "date"
        elif tipo_normalizado == "timestamp":
            tipo_java = "LocalDateTime"
            tipo_sql = "timestamp"
        else:
            tipo_java = "String"
            tipo_sql = "varchar(255)"

        return CampoSpring(
            id=attr.id,
            nombre_java=nombre_java,
            nombre_getter=nombre_getter,
            nombre_setter=nombre_setter,
            nombre_sql=nombre_sql,
            tipo_java=tipo_java,
            tipo_sql=tipo_sql,
            es_pk=attr.es_llave_primaria,
            permite_nulo=attr.permite_nulo,
            es_unico=attr.es_unico,
            valor_por_defecto=attr.valor_por_defecto,
            longitud=attr.longitud,
            precision=attr.precision,
            escala=attr.escala,
        )

    def _mapear_relaciones(
        self,
        relaciones: tuple[RelacionGenerable, ...],
        entidades_por_id: dict[UUID, EntidadSpring],
        clases_map: dict[UUID, ClaseGenerable],
    ) -> None:
        for r in relaciones:
            if r.id_clase_origen not in entidades_por_id or r.id_clase_destino not in entidades_por_id:
                continue

            entidad_origen = entidades_por_id[r.id_clase_origen]
            entidad_destino = entidades_por_id[r.id_clase_destino]

            tipo = (r.tipo_relacion or "").lower()
            card_orig = r.cardinalidad_origen or "1"
            card_dest = r.cardinalidad_destino or "1"

            # Determinar asociación JPA
            # Si destino es muchos (*, 1..*) y origen es 1 (1, 0..1):
            # entidad_origen tiene OneToMany hacia entidad_destino
            # entidad_destino tiene ManyToOne hacia entidad_origen
            if card_dest in {"*", "0..*", "1..*", "N"} and card_orig in {"1", "0..1"}:
                campo_fk_sql = f"id_{entidad_origen.nombre_tabla}"
                if r.referencias_fk:
                    # Usar columna FK de la referencia si existe
                    ref = r.referencias_fk[0]
                    attr_fk = next((a for a in clases_map[r.id_clase_destino].atributos if a.id == ref.id_atributo_fk), None)
                    if attr_fk:
                        campo_fk_sql = a_snake_case(attr_fk.nombre)

                nombre_asoc_dest = a_camel_case(entidad_origen.nombre_clase)
                asoc_many_to_one = AsociacionSpring(
                    tipo="MANY_TO_ONE",
                    nombre_campo=nombre_asoc_dest,
                    nombre_getter=f"get{a_pascal_case(nombre_asoc_dest)}",
                    nombre_setter=f"set{a_pascal_case(nombre_asoc_dest)}",
                    entidad_destino=entidad_origen.nombre_clase,
                    columna_fk_sql=campo_fk_sql,
                )
                entidad_destino.asociaciones.append(asoc_many_to_one)

            elif card_orig in {"*", "0..*", "1..*", "N"} and card_dest in {"1", "0..1"}:
                campo_fk_sql = f"id_{entidad_destino.nombre_tabla}"
                if r.referencias_fk:
                    ref = r.referencias_fk[0]
                    attr_fk = next((a for a in clases_map[r.id_clase_origen].atributos if a.id == ref.id_atributo_fk), None)
                    if attr_fk:
                        campo_fk_sql = a_snake_case(attr_fk.nombre)

                nombre_asoc_orig = a_camel_case(entidad_destino.nombre_clase)
                asoc_many_to_one = AsociacionSpring(
                    tipo="MANY_TO_ONE",
                    nombre_campo=nombre_asoc_orig,
                    nombre_getter=f"get{a_pascal_case(nombre_asoc_orig)}",
                    nombre_setter=f"set{a_pascal_case(nombre_asoc_orig)}",
                    entidad_destino=entidad_destino.nombre_clase,
                    columna_fk_sql=campo_fk_sql,
                )
                entidad_origen.asociaciones.append(asoc_many_to_one)
