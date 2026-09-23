from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from app.modules.intercambio_enterprise_architect.application.dtos.atributo_ea_dto import (
    AtributoEaDTO,
)
from app.modules.intercambio_enterprise_architect.application.dtos.clase_ea_dto import (
    ClaseEaDTO,
)
from app.modules.intercambio_enterprise_architect.application.dtos.relacion_ea_dto import (
    RelacionEaDTO,
)
from app.shared.domain.exceptions import ValidationException

logger = logging.getLogger(__name__)

MAX_XML_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


class ParserXmiEnterpriseArchitect:
    """Parsea documentos XML / XMI generados por Enterprise Architect de forma segura
    (protección anti-XXE) y extrae las clases, atributos, relaciones y posiciones geométricas.
    """

    @classmethod
    def parsear(cls, contenido_xml: str | bytes) -> tuple[list[ClaseEaDTO], list[RelacionEaDTO], list[str]]:
        if not contenido_xml:
            raise ValidationException("El archivo XML está vacío.", code="FORMATO_EA_INVALIDO")

        if isinstance(contenido_xml, str):
            xml_bytes = contenido_xml.encode("utf-8")
        else:
            xml_bytes = contenido_xml

        if len(xml_bytes) > MAX_XML_SIZE_BYTES:
            raise ValidationException(
                "El archivo supera el tamaño máximo permitido de 10 MB.",
                code="ARCHIVO_EXCEDE_TAMANO_MAXIMO",
            )

        # Protección anti-XXE estricta
        if b"<!ENTITY" in xml_bytes.upper() or b"<!DOCTYPE" in xml_bytes.upper():
            # Inspeccionar si intenta inyectar entidades externas
            if b"SYSTEM" in xml_bytes.upper() or b"PUBLIC" in xml_bytes.upper():
                raise ValidationException(
                    "El archivo contiene declaraciones de entidades externas no permitidas (XXE).",
                    code="FORMATO_EA_INVALIDO",
                )

        try:
            root = ET.fromstring(xml_bytes)
        except Exception as err:
            logger.warning("Error al parsear XML de Enterprise Architect: %s", str(err))
            raise ValidationException(
                f"El archivo no contiene un formato XML válido: {str(err)}",
                code="FORMATO_EA_INVALIDO",
            )

        advertencias: list[str] = []

        # 1. Extraer geometrías del diagrama si están presentes
        # Formato EA: <diagram><elements><element geometry="Left=100;Top=100;Right=380;Bottom=220;" subject="EAID_..."/>
        geometrias_por_subject: dict[str, tuple[float, float, float, float]] = {}
        for elem in root.iter():
            tag = cls._limpiar_tag(elem.tag)
            if tag == "element" and "geometry" in elem.attrib and "subject" in elem.attrib:
                subj = elem.attrib["subject"].strip()
                geom_str = elem.attrib["geometry"]
                coords = cls._parsear_geometria(geom_str)
                if coords:
                    geometrias_por_subject[subj] = coords

        # 2. Extraer Clases y Atributos
        clases: list[ClaseEaDTO] = []
        mapa_clases_por_id: dict[str, ClaseEaDTO] = {}

        for elem in root.iter():
            tag = cls._limpiar_tag(elem.tag)
            elem_type = cls._obtener_attr(elem, "type")

            # Clases en XMI 2.1: <packagedElement xmi:type="uml:Class" ...> o <element xmi:type="uml:Class">
            es_clase = (tag in ("packagedElement", "element") and elem_type.endswith("Class")) or (tag == "Class")

            if es_clase:
                clase_id = cls._obtener_attr(elem, "id") or cls._obtener_attr(elem, "idref")
                nombre_clase = (cls._obtener_attr(elem, "name") or "").strip()

                if not nombre_clase:
                    continue

                if clase_id and clase_id in mapa_clases_por_id:
                    continue

                pos_x, pos_y, ancho, alto = 200.0, 200.0, 280.0, 120.0
                if clase_id in geometrias_por_subject:
                    pos_x, pos_y, ancho, alto = geometrias_por_subject[clase_id]

                clase_dto = ClaseEaDTO(
                    id_ea=clase_id,
                    nombre=nombre_clase,
                    posicion_x=pos_x,
                    posicion_y=pos_y,
                    ancho=ancho,
                    alto=alto,
                    atributos=[],
                )

                # Extraer atributos de la clase
                for child in elem:
                    child_tag = cls._limpiar_tag(child.tag)
                    child_type = cls._obtener_attr(child, "type")

                    es_attr = (child_tag in ("ownedAttribute", "attribute") and (not child_type or child_type.endswith("Property"))) or (child_tag == "Property")

                    # Si es un extremo de asociación propiedad de la clase, ignorarlo como atributo
                    if cls._obtener_attr(child, "association"):
                        continue

                    if es_attr:
                        attr_id = cls._obtener_attr(child, "id")
                        raw_nombre = (cls._obtener_attr(child, "name") or "").strip()
                        if not raw_nombre:
                            continue

                        # Parsear nombre y tipo (ej: "nombre: varchar" o "precio: decimal" o "id")
                        nom_attr, tipo_attr = cls._interpretar_texto_atributo(raw_nombre, child)
                        es_pk = cls._detectar_si_es_pk(nom_attr, raw_nombre, child)

                        attr_dto = AtributoEaDTO(
                            id_ea=attr_id,
                            nombre=nom_attr,
                            tipo_dato=tipo_attr,
                            es_pk=es_pk,
                            texto_exportacion=raw_nombre,
                        )
                        clase_dto.atributos.append(attr_dto)

                clases.append(clase_dto)
                if clase_id:
                    mapa_clases_por_id[clase_id] = clase_dto

        # 3. Extraer Relaciones / Asociaciones
        relaciones: list[RelacionEaDTO] = []
        mapa_relaciones_por_id: set[str] = set()

        for elem in root.iter():
            tag = cls._limpiar_tag(elem.tag)
            elem_type = cls._obtener_attr(elem, "type")

            # Asociaciones en XMI
            es_assoc = (tag in ("packagedElement", "element") and elem_type.endswith("Association")) or (tag == "Association")
            es_gen = (tag == "generalization") or (tag in ("packagedElement", "element") and elem_type.endswith("Generalization"))

            if es_assoc:
                rel_id = cls._obtener_attr(elem, "id") or cls._obtener_attr(elem, "idref")
                if rel_id and rel_id in mapa_relaciones_por_id:
                    continue

                nombre_rel = (cls._obtener_attr(elem, "name") or "").strip() or None

                owned_ends = [
                    ch for ch in elem
                    if cls._limpiar_tag(ch.tag) in ("ownedEnd", "memberEnd")
                    and (cls._obtener_attr(ch, "type") or cls._obtener_attr(ch, "idref"))
                ]

                # Si tiene ownedEnds con extremos tipados
                orig_id, dest_id = None, None
                card_orig, card_dest = "1", "0..*"
                tipo_rel = "asociacion"

                ends_con_tipo = [e for e in owned_ends if cls._obtener_attr(e, "type")]
                if len(ends_con_tipo) >= 2:
                    end_a = ends_con_tipo[0]
                    end_b = ends_con_tipo[1]
                    orig_id = cls._obtener_attr(end_a, "type")
                    dest_id = cls._obtener_attr(end_b, "type")

                    # Agregación / Composición
                    agg_a = (cls._obtener_attr(end_a, "aggregation") or "none").lower()
                    agg_b = (cls._obtener_attr(end_b, "aggregation") or "none").lower()
                    if agg_a == "composite" or agg_b == "composite":
                        tipo_rel = "composicion"
                    elif agg_a == "shared" or agg_b == "shared":
                        tipo_rel = "agregacion"

                    card_orig = cls._extraer_cardinalidad_de_end(end_a, default="1")
                    card_dest = cls._extraer_cardinalidad_de_end(end_b, default="0..*")

                elif len(owned_ends) >= 2:
                    # Referencias cruzadas memberEnd
                    ref_a = cls._obtener_attr(owned_ends[0], "idref")
                    ref_b = cls._obtener_attr(owned_ends[1], "idref")
                    # Buscar elementos Property con esos IDs
                    prop_a = cls._buscar_por_id(root, ref_a)
                    prop_b = cls._buscar_por_id(root, ref_b)
                    if prop_a is not None and prop_b is not None:
                        orig_id = cls._obtener_attr(prop_a, "type")
                        dest_id = cls._obtener_attr(prop_b, "type")
                        card_orig = cls._extraer_cardinalidad_de_end(prop_a, default="1")
                        card_dest = cls._extraer_cardinalidad_de_end(prop_b, default="0..*")

                if orig_id and dest_id and orig_id in mapa_clases_por_id and dest_id in mapa_clases_por_id:
                    if rel_id:
                        mapa_relaciones_por_id.add(rel_id)
                    relaciones.append(
                        RelacionEaDTO(
                            id_ea=rel_id or f"EAID_R_{len(relaciones)+1}",
                            id_clase_origen_ea=orig_id,
                            id_clase_destino_ea=dest_id,
                            nombre=nombre_rel,
                            tipo_relacion=tipo_rel,
                            cardinalidad_origen=card_orig,
                            cardinalidad_destino=card_dest,
                        )
                    )

            elif es_gen:
                # Generalización (Herencia)
                rel_id = cls._obtener_attr(elem, "id") or cls._obtener_attr(elem, "idref")
                if rel_id and rel_id in mapa_relaciones_por_id:
                    continue

                general_id = cls._obtener_attr(elem, "general")
                # Si está dentro de una clase, el origen es la clase padre contenedora
                padre_clase = cls._encontrar_clase_contenedora(elem, root)
                if padre_clase and general_id:
                    if rel_id:
                        mapa_relaciones_por_id.add(rel_id)
                    relaciones.append(
                        RelacionEaDTO(
                            id_ea=rel_id or f"EAID_GEN_{len(relaciones)+1}",
                            id_clase_origen_ea=padre_clase,
                            id_clase_destino_ea=general_id,
                            nombre="herencia",
                            tipo_relacion="generalizacion",
                            cardinalidad_origen="1",
                            cardinalidad_destino="1",
                        )
                    )

        return clases, relaciones, advertencias

    @classmethod
    def _obtener_attr(cls, elem: ET.Element | None, attr_name: str) -> str:
        """Obtiene el valor de un atributo ignorando prefijos o namespaces (ej: 'type', 'id', 'name')."""
        if elem is None or not hasattr(elem, "attrib"):
            return ""
        if attr_name in elem.attrib:
            return elem.attrib[attr_name]
        for k, v in elem.attrib.items():
            if k == attr_name or k.endswith(f":{attr_name}"):
                return v
            if k.startswith("{") and "}" in k:
                local_name = k.split("}", 1)[1]
                if local_name == attr_name:
                    return v
        return ""

    @classmethod
    def _limpiar_tag(cls, raw_tag: str) -> str:
        if "}" in raw_tag:
            return raw_tag.split("}", 1)[1]
        return raw_tag

    @classmethod
    def _extraer_ns(cls, raw_tag: str) -> str:
        if raw_tag.startswith("{") and "}" in raw_tag:
            return raw_tag[1:].split("}", 1)[0]
        return ""

    @classmethod
    def _buscar_por_id(cls, root: ET.Element, target_id: str | None) -> ET.Element | None:
        if not target_id:
            return None
        for elem in root.iter():
            if cls._obtener_attr(elem, "id") == target_id:
                return elem
        return None

    @classmethod
    def _encontrar_clase_contenedora(cls, target_elem: ET.Element, root: ET.Element) -> str | None:
        # Búsqueda de padre navegando el árbol
        for elem in root.iter():
            tag = cls._limpiar_tag(elem.tag)
            elem_type = cls._obtener_attr(elem, "type")
            if tag == "Class" or (tag in ("packagedElement", "element") and elem_type.endswith("Class")):
                clase_id = cls._obtener_attr(elem, "id")
                for child in elem:
                    if child == target_elem:
                        return clase_id
        return None

    @classmethod
    def _parsear_geometria(cls, geom_str: str) -> tuple[float, float, float, float] | None:
        # Left=100;Top=100;Right=380;Bottom=220;
        try:
            m_left = re.search(r"Left=(-?\d+)", geom_str, re.IGNORECASE)
            m_top = re.search(r"Top=(-?\d+)", geom_str, re.IGNORECASE)
            m_right = re.search(r"Right=(-?\d+)", geom_str, re.IGNORECASE)
            m_bottom = re.search(r"Bottom=(-?\d+)", geom_str, re.IGNORECASE)
            if m_left and m_top:
                left = abs(float(m_left.group(1)))
                top = abs(float(m_top.group(1)))
                right = abs(float(m_right.group(1))) if m_right else left + 280.0
                bottom = abs(float(m_bottom.group(1))) if m_bottom else top + 120.0
                ancho = max(200.0, abs(right - left))
                alto = max(100.0, abs(bottom - top))
                return left, top, ancho, alto
        except Exception:
            pass
        return None

    @classmethod
    def _interpretar_texto_atributo(cls, raw_nombre: str, attr_elem: ET.Element) -> tuple[str, str]:
        texto = raw_nombre.strip()
        # Caso 1: nombre: tipo_de_dato
        if ":" in texto:
            partes = texto.split(":", 1)
            nom = partes[0].strip()
            tipo = partes[1].strip()
            return nom, tipo

        # Caso 2: Inspeccionar si tiene etiqueta <type> hija
        for ch in attr_elem:
            if cls._limpiar_tag(ch.tag) == "type":
                href = ch.attrib.get("href", "")
                if "#" in href:
                    uml_t = href.split("#", 1)[1].lower()
                    if uml_t == "integer":
                        return texto, "integer"
                    if uml_t == "boolean":
                        return texto, "boolean"
                type_name = ch.attrib.get("name")
                if type_name:
                    return texto, type_name.strip()

        # Caso 3: sin tipo explícito -> varchar
        return texto, "varchar"

    @classmethod
    def _detectar_si_es_pk(cls, nom_attr: str, raw_nombre: str, attr_elem: ET.Element) -> bool:
        t_lower = nom_attr.lower().strip()
        raw_lower = raw_nombre.lower().strip()
        if t_lower in {"id", "pk", "id_pk", "pk_id"}:
            return True
        if "[pk]" in raw_lower or "(pk)" in raw_lower or ": pk" in raw_lower:
            return True
        for ch in attr_elem.iter():
            if ch.attrib.get("value") == "PK" or ch.attrib.get("name") == "PK":
                return True
        return False

    @classmethod
    def _extraer_cardinalidad_de_end(cls, end_elem: ET.Element, default: str = "1") -> str:
        low = None
        up = None
        for ch in end_elem:
            tag = cls._limpiar_tag(ch.tag)
            if tag == "lowerValue":
                low = ch.attrib.get("value")
            elif tag == "upperValue":
                up = ch.attrib.get("value")

        if low is not None and up is not None:
            if low == "1" and up == "1":
                return "1"
            if low == "0" and up == "1":
                return "0..1"
            if (low == "0" or low is None) and up == "*":
                return "0..*"
            if low == "1" and up == "*":
                return "1..*"
            return f"{low}..{up}"
        elif up is not None:
            if up == "*":
                return "0..*"
            return up
        elif low is not None:
            return low
        return default
