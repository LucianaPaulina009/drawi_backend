from __future__ import annotations

import logging
from typing import Any
from uuid import UUID, uuid4

from app.modules.diagramas.application.services.notificador_colaboracion import (
    construir_efectos,
    emitir_evento_mutacion_confirmada,
    proyectar_clase,
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
from app.modules.diagramas.domain.entities.relacion import Relacion
from app.modules.diagramas.domain.repositories.atributo_repository import (
    AtributoRepository,
)
from app.modules.diagramas.domain.repositories.clase_repository import ClaseRepository
from app.modules.diagramas.domain.repositories.referencia_fk_repository import (
    ReferenciaFKRepository,
)
from app.modules.diagramas.domain.repositories.relacion_repository import (
    RelacionRepository,
)
from app.modules.inteligencia_artificial.application.services.validador_respuesta_ia import (
    AccionCrearAtributoSchema,
    AccionCrearClaseSchema,
    AccionCrearRelacionSchema,
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
    ) -> None:
        self.crear_clase_use_case = crear_clase_use_case
        self.atributo_use_case = atributo_use_case
        self.crear_relacion_use_case = crear_relacion_use_case
        self.clase_repo = clase_repository
        self.atributo_repo = atributo_repository
        self.relacion_repo = relacion_repository
        self.referencia_fk_repo = referencia_fk_repository

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

                elif isinstance(accion, AccionCrearAtributoSchema):
                    ref_clase = accion.clase_referencia.strip().lower()
                    id_clase = mapa_referencias.get(ref_clase)
                    if not id_clase:
                        raise ValueError(
                            f"No se pudo resolver la clase de referencia '{accion.clase_referencia}'."
                        )

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

                elif isinstance(accion, AccionCrearRelacionSchema):
                    ref_orig = accion.clase_origen_referencia.strip().lower()
                    ref_dest = accion.clase_destino_referencia.strip().lower()
                    id_origen = mapa_referencias.get(ref_orig)
                    id_destino = mapa_referencias.get(ref_dest)

                    if not id_origen or not id_destino:
                        raise ValueError(
                            f"No se pudieron resolver las clases para la relación '{ref_orig}' -> '{ref_dest}'."
                        )

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
                        if rel_temp.tipo_relacion in {"herencia", "realizacion", "dependencia"}:
                            clase_fk = id_origen
                            clase_ref = id_destino
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
                            nombre_fk = f"id_{clase_ref_name}"
                            attrs_en_fk = self.atributo_repo.listar_por_clase(clase_fk)
                            attr_existente = next((a for a in attrs_en_fk if a.nombre.lower() == nombre_fk), None)
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

                resultados_pasos.append(paso_info)

            except Exception as err:
                logger.warning(
                    "Error al ejecutar paso %d (%s): %s", indice, accion.tipo, str(err)
                )
                paso_info["estado"] = "fallido"
                paso_info["error"] = str(err)
                resultados_pasos.append(paso_info)
                # Detener dependencias y pasos subsecuentes; mantener los ya confirmados
                break

        return resultados_pasos
