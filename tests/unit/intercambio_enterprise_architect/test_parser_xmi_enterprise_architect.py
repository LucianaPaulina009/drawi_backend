from __future__ import annotations

import pytest
from app.modules.intercambio_enterprise_architect.application.services.parser_xmi_enterprise_architect import (
    ParserXmiEnterpriseArchitect,
)
from app.shared.domain.exceptions import ValidationException


def test_parsear_xml_ea_valido_con_clases_y_geometria():
    xml_content = """<?xml version="1.0" encoding="windows-1252"?>
<xmi:XMI xmi:version="2.1" xmlns:uml="http://schema.omg.org/spec/UML/2.1" xmlns:xmi="http://schema.omg.org/spec/XMI/2.1">
    <uml:Model xmi:type="uml:Model" name="EA_Model">
        <packagedElement xmi:type="uml:Package" xmi:id="EAPK_1" name="Modelo">
            <packagedElement xmi:type="uml:Class" xmi:id="EAID_CLASE_1" name="Cliente">
                <ownedAttribute xmi:type="uml:Property" xmi:id="EAID_ATTR_1" name="nombre">
                    <type xmi:type="uml:PrimitiveType" href="http://schema.omg.org/spec/UML/2.1/uml.xml#String"/>
                </ownedAttribute>
                <ownedAttribute xmi:type="uml:Property" xmi:id="EAID_ATTR_2" name="email">
                    <type xmi:type="uml:PrimitiveType" href="http://schema.omg.org/spec/UML/2.1/uml.xml#String"/>
                </ownedAttribute>
            </packagedElement>
            <packagedElement xmi:type="uml:Class" xmi:id="EAID_CLASE_2" name="Pedido">
                <ownedAttribute xmi:type="uml:Property" xmi:id="EAID_ATTR_3" name="fecha">
                    <type xmi:type="uml:PrimitiveType" href="http://schema.omg.org/spec/UML/2.1/uml.xml#Date"/>
                </ownedAttribute>
            </packagedElement>
            <packagedElement xmi:type="uml:Association" xmi:id="EAID_REL_1" name="realiza">
                <memberEnd xmi:idref="EAID_END_1"/>
                <memberEnd xmi:idref="EAID_END_2"/>
                <ownedEnd xmi:type="uml:Property" xmi:id="EAID_END_1" type="EAID_CLASE_1">
                    <lowerValue xmi:type="uml:LiteralInteger" value="1"/>
                    <upperValue xmi:type="uml:LiteralUnlimitedNatural" value="1"/>
                </ownedEnd>
                <ownedEnd xmi:type="uml:Property" xmi:id="EAID_END_2" type="EAID_CLASE_2">
                    <lowerValue xmi:type="uml:LiteralInteger" value="0"/>
                    <upperValue xmi:type="uml:LiteralUnlimitedNatural" value="*"/>
                </ownedEnd>
            </packagedElement>
        </packagedElement>
    </uml:Model>
    <xmi:Extension extender="Enterprise Architect" extenderID="6.5">
        <diagrams>
            <diagram xmi:id="EAID_DIAG_1">
                <elements>
                    <element geometry="Left=120;Top=150;Right=400;Bottom=300;" subject="EAID_CLASE_1"/>
                    <element geometry="Left=550;Top=150;Right=830;Bottom=300;" subject="EAID_CLASE_2"/>
                </elements>
            </diagram>
        </diagrams>
    </xmi:Extension>
</xmi:XMI>
"""
    clases, relaciones, advertencias = ParserXmiEnterpriseArchitect.parsear(xml_content)

    assert len(clases) == 2
    nombres = {c.nombre: c for c in clases}
    assert "Cliente" in nombres
    assert "Pedido" in nombres

    cliente = nombres["Cliente"]
    assert cliente.posicion_x == 120.0
    assert cliente.posicion_y == 150.0
    assert len(cliente.atributos) == 2
    nombres_attr = [a.nombre for a in cliente.atributos]
    assert "nombre" in nombres_attr
    assert "email" in nombres_attr

    assert len(relaciones) == 1
    rel = relaciones[0]
    assert rel.id_clase_origen_ea == "EAID_CLASE_1"
    assert rel.id_clase_destino_ea == "EAID_CLASE_2"
    assert rel.cardinalidad_origen == "1"
    assert rel.cardinalidad_destino == "0..*"


def test_parsear_xml_corrupto_lanza_excepcion_validacion():
    xml_corrupto = "<xmi:XMI><unclosed_tag>"
    with pytest.raises(ValidationException) as exc_info:
        ParserXmiEnterpriseArchitect.parsear(xml_corrupto)
    assert exc_info.value.code == "FORMATO_EA_INVALIDO"


def test_parsear_xml_sin_clases_retorna_vacio():
    xml_vacio = """<?xml version="1.0"?>
<xmi:XMI xmi:version="2.1" xmlns:uml="http://schema.omg.org/spec/UML/2.1" xmlns:xmi="http://schema.omg.org/spec/XMI/2.1">
    <uml:Model name="EmptyModel"/>
</xmi:XMI>
"""
    clases, relaciones, advertencias = ParserXmiEnterpriseArchitect.parsear(xml_vacio)
    assert len(clases) == 0
    assert len(relaciones) == 0
