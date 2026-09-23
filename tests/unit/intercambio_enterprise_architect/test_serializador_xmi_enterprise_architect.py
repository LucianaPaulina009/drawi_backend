from __future__ import annotations

import xml.etree.ElementTree as ET
from uuid import uuid4

from app.modules.diagramas.application.queries.dtos import (
    AtributoDTO,
    ClaseDetalleDTO,
    DiagramaDetalleDTO,
)
from app.modules.intercambio_enterprise_architect.application.services.serializador_xmi_enterprise_architect import (
    SerializadorXmiEnterpriseArchitect,
)


def test_serializar_diagrama_basico_con_clases_y_geometria():
    diagrama_id = uuid4()
    clase1_id = uuid4()
    clase2_id = uuid4()
    attr1_id = uuid4()
    attr2_id = uuid4()

    diagrama_dto = DiagramaDetalleDTO(
        id=diagrama_id,
        id_proyecto=uuid4(),
        nombre="Diagrama de Ventas",
        numero=1,
        clases=(
            ClaseDetalleDTO(
                id=clase1_id,
                id_diagrama=diagrama_id,
                nombre="Producto",
                posicion_x=150.0,
                posicion_y=200.0,
                ancho=280.0,
                atributos=(
                    AtributoDTO(
                        id=attr1_id,
                        id_clase=clase1_id,
                        nombre="id",
                        tipo_dato="integer",
                        longitud=None,
                        precision=None,
                        escala=None,
                        orden_de_posicion=1,
                        es_llave_primaria=True,
                        permite_nulo=False,
                        es_unico=True,
                        valor_por_defecto=None,
                        procedencia="sistema_clase",
                    ),
                    AtributoDTO(
                        id=attr2_id,
                        id_clase=clase1_id,
                        nombre="nombre",
                        tipo_dato="varchar",
                        longitud=100,
                        precision=None,
                        escala=None,
                        orden_de_posicion=2,
                        es_llave_primaria=False,
                        permite_nulo=False,
                        es_unico=False,
                        valor_por_defecto=None,
                        procedencia="usuario",
                    ),
                ),
            ),
            ClaseDetalleDTO(
                id=clase2_id,
                id_diagrama=diagrama_id,
                nombre="Categoria",
                posicion_x=500.0,
                posicion_y=200.0,
                ancho=280.0,
                atributos=(),
            ),
        ),
        relaciones=(),
        estructuras_nm=(),
    )

    xml_salida = SerializadorXmiEnterpriseArchitect.serializar(diagrama_dto)

    # Validar que sea XML parseable
    root = ET.fromstring(xml_salida)
    assert "XMI" in root.tag
    assert root.attrib.get("{http://schema.omg.org/spec/XMI/2.1}version") == "2.1"

    # Validar que contiene las clases
    clases_xml = [el for el in root.iter() if el.tag.endswith("packagedElement") and el.attrib.get("{http://schema.omg.org/spec/XMI/2.1}type") == "uml:Class"]
    nombres = [c.attrib.get("name") for c in clases_xml]
    assert "Producto" in nombres
    assert "Categoria" in nombres

    # Validar extensión de Enterprise Architect con geometría y paquete
    diagrams_xml = [el for el in root.iter() if el.tag == "diagram"]
    assert len(diagrams_xml) >= 1
    diagram = diagrams_xml[0]
    elements = diagram.findall(".//element")
    assert len(elements) == 2
    geometrias = [e.attrib.get("geometry") for e in elements]
    assert any("Left=150" in g and "Top=200" in g for g in geometrias)

    # Validar que el paquete esté definido en elements de xmi:Extension
    extension = [el for el in root.iter() if el.tag.endswith("Extension")][0]
    type_attr = "{http://schema.omg.org/spec/XMI/2.1}type"
    idref_attr = "{http://schema.omg.org/spec/XMI/2.1}idref"
    pkg_elements = [el for el in extension.findall(".//element") if el.attrib.get(type_attr) == "uml:Package"]
    assert len(pkg_elements) == 1
    assert pkg_elements[0].attrib.get("name") == "Diagrama de Ventas"
    assert pkg_elements[0].attrib.get(idref_attr).startswith("EAPK_")

    # Validar que el diagrama vincule al paquete correcto
    diag_model = diagram.find("model")
    assert diag_model is not None
    assert diag_model.attrib.get("package") == pkg_elements[0].attrib.get(idref_attr)
    assert diag_model.attrib.get("owner") == pkg_elements[0].attrib.get(idref_attr)

