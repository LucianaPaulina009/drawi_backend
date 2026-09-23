import datetime
import xml.etree.ElementTree as ET
from xml.dom import minidom
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.modules.diagramas.application.queries.dtos import (
        ClaseDetalleDTO,
        DiagramaDetalleDTO,
        RelacionDetalleDTO,
    )


class SerializadorXmiEnterpriseArchitect:
    """Serializa un DiagramaDetalleDTO a un documento XML estándar XMI 2.1
    compatible de forma nativa con Enterprise Architect, incluyendo la estructura
    lógica de paquetes, clases, atributos simplificados ('nombre: tipo'), conectores
    y el diagrama visual con geometrías y links.
    """

    @classmethod
    def serializar(cls, diagrama: DiagramaDetalleDTO) -> str:
        ahora_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        nom_diagrama = (diagrama.nombre or "Diagrama Principal").strip()

        # 1. Elemento raíz XMI
        root = ET.Element(
            "xmi:XMI",
            {
                "xmi:version": "2.1",
                "xmlns:uml": "http://schema.omg.org/spec/UML/2.1",
                "xmlns:xmi": "http://schema.omg.org/spec/XMI/2.1",
            },
        )

        # 2. Documentación del exportador
        ET.SubElement(
            root,
            "xmi:Documentation",
            {
                "exporter": "Enterprise Architect",
                "exporterVersion": "6.5",
            },
        )

        # 3. Modelo UML
        model = ET.SubElement(
            root,
            "uml:Model",
            {
                "xmi:type": "uml:Model",
                "name": "EA_Model",
                "visibility": "public",
            },
        )

        pkg_raw_id = str(diagrama.id).replace("-", "_").upper()
        pkg_id = f"EAPK_{pkg_raw_id}"
        pkg_eaid = f"EAID_{pkg_raw_id}"

        package = ET.SubElement(
            model,
            "packagedElement",
            {
                "xmi:type": "uml:Package",
                "xmi:id": pkg_id,
                "name": nom_diagrama,
                "visibility": "public",
            },
        )

        # Mapeo de IDs de DRAWI a IDs XMI
        mapa_xmi_clases: dict[str, str] = {}
        mapa_clases_dto: dict[str, ClaseDetalleDTO] = {}
        for c in diagrama.clases:
            c_str_id = str(c.id)
            mapa_xmi_clases[c_str_id] = f"EAID_{c_str_id.replace('-', '_').upper()}"
            mapa_clases_dto[c_str_id] = c

        # 4. Serializar Clases y Atributos en el modelo UML
        for c in diagrama.clases:
            clase_xmi_id = mapa_xmi_clases[str(c.id)]
            clase_elem = ET.SubElement(
                package,
                "packagedElement",
                {
                    "xmi:type": "uml:Class",
                    "xmi:id": clase_xmi_id,
                    "name": c.nombre,
                    "visibility": "public",
                },
            )

            for a in c.atributos:
                attr_xmi_id = f"EAID_ATTR_{str(a.id).replace('-', '_').upper()}"
                # Convención simplificada: nombre: tipo_de_dato
                texto_attr = f"{a.nombre}: {a.tipo_dato}"
                attr_elem = ET.SubElement(
                    clase_elem,
                    "ownedAttribute",
                    {
                        "xmi:type": "uml:Property",
                        "xmi:id": attr_xmi_id,
                        "name": texto_attr,
                        "visibility": "public",
                    },
                )
                tipo_uml = cls._mapear_tipo_a_uml_primitivo(a.tipo_dato)
                ET.SubElement(
                    attr_elem,
                    "type",
                    {
                        "xmi:type": "uml:PrimitiveType",
                        "href": f"http://schema.omg.org/spec/UML/2.1/uml.xml#{tipo_uml}",
                    },
                )

        # 5. Serializar Relaciones en el modelo UML
        relaciones_validas: list[tuple[RelacionDetalleDTO, str, str, str, str, str, str]] = []
        relaciones_por_clase: dict[str, list[tuple[str, str, str, str]]] = {
            str(c.id): [] for c in diagrama.clases
        }

        for r in diagrama.relaciones:
            orig_id = str(r.id_clase_origen)
            dest_id = str(r.id_clase_destino)
            if orig_id not in mapa_xmi_clases or dest_id not in mapa_xmi_clases:
                continue

            orig_xmi_id = mapa_xmi_clases[orig_id]
            dest_xmi_id = mapa_xmi_clases[dest_id]
            r_raw_id = str(r.id).replace("-", "_").upper()
            rel_xmi_id = f"EAID_{r_raw_id}"
            src_end_id = f"EAID_SRC_{r_raw_id}"
            dst_end_id = f"EAID_DST_{r_raw_id}"

            tipo_rel = (r.tipo_relacion or "asociacion").lower()
            nom_rel = r.nombre or ""

            # Determinar tipo de asociación y agregación
            agg_type = "none"
            if tipo_rel == "agregacion":
                agg_type = "shared"
            elif tipo_rel == "composicion":
                agg_type = "composite"

            assoc_elem = ET.SubElement(
                package,
                "packagedElement",
                {
                    "xmi:type": "uml:Association",
                    "xmi:id": rel_xmi_id,
                    "name": nom_rel,
                    "visibility": "public",
                },
            )

            ET.SubElement(assoc_elem, "memberEnd", {"xmi:idref": src_end_id})
            ET.SubElement(assoc_elem, "memberEnd", {"xmi:idref": dst_end_id})

            # Extremo Origen (Source)
            owned_src = ET.SubElement(
                assoc_elem,
                "ownedEnd",
                {
                    "xmi:type": "uml:Property",
                    "xmi:id": src_end_id,
                    "type": orig_xmi_id,
                    "visibility": "public",
                    "association": rel_xmi_id,
                },
            )
            if agg_type != "none":
                owned_src.set("aggregation", agg_type)
            cls._agregar_multiplicidad(owned_src, r.cardinalidad_origen or "1")

            # Extremo Destino (Target)
            owned_dst = ET.SubElement(
                assoc_elem,
                "ownedEnd",
                {
                    "xmi:type": "uml:Property",
                    "xmi:id": dst_end_id,
                    "type": dest_xmi_id,
                    "visibility": "public",
                    "association": rel_xmi_id,
                },
            )
            cls._agregar_multiplicidad(owned_dst, r.cardinalidad_destino or "0..*")

            relaciones_validas.append((r, rel_xmi_id, orig_id, dest_id, orig_xmi_id, dest_xmi_id, tipo_rel))
            rel_tuple = (rel_xmi_id, orig_xmi_id, dest_xmi_id, tipo_rel)
            if orig_id in relaciones_por_clase:
                relaciones_por_clase[orig_id].append(rel_tuple)
            if dest_id in relaciones_por_clase and dest_id != orig_id:
                relaciones_por_clase[dest_id].append(rel_tuple)

        # 6. Extensión de Enterprise Architect (Metadatos, Conectores y Diagrama Visual)
        extension = ET.SubElement(
            root,
            "xmi:Extension",
            {
                "extender": "Enterprise Architect",
                "extenderID": "6.5",
            },
        )

        # 6.1 <elements>: Metadatos del Package y de cada Clase
        elements_sec = ET.SubElement(extension, "elements")

        # Elemento del Package
        pkg_elem = ET.SubElement(
            elements_sec,
            "element",
            {
                "xmi:idref": pkg_id,
                "xmi:type": "uml:Package",
                "name": nom_diagrama,
                "scope": "public",
            },
        )
        ET.SubElement(
            pkg_elem,
            "model",
            {
                "package2": pkg_eaid,
                "package": "0",
                "tpos": "0",
                "ea_localid": "1",
                "ea_eleType": "package",
            },
        )
        ET.SubElement(
            pkg_elem,
            "properties",
            {
                "isSpecification": "false",
                "sType": "Package",
                "nType": "0",
                "scope": "public",
            },
        )
        ET.SubElement(
            pkg_elem,
            "project",
            {
                "author": "DRAWI",
                "version": "1.0",
                "phase": "1.0",
                "created": ahora_str,
                "modified": ahora_str,
                "complexity": "1",
                "status": "Proposed",
            },
        )
        ET.SubElement(pkg_elem, "code", {"gentype": "Java"})
        ET.SubElement(
            pkg_elem,
            "style",
            {
                "appearance": "BackColor=-1;BorderColor=-1;BorderWidth=-1;FontColor=-1;VSwimLanes=1;HSwimLanes=1;BorderStyle=0;",
            },
        )
        ET.SubElement(pkg_elem, "tags")
        ET.SubElement(pkg_elem, "xrefs")
        ET.SubElement(pkg_elem, "extendedProperties", {"tagged": "0", "package_name": "Model"})
        ET.SubElement(pkg_elem, "packageproperties", {"version": "1.0"})
        ET.SubElement(pkg_elem, "paths")
        ET.SubElement(pkg_elem, "times", {"created": ahora_str, "modified": ahora_str})
        ET.SubElement(
            pkg_elem,
            "flags",
            {
                "iscontrolled": "FALSE",
                "isprotected": "FALSE",
                "usedtd": "FALSE",
                "logxml": "FALSE",
                "packageFlags": "isModel=1;VICON=2;",
            },
        )

        # Elementos de Clases
        mapa_local_id_clases: dict[str, str] = {}
        for idx, c in enumerate(diagrama.clases, start=2):
            c_str_id = str(c.id)
            clase_xmi_id = mapa_xmi_clases[c_str_id]
            ea_loc_id = str(idx)
            mapa_local_id_clases[c_str_id] = ea_loc_id

            c_elem = ET.SubElement(
                elements_sec,
                "element",
                {
                    "xmi:idref": clase_xmi_id,
                    "xmi:type": "uml:Class",
                    "name": c.nombre,
                    "scope": "public",
                },
            )
            ET.SubElement(
                c_elem,
                "model",
                {
                    "package": pkg_id,
                    "tpos": "0",
                    "ea_localid": ea_loc_id,
                    "ea_eleType": "element",
                },
            )
            ET.SubElement(
                c_elem,
                "properties",
                {
                    "isSpecification": "false",
                    "sType": "Class",
                    "nType": "0",
                    "scope": "public",
                    "isRoot": "false",
                    "isLeaf": "false",
                    "isAbstract": "false",
                },
            )
            ET.SubElement(
                c_elem,
                "project",
                {
                    "author": "DRAWI",
                    "version": "1.0",
                    "phase": "1.0",
                    "created": ahora_str,
                    "modified": ahora_str,
                    "complexity": "1",
                    "status": "Proposed",
                },
            )
            ET.SubElement(c_elem, "code", {"gentype": "Java"})
            ET.SubElement(
                c_elem,
                "style",
                {
                    "appearance": "BackColor=-1;BorderColor=-1;BorderWidth=-1;FontColor=-1;VSwimLanes=1;HSwimLanes=1;BorderStyle=0;",
                },
            )
            ET.SubElement(c_elem, "tags")
            ET.SubElement(c_elem, "xrefs")
            ET.SubElement(c_elem, "extendedProperties", {"tagged": "0", "package_name": nom_diagrama})

            # Links asociados a esta clase
            rels_de_clase = relaciones_por_clase.get(c_str_id, [])
            if rels_de_clase:
                links_elem = ET.SubElement(c_elem, "links")
                for r_xmi_id, r_src_xmi, r_dst_xmi, r_tipo in rels_de_clase:
                    tag_rel = "Association"
                    if r_tipo == "generalizacion":
                        tag_rel = "Generalization"
                    elif r_tipo == "agregacion":
                        tag_rel = "Aggregation"
                    elif r_tipo == "composicion":
                        tag_rel = "Composition"

                    ET.SubElement(
                        links_elem,
                        tag_rel,
                        {
                            "xmi:id": r_xmi_id,
                            "start": r_src_xmi,
                            "end": r_dst_xmi,
                        },
                    )

        # 6.2 <connectors>: Relaciones detalladas en la extensión de EA
        connectors_sec = ET.SubElement(extension, "connectors")
        diag_xmi_id = f"EAID_DIAG_{pkg_raw_id}"

        for idx, (r, rel_xmi_id, orig_id, dest_id, orig_xmi_id, dest_xmi_id, tipo_rel) in enumerate(relaciones_validas, start=1):
            clase_orig_dto = mapa_clases_dto.get(orig_id)
            clase_dest_dto = mapa_clases_dto.get(dest_id)
            nom_orig = clase_orig_dto.nombre if clase_orig_dto else "Source"
            nom_dest = clase_dest_dto.nombre if clase_dest_dto else "Target"
            ea_loc_orig = mapa_local_id_clases.get(orig_id, "1")
            ea_loc_dest = mapa_local_id_clases.get(dest_id, "2")

            ea_type = "Association"
            subtype = "Class"
            agg_source = "none"
            if tipo_rel == "agregacion":
                agg_source = "shared"
            elif tipo_rel == "composicion":
                agg_source = "composite"
            elif tipo_rel == "generalizacion":
                ea_type = "Generalization"

            conn_elem = ET.SubElement(connectors_sec, "connector", {"xmi:idref": rel_xmi_id})

            # Source
            src_conn = ET.SubElement(conn_elem, "source", {"xmi:idref": orig_xmi_id})
            ET.SubElement(src_conn, "model", {"ea_localid": ea_loc_orig, "type": subtype, "name": nom_orig})
            ET.SubElement(src_conn, "role", {"visibility": "Public", "targetScope": "instance"})
            ET.SubElement(src_conn, "type", {"aggregation": agg_source, "containment": "Unspecified"})
            ET.SubElement(src_conn, "constraints")
            ET.SubElement(src_conn, "modifiers", {"isOrdered": "false", "changeable": "none", "isNavigable": "true"})
            ET.SubElement(src_conn, "style", {"value": "Union=0;Derived=0;AllowDuplicates=0;Owned=0;Navigable=Navigable;"})
            ET.SubElement(src_conn, "documentation")
            ET.SubElement(src_conn, "xrefs")
            ET.SubElement(src_conn, "tags")

            # Target
            dst_conn = ET.SubElement(conn_elem, "target", {"xmi:idref": dest_xmi_id})
            ET.SubElement(dst_conn, "model", {"ea_localid": ea_loc_dest, "type": subtype, "name": nom_dest})
            ET.SubElement(dst_conn, "role", {"visibility": "Public", "targetScope": "instance"})
            ET.SubElement(dst_conn, "type", {"aggregation": "none", "containment": "Unspecified"})
            ET.SubElement(dst_conn, "constraints")
            ET.SubElement(dst_conn, "modifiers", {"isOrdered": "false", "changeable": "none", "isNavigable": "true"})
            ET.SubElement(dst_conn, "style", {"value": "Union=0;Derived=0;AllowDuplicates=0;Owned=0;Navigable=Navigable;"})
            ET.SubElement(dst_conn, "documentation")
            ET.SubElement(dst_conn, "xrefs")
            ET.SubElement(dst_conn, "tags")

            ET.SubElement(conn_elem, "model", {"ea_localid": str(idx)})
            ET.SubElement(conn_elem, "properties", {"name": r.nombre or "", "ea_type": ea_type, "direction": "Unspecified"})
            ET.SubElement(conn_elem, "documentation")
            ET.SubElement(conn_elem, "appearance", {"linemode": "1", "linecolor": "-1", "linewidth": "0", "seqno": str(idx), "headStyle": "0", "lineStyle": "0"})
            ET.SubElement(
                conn_elem,
                "extendedProperties",
                {
                    "stateflags": "Activation=0;ExtendActivationUp=0;",
                    "virtualInheritance": "0",
                    "diagram": diag_xmi_id,
                    "privatedata1": "Synchronous",
                    "privatedata2": "retval=void;",
                    "privatedata3": "Call",
                    "privatedata4": "0",
                    "privatedata5": "SX=0;SY=0;EX=0;EY=0;",
                },
            )
            ET.SubElement(conn_elem, "style")
            ET.SubElement(conn_elem, "xrefs")
            ET.SubElement(conn_elem, "tags")

        # 6.3 Tipos primitivos y perfiles
        prim_types = ET.SubElement(extension, "primitivetypes")
        ET.SubElement(
            prim_types,
            "packagedElement",
            {
                "xmi:type": "uml:Package",
                "xmi:id": "EAPrimitiveTypesPackage",
                "name": "EA_PrimitiveTypes_Package",
                "visibility": "public",
            },
        )
        ET.SubElement(extension, "profiles")

        # 6.4 <diagrams>: Diagrama Visual y Layout Geométrico
        diagrams_elem = ET.SubElement(extension, "diagrams")
        diag_elem = ET.SubElement(diagrams_elem, "diagram", {"xmi:id": diag_xmi_id})

        ET.SubElement(
            diag_elem,
            "model",
            {
                "package": pkg_id,
                "localID": "1",
                "owner": pkg_id,
                "ea_localid": "1",
                "type": "Logical",
            },
        )
        ET.SubElement(
            diag_elem,
            "properties",
            {
                "name": nom_diagrama,
                "type": "Logical",
            },
        )
        ET.SubElement(
            diag_elem,
            "project",
            {
                "author": "DRAWI",
                "version": "1.0",
                "created": ahora_str,
                "modified": ahora_str,
            },
        )
        ET.SubElement(
            diag_elem,
            "style1",
            {
                "value": "ShowPrivate=1;ShowProtected=1;ShowPublic=1;HideRelationships=0;Locked=0;Border=1;HighlightForeign=1;PackageContents=1;SequenceNotes=0;ScalePrintImage=0;PPgs.cx=1;PPgs.cy=1;DocSize.cx=850;DocSize.cy=1098;ShowDetails=0;Orientation=P;Zoom=100;ShowTags=0;OpParams=1;VisibleAttributeDetail=0;ShowOpRetType=1;ShowIcons=1;CollabNums=0;HideProps=0;ShowReqs=0;ShowCons=0;PaperSize=1;HideParents=0;UseAlias=0;HideAtts=0;HideOps=0;HideStereo=0;HideElemStereo=0;ShowTests=0;ShowMaint=0;ConnectorNotation=UML 2.1;ExplicitNavigability=0;ShowShape=1;AdvancedElementProps=1;AdvancedFeatureProps=1;AdvancedConnectorProps=1;m_bElementClassifier=1;ShowNotes=0;SuppressBrackets=0;SuppConnectorLabels=0;PrintPageHeadFoot=0;ShowAsList=0;",
            },
        )
        ET.SubElement(
            diag_elem,
            "style2",
            {
                "value": "ExcludeRTF=0;DocAll=0;HideQuals=0;AttPkg=1;ShowTests=0;ShowMaint=0;SuppressFOC=0;INT_ARGS=;INT_RET=;INT_ATT=;SeqTopMargin=50;MatrixActive=0;SwimlanesActive=1;KanbanActive=0;MatrixLineWidth=1;MatrixLineClr=0;MatrixLocked=0;TConnectorNotation=UML 2.1;TExplicitNavigability=0;AdvancedElementProps=1;AdvancedFeatureProps=1;AdvancedConnectorProps=1;m_bElementClassifier=1;ProfileData=;MDGDgm=;STBLDgm=;ShowNotes=0;VisibleAttributeDetail=0;ShowOpRetType=1;SuppressBrackets=0;SuppConnectorLabels=0;PrintPageHeadFoot=0;ShowAsList=0;SuppressedCompartments=;Theme=:119;SaveTag=D95F455B;",
            },
        )
        ET.SubElement(
            diag_elem,
            "swimlanes",
            {
                "value": "locked=false;orientation=0;width=0;inbar=false;names=false;color=-1;bold=false;fcol=0;tcol=-1;ofCol=-1;ufCol=-1;hl=0;ufh=0;cls=0;SwimlaneFont=lfh:-10,lfw:0,lfi:0,lfu:0,lfs:0,lfface:Calibri,lfe:0,lfo:0,lfchar:1,lfop:0,lfcp:0,lfq:0,lfpf=0,lfWidth=0;",
            },
        )
        ET.SubElement(
            diag_elem,
            "matrixitems",
            {
                "value": "locked=false;matrixactive=false;swimlanesactive=true;kanbanactive=false;width=1;clrLine=0;",
            },
        )
        ET.SubElement(diag_elem, "extendedProperties")

        # Elementos y Conectores en el Diagrama
        elements_container = ET.SubElement(diag_elem, "elements")
        for idx, c in enumerate(diagrama.clases, start=1):
            clase_xmi_id = mapa_xmi_clases[str(c.id)]
            left = int(c.posicion_x)
            top = int(c.posicion_y)
            ancho = int(c.ancho or 280)
            right = left + ancho
            alto = max(120, 45 + len(c.atributos) * 22)
            bottom = top + alto

            geom_str = f"Left={left};Top={top};Right={right};Bottom={bottom};"
            ET.SubElement(
                elements_container,
                "element",
                {
                    "geometry": geom_str,
                    "subject": clase_xmi_id,
                    "seqno": str(idx),
                    "style": "DUID=EA_ELM_" + str(c.id).replace("-", "")[:8].upper() + ";",
                },
            )

        # Links visuales de relaciones en el diagrama
        for r, rel_xmi_id, _, _, _, _, _ in relaciones_validas:
            ET.SubElement(
                elements_container,
                "element",
                {
                    "geometry": "SX=0;SY=0;EX=0;EY=0;Path=;",
                    "subject": rel_xmi_id,
                    "style": ";Hidden=0;",
                },
            )

        # Generar XML formateado limpio
        raw_xml = ET.tostring(root, encoding="utf-8")
        parsed = minidom.parseString(raw_xml)
        return parsed.toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")

    @classmethod
    def _mapear_tipo_a_uml_primitivo(cls, tipo_dato: str) -> str:
        t = (tipo_dato or "").strip().lower()
        if t in {"integer", "bigint", "int", "int4", "int8", "smallint"}:
            return "Integer"
        if t in {"boolean", "bool"}:
            return "Boolean"
        return "String"

    @classmethod
    def _agregar_multiplicidad(cls, end_elem: ET.Element, card: str) -> None:
        c = (card or "1").strip().lower()
        if c in {"1", "1..1"}:
            ET.SubElement(end_elem, "lowerValue", {"xmi:type": "uml:LiteralInteger", "value": "1"})
            ET.SubElement(end_elem, "upperValue", {"xmi:type": "uml:LiteralUnlimitedNatural", "value": "1"})
        elif c in {"0..1"}:
            ET.SubElement(end_elem, "lowerValue", {"xmi:type": "uml:LiteralInteger", "value": "0"})
            ET.SubElement(end_elem, "upperValue", {"xmi:type": "uml:LiteralUnlimitedNatural", "value": "1"})
        elif c in {"0..*", "*", "n", "m"}:
            ET.SubElement(end_elem, "lowerValue", {"xmi:type": "uml:LiteralInteger", "value": "0"})
            ET.SubElement(end_elem, "upperValue", {"xmi:type": "uml:LiteralUnlimitedNatural", "value": "*"})
        elif c in {"1..*", "1..n", "1..m"}:
            ET.SubElement(end_elem, "lowerValue", {"xmi:type": "uml:LiteralInteger", "value": "1"})
            ET.SubElement(end_elem, "upperValue", {"xmi:type": "uml:LiteralUnlimitedNatural", "value": "*"})
        else:
            ET.SubElement(end_elem, "lowerValue", {"xmi:type": "uml:LiteralInteger", "value": "1"})
            ET.SubElement(end_elem, "upperValue", {"xmi:type": "uml:LiteralUnlimitedNatural", "value": "1"})

