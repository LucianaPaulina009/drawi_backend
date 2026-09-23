from __future__ import annotations

import logging
from uuid import UUID, uuid4

from app.modules.diagramas.application.services.geometria_conectores import (
    calcular_mejores_conectores,
)
from app.modules.diagramas.application.services.notificador_colaboracion import (
    construir_efectos,
    emitir_evento_mutacion_confirmada,
    proyectar_clase,
    proyectar_estructura_nm,
    proyectar_relacion,
)
from app.modules.diagramas.application.use_cases.atributo.atributo_use_cases import (
    AtributoCommand,
    AtributoUseCase,
)
from app.modules.diagramas.application.use_cases.clase.crear_clase import (
    CrearClaseCommand,
    CrearClaseUseCase,
)
from app.modules.diagramas.application.use_cases.estructura_relacion_nm.crear_estructura_relacion_nm import (
    CrearEstructuraRelacionNmCommand,
    CrearEstructuraRelacionNmUseCase,
)
from app.modules.diagramas.application.use_cases.relacion.crear_relacion import (
    AtributoFkNuevoCommand,
    CrearRelacionCommand,
    CrearRelacionUseCase,
    MaterializacionFKCommand,
)
from app.modules.diagramas.application.use_cases.relacion.materializacion import (
    _maximo,
    requiere_materializacion,
)
from app.modules.diagramas.application.validaciones import (
    obtener_diagrama_autorizado,
)
from app.modules.diagramas.domain.entities.relacion import Relacion
from app.modules.diagramas.domain.repositories.atributo_repository import (
    AtributoRepository,
)
from app.modules.diagramas.domain.repositories.clase_repository import ClaseRepository
from app.modules.diagramas.domain.repositories.diagrama_repository import (
    DiagramaRepository,
)
from app.modules.diagramas.domain.repositories.estructura_relacion_nm_repository import (
    EstructuraRelacionNmRepository,
)
from app.modules.diagramas.domain.repositories.referencia_fk_repository import (
    ReferenciaFKRepository,
)
from app.modules.diagramas.domain.repositories.relacion_repository import (
    RelacionRepository,
)
from app.modules.gestion_colaboradores.domain.repositories.colaborador_proyecto_repository import (
    ColaboradorProyectoRepository,
)
from app.modules.gestion_proyectos.domain.repositories.proyecto_repository import (
    ProyectoRepository,
)
from app.modules.intercambio_enterprise_architect.application.dtos.resultado_intercambio_dto import (
    ResultadoImportacionEaDTO,
)
from app.modules.intercambio_enterprise_architect.application.services.parser_xmi_enterprise_architect import (
    ParserXmiEnterpriseArchitect,
)
from app.modules.intercambio_enterprise_architect.application.services.reconciliador_modelo_ea import (
    ReconciliadorModeloEa,
)
from app.shared.domain.exceptions import (
    ConflictException,
    ValidationException,
)

logger = logging.getLogger(__name__)


class ImportarDiagramaEaUseCase:
    """Caso de uso para importar un archivo XML/XMI de Enterprise Architect en el diagrama activo,
    exigiendo que la página receptora esté en blanco y reconstruyendo las entidades con las invariantes de DRAWI.
    """

    def __init__(
        self,
        proyecto_repository: ProyectoRepository,
        diagrama_repository: DiagramaRepository,
        clase_repository: ClaseRepository,
        atributo_repository: AtributoRepository,
        relacion_repository: RelacionRepository,
        referencia_fk_repository: ReferenciaFKRepository,
        crear_clase_use_case: CrearClaseUseCase,
        atributo_use_case: AtributoUseCase,
        crear_relacion_use_case: CrearRelacionUseCase,
        crear_estructura_nm_use_case: CrearEstructuraRelacionNmUseCase | None = None,
        estructura_nm_repository: EstructuraRelacionNmRepository | None = None,
        colaborador_repository: ColaboradorProyectoRepository | None = None,
    ) -> None:
        self.proyecto_repo = proyecto_repository
        self.diagrama_repo = diagrama_repository
        self.clase_repo = clase_repository
        self.atributo_repo = atributo_repository
        self.relacion_repo = relacion_repository
        self.referencia_fk_repo = referencia_fk_repository
        self.crear_clase_use_case = crear_clase_use_case
        self.atributo_use_case = atributo_use_case
        self.crear_relacion_use_case = crear_relacion_use_case
        self.crear_estructura_nm_use_case = crear_estructura_nm_use_case
        self.estructura_nm_repo = estructura_nm_repository
        self.colaborador_repo = colaborador_repository

    def execute(
        self,
        *,
        usuario_id: str,
        proyecto_id: UUID,
        diagrama_id: UUID,
        contenido_xml: str | bytes,
    ) -> ResultadoImportacionEaDTO:
        # 1. Autorización de edición
        diagrama = obtener_diagrama_autorizado(
            propietario_id=usuario_id,
            diagrama_id=diagrama_id,
            proyecto_repository=self.proyecto_repo,
            diagrama_repository=self.diagrama_repo,
            colaborador_repository=self.colaborador_repo,
            exigir_edicion=True,
        )

        if diagrama.id_proyecto != proyecto_id:
            raise ValidationException(
                "El diagrama no pertenece al proyecto especificado.",
                code="DIAGRAMA_NO_ENCONTRADO",
            )

        # 2. Regla estricta: Solo se puede importar si el diagrama o la página está en blanco
        clases_actuales = self.clase_repo.listar_por_diagrama(diagrama_id)
        if len(clases_actuales) > 0:
            raise ConflictException(
                "La importación de Enterprise Architect solo está permitida en un diagrama o página en blanco.",
                code="DIAGRAMA_NO_ESTA_EN_BLANCO",
            )

        # 3. Parsear el archivo XML/XMI con seguridad anti-XXE
        clases_ea, relaciones_ea, advertencias_parser = ParserXmiEnterpriseArchitect.parsear(
            contenido_xml
        )

        if not clases_ea:
            raise ValidationException(
                "El archivo no contiene clases válidas para importar.",
                code="FORMATO_EA_INVALIDO",
            )

        # 4. Reconciliar elementos con las reglas de dominio de DRAWI
        plan = ReconciliadorModeloEa.reconciliar(clases_ea, relaciones_ea)
        advertencias = list(advertencias_parser) + list(plan.advertencias)

        mapa_ea_a_drawi: dict[str, UUID] = {}
        total_clases_creadas = 0
        total_atributos_creados = 0
        total_relaciones_creadas = 0
        total_estructuras_nm_creadas = 0

        # 5. Crear clases regulares y sus atributos limpios
        for c in plan.clases_regulares:
            cmd_c = CrearClaseCommand(
                propietario_id=usuario_id,
                diagrama_id=diagrama_id,
                posicion_x=c.posicion_x,
                posicion_y=c.posicion_y,
                ancho=c.ancho or 280.0,
                nombre=c.nombre,
            )
            clase_creada, _ = self.crear_clase_use_case.execute(cmd_c)
            mapa_ea_a_drawi[c.id_ea] = clase_creada.id
            total_clases_creadas += 1

            # Crear atributos regulares (el PK 'id' ya fue creado automáticamente por CrearClaseUseCase)
            for a in c.atributos:
                cmd_a = AtributoCommand(
                    propietario_id=usuario_id,
                    clase_id=clase_creada.id,
                    datos={
                        "nombre": a.nombre,
                        "tipo_dato": a.tipo_dato,
                        "permite_nulo": True,
                        "es_unico": False,
                        "es_llave_primaria": False,
                    },
                )
                self.atributo_use_case.crear(cmd_a)
                total_atributos_creados += 1

            # Notificar mutación de clase
            proy = proyectar_clase(self.clase_repo, self.atributo_repo, clase_creada.id)
            efectos = construir_efectos(clases_actualizadas=[proy])
            emitir_evento_mutacion_confirmada(
                diagrama_id=diagrama_id,
                action_id=str(uuid4()),
                tipo_operacion="CREAR_CLASE",
                emisor_id=usuario_id,
                efectos=efectos,
            )

        # 6. Crear estructuras N:M y clases intermedias
        if self.crear_estructura_nm_use_case and self.estructura_nm_repo:
            for nm in plan.estructuras_nm:
                id_orig = mapa_ea_a_drawi.get(nm.clase_origen_ea)
                id_dest = mapa_ea_a_drawi.get(nm.clase_destino_ea)
                if not id_orig or not id_dest:
                    continue

                clase_orig_obj = self.clase_repo.obtener_por_id(id_orig)
                clase_dest_obj = self.clase_repo.obtener_por_id(id_dest)
                if not clase_orig_obj or not clase_dest_obj:
                    continue

                attrs_orig = self.atributo_repo.listar_por_clase(id_orig)
                attrs_dest = self.atributo_repo.listar_por_clase(id_dest)
                pk_orig = next((a for a in attrs_orig if a.es_llave_primaria or a.es_unico), None)
                pk_dest = next((a for a in attrs_dest if a.es_llave_primaria or a.es_unico), None)
                if not pk_orig or not pk_dest:
                    continue

                con_orig_nm, con_dest_nm = calcular_mejores_conectores(
                    clase_origen=clase_orig_obj,
                    clase_destino=clase_dest_obj,
                    relaciones_existentes=[],
                )

                id_struct = uuid4()
                id_inter = uuid4()
                action_id = uuid4()

                cmd_nm = CrearEstructuraRelacionNmCommand(
                    propietario_id=usuario_id,
                    diagrama_id=diagrama_id,
                    action_id=action_id,
                    id_estructura=id_struct,
                    id_clase_origen=id_orig,
                    id_clase_destino=id_dest,
                    id_clase_intermedia=id_inter,
                    id_atributo_inicial=uuid4(),
                    id_atributo_fk_origen=uuid4(),
                    id_atributo_fk_destino=uuid4(),
                    id_relacion_origen=uuid4(),
                    id_relacion_destino=uuid4(),
                    id_referencia_fk_origen=uuid4(),
                    id_referencia_fk_destino=uuid4(),
                    id_atributo_referenciado_origen=pk_orig.id,
                    id_atributo_referenciado_destino=pk_dest.id,
                    nombre_intermedia=nm.nombre_intermedia,
                    posicion_x=nm.posicion_x,
                    posicion_y=nm.posicion_y,
                    ancho=280.0,
                    conector_origen=con_orig_nm,
                    conector_destino=con_dest_nm,
                )
                res_nm = self.crear_estructura_nm_use_case.execute(cmd_nm, confirmar=True)
                total_estructuras_nm_creadas += 1
                total_clases_creadas += 1
                total_relaciones_creadas += 2

                if nm.id_clase_intermedia_ea:
                    mapa_ea_a_drawi[nm.id_clase_intermedia_ea] = id_inter

                # Agregar atributos payload de la tabla intermedia si existen
                for a_payload in nm.atributos_payload:
                    cmd_pay = AtributoCommand(
                        propietario_id=usuario_id,
                        clase_id=id_inter,
                        datos={
                            "nombre": a_payload.nombre,
                            "tipo_dato": a_payload.tipo_dato,
                            "permite_nulo": True,
                            "es_unico": False,
                            "es_llave_primaria": False,
                        },
                    )
                    self.atributo_use_case.crear(cmd_pay)
                    total_atributos_creados += 1

                # Notificar mutación N:M
                proy_inter = proyectar_clase(self.clase_repo, self.atributo_repo, id_inter)
                proy_rel_orig = proyectar_relacion(self.relacion_repo, self.referencia_fk_repo, UUID(res_nm["id_relacion_origen"]))
                proy_rel_dest = proyectar_relacion(self.relacion_repo, self.referencia_fk_repo, UUID(res_nm["id_relacion_destino"]))
                proy_struct = proyectar_estructura_nm(self.estructura_nm_repo, id_struct)

                efectos = construir_efectos(
                    clases_actualizadas=[proy_inter],
                    relaciones_actualizadas=[proy_rel_orig, proy_rel_dest],
                    estructuras_nm_actualizadas=[proy_struct],
                )
                emitir_evento_mutacion_confirmada(
                    diagrama_id=diagrama_id,
                    action_id=str(action_id),
                    tipo_operacion="CREAR_ESTRUCTURA_NM",
                    emisor_id=usuario_id,
                    efectos=efectos,
                )

        # 7. Crear relaciones binarias (1:1 y 1:N) con materialización de FKs
        todas_clases = self.clase_repo.listar_por_diagrama(diagrama_id)
        todas_relaciones = self.relacion_repo.listar_por_diagrama(diagrama_id)

        for r in plan.relaciones_binarias:
            id_orig = mapa_ea_a_drawi.get(r.id_clase_origen_ea)
            id_dest = mapa_ea_a_drawi.get(r.id_clase_destino_ea)
            if not id_orig or not id_dest:
                continue

            clase_orig_obj = next((c for c in todas_clases if c.id == id_orig), None)
            clase_dest_obj = next((c for c in todas_clases if c.id == id_dest), None)
            if not clase_orig_obj or not clase_dest_obj:
                continue

            con_orig, con_dest = calcular_mejores_conectores(
                clase_origen=clase_orig_obj,
                clase_destino=clase_dest_obj,
                relaciones_existentes=todas_relaciones,
            )

            id_rel = uuid4()
            rel_temp = Relacion.crear(
                id=id_rel,
                id_diagrama=diagrama_id,
                id_clase_origen=id_orig,
                id_clase_destino=id_dest,
                tipo_relacion=r.tipo_relacion,
                cardinalidad_origen=r.cardinalidad_origen,
                cardinalidad_destino=r.cardinalidad_destino,
                conector_origen=con_orig,
                conector_destino=con_dest,
                nombre=r.nombre,
            )

            materializaciones: list[MaterializacionFKCommand] = []
            if requiere_materializacion(rel_temp):
                origen_muchos = _maximo(rel_temp.cardinalidad_origen) is None or _maximo(rel_temp.cardinalidad_origen) > 1
                destino_muchos = _maximo(rel_temp.cardinalidad_destino) is None or _maximo(rel_temp.cardinalidad_destino) > 1

                if r.clase_fk_ea and mapa_ea_a_drawi.get(r.clase_fk_ea):
                    clase_fk = mapa_ea_a_drawi[r.clase_fk_ea]
                    clase_ref = id_orig if (clase_fk == id_dest and id_orig != id_dest) else (id_dest if id_orig != id_dest else id_orig)
                elif rel_temp.tipo_relacion in {"herencia", "realizacion", "dependencia"}:
                    clase_fk = id_orig
                    clase_ref = id_dest
                elif id_orig == id_dest:
                    clase_fk = id_orig
                    clase_ref = id_orig
                elif origen_muchos != destino_muchos:
                    clase_fk = id_orig if origen_muchos else id_dest
                    clase_ref = id_dest if origen_muchos else id_orig
                else:
                    clase_fk = id_dest
                    clase_ref = id_orig

                pk_attr = next((a for a in self.atributo_repo.listar_por_clase(clase_ref) if a.es_llave_primaria), None)
                if pk_attr:
                    clase_ref_obj = self.clase_repo.obtener_por_id(clase_ref)
                    clase_ref_name = (clase_ref_obj.nombre if clase_ref_obj else "origen").lower()

                    if r.nombre_fk:
                        nombre_fk = r.nombre_fk
                    elif id_orig == id_dest:
                        nombre_fk = f"id_{clase_ref_name}_padre"
                    else:
                        nombre_fk = f"id_{clase_ref_name}"

                    attrs_en_fk = self.atributo_repo.listar_por_clase(clase_fk)
                    attr_existente = next((a for a in attrs_en_fk if a.nombre.lower() == nombre_fk.lower()), None)
                    if attr_existente:
                        materializaciones.append(
                            MaterializacionFKCommand(
                                id_referencia_fk=uuid4(),
                                id_atributo_referenciado=pk_attr.id,
                                id_atributo_fk=attr_existente.id,
                            )
                        )
                    else:
                        materializaciones.append(
                            MaterializacionFKCommand(
                                id_referencia_fk=uuid4(),
                                id_atributo_referenciado=pk_attr.id,
                                id_clase_fk=clase_fk,
                                atributo_fk_nuevo=AtributoFkNuevoCommand(
                                    id_atributo=uuid4(),
                                    nombre=nombre_fk,
                                    tipo_dato=pk_attr.tipo_dato,
                                    longitud=pk_attr.longitud,
                                    precision=pk_attr.precision,
                                    escala=pk_attr.escala,
                                ),
                            )
                        )

            cmd_rel = CrearRelacionCommand(
                propietario_id=usuario_id,
                diagrama_id=diagrama_id,
                id_relacion=id_rel,
                id_clase_origen=id_orig,
                id_clase_destino=id_dest,
                tipo_relacion=r.tipo_relacion,
                cardinalidad_origen=r.cardinalidad_origen,
                cardinalidad_destino=r.cardinalidad_destino,
                conector_origen=con_orig,
                conector_destino=con_dest,
                nombre=r.nombre,
                materializacion_fk=materializaciones if materializaciones else None,
            )
            rel_creada = self.crear_relacion_use_case.execute(cmd_rel)
            total_relaciones_creadas += 1

            # Notificar mutación de relación
            proy_rel = proyectar_relacion(self.relacion_repo, self.referencia_fk_repo, rel_creada.id)
            proy_orig = proyectar_clase(self.clase_repo, self.atributo_repo, id_orig)
            proy_dest = proyectar_clase(self.clase_repo, self.atributo_repo, id_dest)
            efectos = construir_efectos(
                clases_actualizadas=[proy_orig, proy_dest],
                relaciones_actualizadas=[proy_rel],
            )
            emitir_evento_mutacion_confirmada(
                diagrama_id=diagrama_id,
                action_id=str(uuid4()),
                tipo_operacion="CREAR_RELACION",
                emisor_id=usuario_id,
                efectos=efectos,
            )

        return ResultadoImportacionEaDTO(
            diagrama_id=diagrama_id,
            clases_importadas=total_clases_creadas,
            atributos_importados=total_atributos_creados,
            relaciones_importadas=total_relaciones_creadas,
            estructuras_nm_importadas=total_estructuras_nm_creadas,
            advertencias=advertencias,
        )
