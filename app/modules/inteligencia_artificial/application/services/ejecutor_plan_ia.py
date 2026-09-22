from __future__ import annotations

import logging
from typing import Any
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
from app.modules.diagramas.application.use_cases.clase.actualizar_clase import (
    ActualizarClaseCommand,
    ActualizarClaseUseCase,
)
from app.modules.diagramas.application.use_cases.clase.crear_clase import (
    CrearClaseCommand,
    CrearClaseUseCase,
)
from app.shared.domain.exceptions import (
    DomainException,
    NotFoundException,
    ValidationException,
)
from app.modules.diagramas.application.use_cases.clase.eliminar_clase import (
    EliminarClaseCommand,
    EliminarClaseUseCase,
)
from app.modules.diagramas.application.use_cases.estructura_relacion_nm.crear_estructura_relacion_nm import (
    CrearEstructuraRelacionNmCommand,
    CrearEstructuraRelacionNmUseCase,
)
from app.modules.diagramas.application.use_cases.estructura_relacion_nm.eliminar_estructura_relacion_nm import (
    EliminarEstructuraRelacionNmCommand,
    EliminarEstructuraRelacionNmUseCase,
)
from app.modules.diagramas.application.use_cases.relacion.actualizar_relacion import (
    ActualizarRelacionCommand,
    ActualizarRelacionUseCase,
)
from app.modules.diagramas.application.use_cases.relacion.crear_relacion import (
    AtributoFkNuevoCommand,
    CrearRelacionCommand,
    CrearRelacionUseCase,
    MaterializacionFKCommand,
)
from app.modules.diagramas.application.use_cases.relacion.eliminar_relacion import (
    EliminarRelacionCommand,
    EliminarRelacionUseCase,
)
from app.modules.diagramas.application.use_cases.relacion.materializacion import (
    _maximo,
    requiere_materializacion,
)
from app.modules.diagramas.domain.entities.relacion import Relacion
from app.modules.diagramas.domain.repositories.atributo_repository import (
    AtributoRepository,
)
from app.modules.diagramas.domain.repositories.clase_repository import ClaseRepository
from app.modules.diagramas.domain.repositories.estructura_relacion_nm_repository import (
    EstructuraRelacionNmRepository,
)
from app.modules.diagramas.domain.repositories.referencia_fk_repository import (
    ReferenciaFKRepository,
)
from app.modules.diagramas.domain.repositories.relacion_repository import (
    RelacionRepository,
)
from app.modules.inteligencia_artificial.application.services.resolvedor_referencias_ia import (
    ResolvedorReferenciasIa,
)
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
    PosicionSchema,
)

logger = logging.getLogger(__name__)


class EjecutorPlanIa:
    """Ejecuta secuencialmente las acciones del plan IA reutilizando los casos de uso existentes de Diagramas."""

    def __init__(
        self,
        crear_clase_use_case: CrearClaseUseCase,
        atributo_use_case: AtributoUseCase,
        crear_relacion_use_case: CrearRelacionUseCase,
        clase_repository: ClaseRepository,
        atributo_repository: AtributoRepository,
        relacion_repository: RelacionRepository,
        referencia_fk_repository: ReferenciaFKRepository,
        actualizar_clase_use_case: ActualizarClaseUseCase | None = None,
        eliminar_clase_use_case: EliminarClaseUseCase | None = None,
        actualizar_relacion_use_case: ActualizarRelacionUseCase | None = None,
        eliminar_relacion_use_case: EliminarRelacionUseCase | None = None,
        crear_estructura_nm_use_case: CrearEstructuraRelacionNmUseCase | None = None,
        eliminar_estructura_nm_use_case: EliminarEstructuraRelacionNmUseCase | None = None,
        estructura_nm_repository: EstructuraRelacionNmRepository | None = None,
    ) -> None:
        self.crear_clase_use_case = crear_clase_use_case
        self.atributo_use_case = atributo_use_case
        self.crear_relacion_use_case = crear_relacion_use_case
        self.clase_repo = clase_repository
        self.atributo_repo = atributo_repository
        self.relacion_repo = relacion_repository
        self.referencia_fk_repo = referencia_fk_repository
        self.actualizar_clase_use_case = actualizar_clase_use_case
        self.eliminar_clase_use_case = eliminar_clase_use_case
        self.actualizar_relacion_use_case = actualizar_relacion_use_case
        self.eliminar_relacion_use_case = eliminar_relacion_use_case
        self.crear_estructura_nm_use_case = crear_estructura_nm_use_case
        self.eliminar_estructura_nm_use_case = eliminar_estructura_nm_use_case
        self.estructura_nm_repo = estructura_nm_repository

    def _obtener_clases_actuales(self, diagrama_id: UUID) -> list[Any]:
        clases = self.clase_repo.listar_por_diagrama(diagrama_id)
        for c in clases:
            if not hasattr(c, "atributos") or not c.atributos:
                c.atributos = self.atributo_repo.listar_por_clase(c.id)
        return clases

    def ejecutar_plan(
        self,
        *,
        usuario_id: str,
        diagrama_id: UUID,
        acciones: list[AccionIaUnion],
        clases_existentes: dict[str, UUID] | None = None,
    ) -> list[dict[str, Any]]:
        mapa_referencias: dict[str, UUID] = {}
        if clases_existentes:
            for clave, uid in clases_existentes.items():
                mapa_referencias[clave.lower()] = uid
                mapa_referencias[str(uid).lower()] = uid

        resultados_pasos: list[dict[str, Any]] = []

        for indice, accion in enumerate(acciones, start=1):
            paso_info: dict[str, Any] = {
                "paso": indice,
                "tipo": accion.tipo,
                "estado": "pendiente",
            }
            try:
                clases_actuales = self._obtener_clases_actuales(diagrama_id)
                relaciones_actuales = self.relacion_repo.listar_por_diagrama(diagrama_id)

                if isinstance(accion, AccionCrearClaseSchema):
                    pos = accion.posicion or PosicionSchema(
                        x=150.0 + (indice * 40.0), y=150.0 + (indice * 30.0)
                    )
                    cmd = CrearClaseCommand(
                        propietario_id=usuario_id,
                        diagrama_id=diagrama_id,
                        posicion_x=pos.x,
                        posicion_y=pos.y,
                        ancho=accion.ancho or 280.0,
                        nombre=accion.nombre,
                    )
                    clase, _ = self.crear_clase_use_case.execute(cmd)
                    mapa_referencias[accion.referencia.strip().lower()] = clase.id
                    mapa_referencias[accion.nombre.strip().lower()] = clase.id
                    mapa_referencias[str(clase.id).lower()] = clase.id

                    proy = proyectar_clase(self.clase_repo, self.atributo_repo, clase.id)
                    efectos = construir_efectos(clases_actualizadas=[proy])
                    emitir_evento_mutacion_confirmada(
                        diagrama_id=diagrama_id,
                        action_id=str(uuid4()),
                        tipo_operacion="CREAR_CLASE",
                        emisor_id=usuario_id,
                        efectos=efectos,
                    )
                    paso_info["estado"] = "completado"
                    paso_info["id_creado"] = str(clase.id)
                    paso_info["nombre"] = clase.nombre

                elif isinstance(accion, AccionActualizarClaseSchema):
                    if not self.actualizar_clase_use_case:
                        raise ValidationException("El caso de uso ActualizarClase no está disponible.")
                    res_c = ResolvedorReferenciasIa.resolver_clase(
                        accion.clase_referencia, clases_actuales, mapa_referencias
                    )
                    if not res_c.exito:
                        if res_c.es_ambiguo:
                            raise ValidationException(res_c.motivo, code="REFERENCIA_AMBIGUA")
                        raise NotFoundException(res_c.motivo, code="REFERENCIA_NO_ENCONTRADA")

                    cmd_act_c = ActualizarClaseCommand(
                        propietario_id=usuario_id,
                        diagrama_id=diagrama_id,
                        clase_id=res_c.id,
                        nombre=accion.nuevo_nombre,
                        posicion_x=accion.posicion.x if accion.posicion else None,
                        posicion_y=accion.posicion.y if accion.posicion else None,
                        ancho=accion.ancho,
                    )
                    clase_act = self.actualizar_clase_use_case.execute(cmd_act_c)
                    if accion.nuevo_nombre:
                        mapa_referencias[accion.nuevo_nombre.strip().lower()] = clase_act.id

                    proy = proyectar_clase(self.clase_repo, self.atributo_repo, clase_act.id)
                    efectos = construir_efectos(clases_actualizadas=[proy])
                    emitir_evento_mutacion_confirmada(
                        diagrama_id=diagrama_id,
                        action_id=str(uuid4()),
                        tipo_operacion="ACTUALIZAR_CLASE",
                        emisor_id=usuario_id,
                        efectos=efectos,
                    )
                    paso_info["estado"] = "completado"
                    paso_info["id_clase"] = str(clase_act.id)
                    paso_info["nombre"] = clase_act.nombre

                elif isinstance(accion, AccionEliminarClaseSchema):
                    if not self.eliminar_clase_use_case:
                        raise ValidationException("El caso de uso EliminarClase no está disponible.")
                    res_c = ResolvedorReferenciasIa.resolver_clase(
                        accion.clase_referencia, clases_actuales, mapa_referencias
                    )
                    if not res_c.exito:
                        if res_c.es_ambiguo:
                            raise ValidationException(res_c.motivo, code="REFERENCIA_AMBIGUA")
                        raise NotFoundException(res_c.motivo, code="REFERENCIA_NO_ENCONTRADA")

                    cmd_elim_c = EliminarClaseCommand(
                        propietario_id=usuario_id,
                        diagrama_id=diagrama_id,
                        clase_id=res_c.id,
                    )
                    cierre = self.eliminar_clase_use_case.execute(cmd_elim_c)
                    efectos = construir_efectos(
                        clases_eliminadas=list(cierre.clases_eliminadas),
                        relaciones_eliminadas=list(cierre.relaciones_eliminadas),
                        estructuras_nm_eliminadas=list(cierre.estructuras_nm_eliminadas),
                    )
                    emitir_evento_mutacion_confirmada(
                        diagrama_id=diagrama_id,
                        action_id=str(uuid4()),
                        tipo_operacion="ELIMINAR_CLASE",
                        emisor_id=usuario_id,
                        efectos=efectos,
                    )
                    paso_info["estado"] = "completado"
                    paso_info["id_eliminado"] = str(res_c.id)

                elif isinstance(accion, AccionCrearAtributoSchema):
                    ref_clase = accion.clase_referencia.strip().lower()
                    id_clase = mapa_referencias.get(ref_clase)
                    if not id_clase:
                        res_c = ResolvedorReferenciasIa.resolver_clase(
                            accion.clase_referencia, clases_actuales, mapa_referencias
                        )
                        if not res_c.exito:
                            if res_c.es_ambiguo:
                                raise ValidationException(res_c.motivo, code="REFERENCIA_AMBIGUA")
                            raise NotFoundException(res_c.motivo, code="REFERENCIA_NO_ENCONTRADA")
                        id_clase = res_c.id

                    datos_attr: dict[str, Any] = {
                        "nombre": accion.nombre,
                        "tipo_dato": accion.tipo_dato,
                        "longitud": accion.longitud,
                        "precision": accion.precision,
                        "escala": accion.escala,
                        "permite_nulo": accion.permite_nulo,
                        "es_unico": accion.es_unico,
                        "es_llave_primaria": accion.es_llave_primaria,
                        "valor_por_defecto": accion.valor_por_defecto,
                    }
                    cmd_attr = AtributoCommand(
                        propietario_id=usuario_id,
                        clase_id=id_clase,
                        datos=datos_attr,
                    )
                    nuevo_attr = self.atributo_use_case.crear(cmd_attr)

                    proy = proyectar_clase(self.clase_repo, self.atributo_repo, id_clase)
                    efectos = construir_efectos(clases_actualizadas=[proy])
                    emitir_evento_mutacion_confirmada(
                        diagrama_id=diagrama_id,
                        action_id=str(uuid4()),
                        tipo_operacion="CREAR_ATRIBUTO",
                        emisor_id=usuario_id,
                        efectos=efectos,
                    )
                    paso_info["estado"] = "completado"
                    paso_info["id_creado"] = str(nuevo_attr.id)
                    paso_info["nombre"] = nuevo_attr.nombre

                elif isinstance(accion, AccionActualizarAtributoSchema):
                    res_a = ResolvedorReferenciasIa.resolver_atributo(
                        accion.clase_referencia, accion.atributo_referencia, clases_actuales, mapa_referencias
                    )
                    if not res_a.exito:
                        if res_a.es_ambiguo:
                            raise ValidationException(res_a.motivo, code="REFERENCIA_AMBIGUA")
                        raise NotFoundException(res_a.motivo, code="REFERENCIA_NO_ENCONTRADA")

                    id_attr = res_a.id
                    id_clase = res_a.metadatos["id_clase"] if res_a.metadatos else None
                    if not id_clase:
                        raise NotFoundException("No se pudo determinar la clase del atributo a actualizar.", code="REFERENCIA_NO_ENCONTRADA")

                    campos: dict[str, Any] = {}
                    if accion.nuevo_nombre is not None:
                        campos["nombre"] = accion.nuevo_nombre
                    if accion.tipo_dato is not None:
                        campos["tipo_dato"] = accion.tipo_dato
                    if accion.longitud is not None:
                        campos["longitud"] = accion.longitud
                    if accion.precision is not None:
                        campos["precision"] = accion.precision
                    if accion.escala is not None:
                        campos["escala"] = accion.escala
                    if accion.permite_nulo is not None:
                        campos["permite_nulo"] = accion.permite_nulo
                    if accion.es_unico is not None:
                        campos["es_unico"] = accion.es_unico
                    if accion.valor_por_defecto is not None:
                        campos["valor_por_defecto"] = accion.valor_por_defecto

                    cmd_act_a = AtributoCommand(
                        propietario_id=usuario_id,
                        clase_id=id_clase,
                        atributo_id=id_attr,
                        datos=campos,
                    )
                    attr_act = self.atributo_use_case.actualizar(cmd_act_a)

                    proy = proyectar_clase(self.clase_repo, self.atributo_repo, id_clase)
                    efectos = construir_efectos(clases_actualizadas=[proy])
                    emitir_evento_mutacion_confirmada(
                        diagrama_id=diagrama_id,
                        action_id=str(uuid4()),
                        tipo_operacion="ACTUALIZAR_ATRIBUTO",
                        emisor_id=usuario_id,
                        efectos=efectos,
                    )
                    paso_info["estado"] = "completado"
                    paso_info["id_atributo"] = str(attr_act.id)
                    paso_info["nombre"] = attr_act.nombre

                elif isinstance(accion, AccionEliminarAtributoSchema):
                    res_a = ResolvedorReferenciasIa.resolver_atributo(
                        accion.clase_referencia, accion.atributo_referencia, clases_actuales, mapa_referencias
                    )
                    if not res_a.exito:
                        if res_a.es_ambiguo:
                            raise ValidationException(res_a.motivo, code="REFERENCIA_AMBIGUA")
                        raise NotFoundException(res_a.motivo, code="REFERENCIA_NO_ENCONTRADA")

                    id_attr = res_a.id
                    id_clase = res_a.metadatos["id_clase"] if res_a.metadatos else None
                    if not id_clase:
                        raise NotFoundException("No se pudo determinar la clase del atributo a eliminar.", code="REFERENCIA_NO_ENCONTRADA")

                    cmd_elim_a = AtributoCommand(
                        propietario_id=usuario_id,
                        clase_id=id_clase,
                        atributo_id=id_attr,
                        datos={},
                    )
                    cierre = self.atributo_use_case.eliminar(cmd_elim_a)
                    proy_clase = (
                        proyectar_clase(self.clase_repo, self.atributo_repo, id_clase)
                        if id_clase not in cierre.clases_eliminadas
                        else None
                    )
                    efectos = construir_efectos(
                        clases_actualizadas=[proy_clase] if proy_clase else None,
                        clases_eliminadas=list(cierre.clases_eliminadas),
                        relaciones_eliminadas=list(cierre.relaciones_eliminadas),
                        estructuras_nm_eliminadas=list(cierre.estructuras_nm_eliminadas),
                    )
                    emitir_evento_mutacion_confirmada(
                        diagrama_id=diagrama_id,
                        action_id=str(uuid4()),
                        tipo_operacion="ELIMINAR_ATRIBUTO",
                        emisor_id=usuario_id,
                        efectos=efectos,
                    )
                    paso_info["estado"] = "completado"
                    paso_info["id_eliminado"] = str(id_attr)

                elif isinstance(accion, AccionCrearRelacionSchema):
                    res_orig = ResolvedorReferenciasIa.resolver_clase(
                        accion.clase_origen_referencia, clases_actuales, mapa_referencias
                    )
                    res_dest = ResolvedorReferenciasIa.resolver_clase(
                        accion.clase_destino_referencia, clases_actuales, mapa_referencias
                    )
                    if not res_orig.exito:
                        if res_orig.es_ambiguo:
                            raise ValidationException(res_orig.motivo, code="REFERENCIA_AMBIGUA")
                        raise NotFoundException(res_orig.motivo, code="REFERENCIA_NO_ENCONTRADA")
                    if not res_dest.exito:
                        if res_dest.es_ambiguo:
                            raise ValidationException(res_dest.motivo, code="REFERENCIA_AMBIGUA")
                        raise NotFoundException(res_dest.motivo, code="REFERENCIA_NO_ENCONTRADA")

                    id_origen = res_orig.id
                    id_destino = res_dest.id

                    clase_orig_obj = next((c for c in clases_actuales if c.id == id_origen), None)
                    clase_dest_obj = next((c for c in clases_actuales if c.id == id_destino), None)
                    if not clase_orig_obj:
                        clase_orig_obj = self.clase_repo.obtener_por_id(id_origen)
                    if not clase_dest_obj:
                        clase_dest_obj = self.clase_repo.obtener_por_id(id_destino)

                    if clase_orig_obj and clase_dest_obj:
                        con_orig, con_dest = calcular_mejores_conectores(
                            clase_origen=clase_orig_obj,
                            clase_destino=clase_dest_obj,
                            relaciones_existentes=relaciones_actuales,
                            conector_origen_preferido=accion.conector_origen,
                            conector_destino_preferido=accion.conector_destino,
                        )
                    else:
                        con_orig = accion.conector_origen if accion.conector_origen in ("top", "right", "bottom", "left") else "right"
                        con_dest = accion.conector_destino if accion.conector_destino in ("top", "right", "bottom", "left") else "left"

                    id_rel = uuid4()
                    rel_temp = Relacion.crear(
                        id=id_rel,
                        id_diagrama=diagrama_id,
                        id_clase_origen=id_origen,
                        id_clase_destino=id_destino,
                        tipo_relacion=accion.tipo_relacion,
                        cardinalidad_origen=accion.cardinalidad_origen,
                        cardinalidad_destino=accion.cardinalidad_destino,
                        conector_origen=con_orig,
                        conector_destino=con_dest,
                        nombre=accion.nombre,
                    )

                    materializaciones: list[MaterializacionFKCommand] = []
                    if requiere_materializacion(rel_temp):
                        origen_muchos = _maximo(rel_temp.cardinalidad_origen) is None or _maximo(rel_temp.cardinalidad_origen) > 1
                        destino_muchos = _maximo(rel_temp.cardinalidad_destino) is None or _maximo(rel_temp.cardinalidad_destino) > 1

                        if accion.clase_fk_referencia:
                            res_fk = ResolvedorReferenciasIa.resolver_clase(
                                accion.clase_fk_referencia, clases_actuales, mapa_referencias
                            )
                            if res_fk.exito:
                                clase_fk = res_fk.id
                                clase_ref = (
                                    id_origen
                                    if (clase_fk == id_destino and id_origen != id_destino)
                                    else (id_destino if id_origen != id_destino else id_origen)
                                )
                            else:
                                clase_fk = id_origen if origen_muchos else id_destino
                                clase_ref = id_destino if origen_muchos else id_origen
                        elif rel_temp.tipo_relacion in {"herencia", "realizacion", "dependencia"}:
                            clase_fk = id_origen
                            clase_ref = id_destino
                        elif id_origen == id_destino:
                            clase_fk = id_origen
                            clase_ref = id_origen
                        elif origen_muchos != destino_muchos:
                            clase_fk = id_origen if origen_muchos else id_destino
                            clase_ref = id_destino if origen_muchos else id_origen
                        else:
                            clase_fk = id_destino
                            clase_ref = id_origen

                        pk_attr = next((a for a in self.atributo_repo.listar_por_clase(clase_ref) if a.es_llave_primaria), None)
                        if pk_attr:
                            clase_ref_obj = self.clase_repo.obtener_por_id(clase_ref)
                            clase_ref_name = (clase_ref_obj.nombre if clase_ref_obj else "origen").lower()

                            if accion.nombre_fk:
                                nombre_fk = accion.nombre_fk
                            elif id_origen == id_destino:
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
                        id_clase_origen=id_origen,
                        id_clase_destino=id_destino,
                        tipo_relacion=accion.tipo_relacion,
                        cardinalidad_origen=accion.cardinalidad_origen,
                        cardinalidad_destino=accion.cardinalidad_destino,
                        conector_origen=con_orig,
                        conector_destino=con_dest,
                        nombre=accion.nombre,
                        materializacion_fk=materializaciones if materializaciones else None,
                    )
                    rel = self.crear_relacion_use_case.execute(cmd_rel)

                    proy_rel = proyectar_relacion(
                        self.relacion_repo, self.referencia_fk_repo, rel.id
                    )
                    proy_orig = proyectar_clase(
                        self.clase_repo, self.atributo_repo, id_origen
                    )
                    proy_dest = proyectar_clase(
                        self.clase_repo, self.atributo_repo, id_destino
                    )
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
                    paso_info["estado"] = "completado"
                    paso_info["id_creado"] = str(rel.id)
                    paso_info["nombre"] = rel.nombre

                elif isinstance(accion, AccionActualizarRelacionSchema):
                    if not self.actualizar_relacion_use_case:
                        raise ValidationException("El caso de uso ActualizarRelacion no está disponible.")
                    res_r = ResolvedorReferenciasIa.resolver_relacion(
                        accion.clase_origen_referencia,
                        accion.clase_destino_referencia,
                        relaciones_actuales,
                        clases_actuales,
                        mapa_alias=mapa_referencias,
                    )
                    if not res_r.exito:
                        if res_r.es_ambiguo:
                            raise ValidationException(res_r.motivo, code="REFERENCIA_AMBIGUA")
                        raise NotFoundException(res_r.motivo, code="REFERENCIA_NO_ENCONTRADA")

                    cmd_act_r = ActualizarRelacionCommand(
                        propietario_id=usuario_id,
                        diagrama_id=diagrama_id,
                        relacion_id=res_r.id,
                        nombre=accion.nuevo_nombre,
                    )
                    rel_act = self.actualizar_relacion_use_case.execute(cmd_act_r)
                    proy_rel = proyectar_relacion(self.relacion_repo, self.referencia_fk_repo, rel_act.id)
                    efectos = construir_efectos(relaciones_actualizadas=[proy_rel])
                    emitir_evento_mutacion_confirmada(
                        diagrama_id=diagrama_id,
                        action_id=str(uuid4()),
                        tipo_operacion="RENOMBRAR_RELACION",
                        emisor_id=usuario_id,
                        efectos=efectos,
                    )
                    paso_info["estado"] = "completado"
                    paso_info["id_relacion"] = str(rel_act.id)
                    paso_info["nombre"] = rel_act.nombre

                elif isinstance(accion, AccionEliminarRelacionSchema):
                    if not self.eliminar_relacion_use_case:
                        raise ValidationException("El caso de uso EliminarRelacion no está disponible.")
                    res_r = ResolvedorReferenciasIa.resolver_relacion(
                        accion.clase_origen_referencia,
                        accion.clase_destino_referencia,
                        relaciones_actuales,
                        clases_actuales,
                        nombre_relacion=accion.nombre,
                        mapa_alias=mapa_referencias,
                    )
                    if not res_r.exito:
                        if res_r.es_ambiguo:
                            raise ValidationException(res_r.motivo, code="REFERENCIA_AMBIGUA")
                        raise NotFoundException(res_r.motivo, code="REFERENCIA_NO_ENCONTRADA")

                    cmd_elim_r = EliminarRelacionCommand(
                        propietario_id=usuario_id,
                        diagrama_id=diagrama_id,
                        relacion_id=res_r.id,
                    )
                    cierre = self.eliminar_relacion_use_case.execute(cmd_elim_r)
                    efectos = construir_efectos(
                        clases_eliminadas=list(cierre.clases_eliminadas),
                        relaciones_eliminadas=list(cierre.relaciones_eliminadas),
                        estructuras_nm_eliminadas=list(cierre.estructuras_nm_eliminadas),
                    )
                    emitir_evento_mutacion_confirmada(
                        diagrama_id=diagrama_id,
                        action_id=str(uuid4()),
                        tipo_operacion="ELIMINAR_RELACION",
                        emisor_id=usuario_id,
                        efectos=efectos,
                    )
                    paso_info["estado"] = "completado"
                    paso_info["id_eliminado"] = str(res_r.id)

                elif isinstance(accion, AccionCrearEstructuraNmSchema):
                    if not self.crear_estructura_nm_use_case or not self.estructura_nm_repo:
                        raise ValidationException("El caso de uso CrearEstructuraRelacionNm no está disponible.")
                    res_orig = ResolvedorReferenciasIa.resolver_clase(
                        accion.clase_origen_referencia, clases_actuales, mapa_referencias
                    )
                    res_dest = ResolvedorReferenciasIa.resolver_clase(
                        accion.clase_destino_referencia, clases_actuales, mapa_referencias
                    )
                    if not res_orig.exito:
                        if res_orig.es_ambiguo:
                            raise ValidationException(res_orig.motivo, code="REFERENCIA_AMBIGUA")
                        raise NotFoundException(res_orig.motivo, code="REFERENCIA_NO_ENCONTRADA")
                    if not res_dest.exito:
                        if res_dest.es_ambiguo:
                            raise ValidationException(res_dest.motivo, code="REFERENCIA_AMBIGUA")
                        raise NotFoundException(res_dest.motivo, code="REFERENCIA_NO_ENCONTRADA")

                    id_origen = res_orig.id
                    id_destino = res_dest.id

                    clase_origen_obj = self.clase_repo.obtener_por_id(id_origen)
                    clase_destino_obj = self.clase_repo.obtener_por_id(id_destino)
                    if not clase_origen_obj or not clase_destino_obj:
                        raise NotFoundException("Clases de origen o destino no encontradas en el diagrama.", code="REFERENCIA_NO_ENCONTRADA")

                    attrs_origen = self.atributo_repo.listar_por_clase(id_origen)
                    attrs_destino = self.atributo_repo.listar_por_clase(id_destino)
                    pk_origen = next((a for a in attrs_origen if a.es_llave_primaria or a.es_unico), None)
                    pk_destino = next((a for a in attrs_destino if a.es_llave_primaria or a.es_unico), None)
                    if not pk_origen or not pk_destino:
                        raise ValidationException("Las clases origen y destino deben contar con una llave primaria o única para relacionarse N:M.")

                    nombre_inter = accion.nombre_intermedia or f"{clase_origen_obj.nombre}_{clase_destino_obj.nombre}"

                    if accion.posicion:
                        pos_x = accion.posicion.x
                        pos_y = accion.posicion.y
                    else:
                        pos_x = (float(clase_origen_obj.posicion_x) + float(clase_destino_obj.posicion_x)) / 2.0
                        pos_y = ((float(clase_origen_obj.posicion_y) + float(clase_destino_obj.posicion_y)) / 2.0) + 120.0

                    id_struct = uuid4()
                    id_inter = uuid4()
                    id_pk = uuid4()
                    id_fk_orig = uuid4()
                    id_fk_dest = uuid4()
                    id_rel_orig = uuid4()
                    id_rel_dest = uuid4()
                    id_ref_orig = uuid4()
                    id_ref_dest = uuid4()
                    action_id = uuid4()

                    con_orig_nm, con_dest_nm = calcular_mejores_conectores(
                        clase_origen=clase_origen_obj,
                        clase_destino=clase_destino_obj,
                        relaciones_existentes=relaciones_actuales,
                    )

                    cmd_nm = CrearEstructuraRelacionNmCommand(
                        propietario_id=usuario_id,
                        diagrama_id=diagrama_id,
                        action_id=action_id,
                        id_estructura=id_struct,
                        id_clase_origen=id_origen,
                        id_clase_destino=id_destino,
                        id_clase_intermedia=id_inter,
                        id_atributo_inicial=id_pk,
                        id_atributo_fk_origen=id_fk_orig,
                        id_atributo_fk_destino=id_fk_dest,
                        id_relacion_origen=id_rel_orig,
                        id_relacion_destino=id_rel_dest,
                        id_referencia_fk_origen=id_ref_orig,
                        id_referencia_fk_destino=id_ref_dest,
                        id_atributo_referenciado_origen=pk_origen.id,
                        id_atributo_referenciado_destino=pk_destino.id,
                        nombre_intermedia=nombre_inter,
                        posicion_x=pos_x,
                        posicion_y=pos_y,
                        ancho=accion.ancho or 280.0,
                        conector_origen=con_orig_nm,
                        conector_destino=con_dest_nm,
                    )
                    res_nm = self.crear_estructura_nm_use_case.execute(cmd_nm, confirmar=False)

                    intermedia_id = UUID(res_nm["id_clase_intermedia"])
                    rel_orig_id = UUID(res_nm["id_relacion_origen"])
                    rel_dest_id = UUID(res_nm["id_relacion_destino"])
                    struct_id = UUID(res_nm["id"])

                    # Registrar en mapa_referencias para que crear_atributo u otras acciones subsiguientes encuentren la tabla intermedia
                    if accion.referencia_intermedia:
                        mapa_referencias[accion.referencia_intermedia.strip().lower()] = intermedia_id
                    mapa_referencias[nombre_inter.strip().lower()] = intermedia_id
                    mapa_referencias[f"{clase_origen_obj.nombre}_{clase_destino_obj.nombre}".strip().lower()] = intermedia_id
                    mapa_referencias[f"{clase_destino_obj.nombre}_{clase_origen_obj.nombre}".strip().lower()] = intermedia_id
                    mapa_referencias[str(intermedia_id).lower()] = intermedia_id
                    mapa_referencias["intermedia"] = intermedia_id
                    mapa_referencias["tabla intermedia"] = intermedia_id
                    mapa_referencias["tabla de muchos a muchos"] = intermedia_id

                    proy_inter = proyectar_clase(self.clase_repo, self.atributo_repo, intermedia_id)
                    proy_rel_orig = proyectar_relacion(self.relacion_repo, self.referencia_fk_repo, rel_orig_id)
                    proy_rel_dest = proyectar_relacion(self.relacion_repo, self.referencia_fk_repo, rel_dest_id)
                    proy_struct = proyectar_estructura_nm(self.estructura_nm_repo, struct_id)

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
                    paso_info["estado"] = "completado"
                    paso_info["id_creado"] = str(struct_id)
                    paso_info["id_clase_intermedia"] = str(intermedia_id)
                    paso_info["nombre"] = nombre_inter

                elif isinstance(accion, AccionEliminarEstructuraNmSchema):
                    if not self.eliminar_estructura_nm_use_case or not self.estructura_nm_repo:
                        raise ValidationException("El caso de uso EliminarEstructuraRelacionNm no está disponible.")
                    estructuras_nm = self.estructura_nm_repo.listar_por_diagrama(diagrama_id)
                    res_nm = ResolvedorReferenciasIa.resolver_estructura_nm(
                        accion.clase_origen_referencia,
                        accion.clase_destino_referencia,
                        estructuras_nm,
                        clases_actuales,
                        mapa_alias=mapa_referencias,
                    )
                    if not res_nm.exito:
                        if res_nm.es_ambiguo:
                            raise ValidationException(res_nm.motivo, code="REFERENCIA_AMBIGUA")
                        raise NotFoundException(res_nm.motivo, code="REFERENCIA_NO_ENCONTRADA")

                    cmd_elim_nm = EliminarEstructuraRelacionNmCommand(
                        propietario_id=usuario_id,
                        diagrama_id=diagrama_id,
                        estructura_id=res_nm.id,
                    )
                    cierre = self.eliminar_estructura_nm_use_case.execute(cmd_elim_nm)
                    efectos = construir_efectos(
                        clases_eliminadas=list(cierre.clases_eliminadas),
                        relaciones_eliminadas=list(cierre.relaciones_eliminadas),
                        estructuras_nm_eliminadas=list(cierre.estructuras_nm_eliminadas),
                    )
                    emitir_evento_mutacion_confirmada(
                        diagrama_id=diagrama_id,
                        action_id=str(uuid4()),
                        tipo_operacion="ELIMINAR_ESTRUCTURA_NM",
                        emisor_id=usuario_id,
                        efectos=efectos,
                    )
                    paso_info["estado"] = "completado"
                    paso_info["id_eliminado"] = str(res_nm.id)

                resultados_pasos.append(paso_info)

            except DomainException as err:
                logger.warning(
                    "Operación rechazada en paso %d (%s): %s [%s]",
                    indice,
                    accion.tipo,
                    err.message,
                    err.code,
                )
                if getattr(err, "code", None) == "REFERENCIA_AMBIGUA":
                    paso_info["estado"] = "aclaracion_requerida"
                else:
                    paso_info["estado"] = "rechazado"
                paso_info["motivo"] = err.message
                paso_info["error"] = err.message
                paso_info["codigo_error"] = getattr(err, "code", None)
                resultados_pasos.append(paso_info)

                # Omitir pasos posteriores de forma determinista
                for rem_idx in range(indice, len(acciones)):
                    rem_accion = acciones[rem_idx]
                    resultados_pasos.append({
                        "paso": rem_idx + 1,
                        "tipo": rem_accion.tipo,
                        "estado": "omitido",
                        "motivo": "Omitido debido a que un paso previo no se pudo completar.",
                    })
                break

            except Exception as err:
                logger.warning(
                    "Error al ejecutar paso %d (%s): %s", indice, accion.tipo, str(err)
                )
                paso_info["estado"] = "fallido"
                paso_info["error"] = str(err)
                paso_info["motivo"] = str(err)
                resultados_pasos.append(paso_info)

                # Omitir pasos posteriores de forma determinista
                for rem_idx in range(indice, len(acciones)):
                    rem_accion = acciones[rem_idx]
                    resultados_pasos.append({
                        "paso": rem_idx + 1,
                        "tipo": rem_accion.tipo,
                        "estado": "omitido",
                        "motivo": "Omitido debido a un error en un paso anterior.",
                    })
                break

        return resultados_pasos
