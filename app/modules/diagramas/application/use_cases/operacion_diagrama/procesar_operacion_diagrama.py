from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from fastapi import HTTPException

from app.modules.diagramas.application.services.cascadas_diagrama import (
    CascadasDiagramaService,
)
from app.modules.diagramas.application.services.geometria_conectores import (
    calcular_mejores_conectores,
)
from app.modules.diagramas.application.services.idempotencia_diagrama import (
    IdempotenciaDiagramaService,
)
from app.modules.diagramas.application.validaciones import (
    obtener_diagrama_autorizado,
    validar_actualizacion_atributo,
    validar_creacion_atributo,
)
from app.modules.diagramas.domain.entities.atributo import Atributo, NO_DEFINIDO, ProcedenciaAtributo
from app.modules.diagramas.domain.entities.clase import Clase
from app.modules.diagramas.domain.entities.relacion import Relacion
from app.modules.diagramas.domain.exceptions import (
    AtributoNoEncontradoException,
    ClaseNoEncontradaException,
    ClaseYaExisteException,
    DiagramaNoEncontradoException,
    NombreRelacionInvalidoException,
    OrdenAtributoFueraDeSecuenciaException,
    RelacionNoEncontradaException,
)
from app.modules.diagramas.domain.repositories.atributo_repository import AtributoRepository
from app.modules.diagramas.domain.repositories.clase_repository import ClaseRepository
from app.modules.diagramas.domain.repositories.diagrama_repository import DiagramaRepository
from app.modules.diagramas.domain.repositories.estructura_relacion_nm_repository import (
    EstructuraRelacionNmRepository,
)
from app.modules.diagramas.domain.repositories.referencia_fk_repository import (
    ReferenciaFKRepository,
)
from app.modules.diagramas.domain.repositories.relacion_repository import RelacionRepository
from app.modules.diagramas.application.use_cases.relacion.crear_relacion import (
    CrearRelacionCommand,
    CrearRelacionUseCase,
    MaterializacionFKCommand,
    AtributoFkNuevoCommand,
)
from app.modules.diagramas.application.use_cases.estructura_relacion_nm.crear_estructura_relacion_nm import (
    CrearEstructuraRelacionNmCommand,
    CrearEstructuraRelacionNmUseCase,
)
from app.modules.gestion_colaboradores.domain.repositories.colaborador_proyecto_repository import (
    ColaboradorProyectoRepository,
)
from app.modules.gestion_proyectos.domain.repositories.proyecto_repository import (
    ProyectoRepository,
)
from app.shared.application.ports import UnitOfWork


@dataclass(slots=True)
class ProcesarOperacionCommand:
    propietario_id: str
    diagrama_id: UUID
    action_id: UUID
    tipo: str
    datos: dict[str, Any]


TIPOS_VALIDOS = {
    "CREAR_CLASE",
    "ACTUALIZAR_CLASE",
    "ELIMINAR_CLASE",
    "CREAR_ATRIBUTO",
    "ACTUALIZAR_ATRIBUTO",
    "ELIMINAR_ATRIBUTO",
    "CREAR_RELACION",
    "RENOMBRAR_RELACION",
    "ELIMINAR_RELACION",
    "CREAR_ESTRUCTURA_NM",
    "ELIMINAR_ESTRUCTURA_NM",
}


class ProcesarOperacionDiagramaUseCase:
    def __init__(
        self,
        proyecto_repository: ProyectoRepository,
        diagrama_repository: DiagramaRepository,
        clase_repository: ClaseRepository,
        atributo_repository: AtributoRepository,
        relacion_repository: RelacionRepository,
        referencia_fk_repository: ReferenciaFKRepository,
        estructura_nm_repository: EstructuraRelacionNmRepository,
        idempotencia_service: IdempotenciaDiagramaService,
        uow: UnitOfWork,
        colaborador_repository: ColaboradorProyectoRepository | None = None,
    ) -> None:
        self.proyecto_repo = proyecto_repository
        self.diagrama_repo = diagrama_repository
        self.clase_repo = clase_repository
        self.atributo_repo = atributo_repository
        self.relacion_repo = relacion_repository
        self.referencia_fk_repo = referencia_fk_repository
        self.estructura_nm_repo = estructura_nm_repository
        self.idempotencia_service = idempotencia_service
        self.uow = uow
        self.colaborador_repo = colaborador_repository

    def execute(self, command: ProcesarOperacionCommand) -> dict[str, Any]:
        if command.tipo not in TIPOS_VALIDOS:
            raise HTTPException(
                status_code=400,
                detail=f"Tipo de operación desconocido: {command.tipo}",
            )

        # 1. Autorización previa antes de cualquier acción o replay
        obtener_diagrama_autorizado(
            propietario_id=command.propietario_id,
            diagrama_id=command.diagrama_id,
            proyecto_repository=self.proyecto_repo,
            diagrama_repository=self.diagrama_repo,
            colaborador_repository=self.colaborador_repo,
            exigir_edicion=True,
        )

        # 2. Huella canónica e idempotencia
        payload_canonica = {
            "tipo": command.tipo,
            "datos": command.datos,
        }
        recibo_previo = self.idempotencia_service.confirmar_o_recuperar(
            action_id=command.action_id,
            usuario_id=command.propietario_id,
            diagrama_id=command.diagrama_id,
            payload=payload_canonica,
        )
        if recibo_previo is not None:
            return recibo_previo

        # 3. Preparación de efectos y servicio de cascadas
        cascadas = CascadasDiagramaService(
            clase_repository=self.clase_repo,
            atributo_repository=self.atributo_repo,
            relacion_repository=self.relacion_repo,
            referencia_fk_repository=self.referencia_fk_repo,
            estructura_nm_repository=self.estructura_nm_repo,
        )

        clases_actualizadas: list[dict[str, Any]] = []
        clases_eliminadas: list[str] = []
        relaciones_actualizadas: list[dict[str, Any]] = []
        relaciones_eliminadas: list[str] = []
        estructuras_nm_actualizadas: list[dict[str, Any]] = []
        estructuras_nm_eliminadas: list[str] = []

        datos = command.datos

        if command.tipo == "CREAR_CLASE":
            class_id = UUID(str(datos.get("id_clase") or datos.get("classId")))
            attr_id = UUID(str(datos.get("id_atributo_inicial") or datos.get("atributoInicialId")))
            if self.clase_repo.obtener_por_id(class_id):
                raise ClaseYaExisteException()

            clase = Clase.crear(
                id=class_id,
                id_diagrama=command.diagrama_id,
                nombre=str(datos.get("nombre", "NuevaClase")),
                posicion_x=float(datos.get("posicion_x", 0.0)),
                posicion_y=float(datos.get("posicion_y", 0.0)),
                ancho=float(datos.get("ancho", 280.0)),
            )
            self.clase_repo.guardar(clase)
            attr_pk = Atributo.crear(
                id=attr_id,
                id_clase=class_id,
                nombre="id",
                tipo_dato="integer",
                orden_de_posicion=1,
                es_llave_primaria=True,
                permite_nulo=False,
                es_unico=True,
                procedencia=ProcedenciaAtributo.SISTEMA_CLASE,
            )
            self.atributo_repo.guardar(attr_pk)
            clases_actualizadas.append(self._proyectar_clase(class_id))

        elif command.tipo == "ACTUALIZAR_CLASE":
            class_id = UUID(str(datos["id_clase"]))
            clase = self.clase_repo.obtener_por_id(class_id)
            if not clase or clase.id_diagrama != command.diagrama_id:
                raise ClaseNoEncontradaException()

            nombre = datos.get("nombre")
            pos_x = datos.get("posicion_x")
            pos_y = datos.get("posicion_y")
            ancho = datos.get("ancho")

            clase.actualizar(
                nombre=nombre if (nombre is not None and nombre != clase.nombre) else None,
                posicion_x=float(pos_x) if pos_x is not None else None,
                posicion_y=float(pos_y) if pos_y is not None else None,
                ancho=float(ancho) if ancho is not None else None,
            )

            self.clase_repo.guardar(clase)
            clases_actualizadas.append(self._proyectar_clase(class_id))

        elif command.tipo == "ELIMINAR_CLASE":
            class_id = UUID(str(datos["id_clase"]))
            clase = self.clase_repo.obtener_por_id(class_id)
            if not clase or clase.id_diagrama != command.diagrama_id:
                raise ClaseNoEncontradaException()

            cierre = cascadas.cerrar_por_clase(class_id, command.diagrama_id)
            clases_eliminadas.extend(str(cid) for cid in cierre.clases_eliminadas)
            relaciones_eliminadas.extend(str(rid) for rid in cierre.relaciones_eliminadas)
            estructuras_nm_eliminadas.extend(str(nid) for nid in cierre.estructuras_nm_eliminadas)
            for cid in (cierre.clases_modificadas - cierre.clases_eliminadas):
                proj = self._proyectar_clase(cid)
                if proj:
                    clases_actualizadas.append(proj)

        elif command.tipo == "CREAR_ATRIBUTO":
            class_id = UUID(str(datos["id_clase"]))
            clase = self.clase_repo.obtener_por_id(class_id)
            if not clase or clase.id_diagrama != command.diagrama_id:
                raise ClaseNoEncontradaException()

            attr_id = UUID(str(datos.get("id_atributo") or datos.get("id")))
            existentes = self.atributo_repo.listar_por_clase(class_id)
            orden = int(datos.get("orden_de_posicion") or (existentes[-1].orden_de_posicion + 1 if existentes else 1))

            nuevo_attr = Atributo.crear(
                id=attr_id,
                id_clase=class_id,
                nombre=str(datos.get("nombre", "atributo")),
                tipo_dato=str(datos.get("tipo_dato", "integer")),
                longitud=datos.get("longitud"),
                precision=datos.get("precision"),
                escala=datos.get("escala"),
                permite_nulo=bool(datos.get("permite_nulo", True)),
                es_unico=bool(datos.get("es_unico", False)),
                valor_por_defecto=datos.get("valor_por_defecto"),
                orden_de_posicion=orden,
                es_llave_primaria=bool(datos.get("es_llave_primaria", False)),
                procedencia=ProcedenciaAtributo.MANUAL,
            )
            validar_creacion_atributo(datos=datos, atributos_existentes=existentes)
            self.atributo_repo.guardar(nuevo_attr)
            clases_actualizadas.append(self._proyectar_clase(class_id))

        elif command.tipo == "ACTUALIZAR_ATRIBUTO":
            class_id = UUID(str(datos["id_clase"]))
            attr_id = UUID(str(datos["id_atributo"]))
            clase = self.clase_repo.obtener_por_id(class_id)
            if not clase or clase.id_diagrama != command.diagrama_id:
                raise ClaseNoEncontradaException()

            attr = self.atributo_repo.obtener_por_id(attr_id)
            if not attr or attr.id_clase != class_id:
                raise AtributoNoEncontradoException()

            campos = datos.get("campos", datos)
            tiene_fk = len(self.referencia_fk_repo.listar_por_atributo(attr_id)) > 0
            validar_actualizacion_atributo(atributo=attr, datos=campos, tiene_referencia_fk=tiene_fk)

            orden = campos.get("orden_de_posicion", NO_DEFINIDO)
            attr.actualizar(**{k: v for k, v in campos.items() if k not in ("id_clase", "id_atributo", "campos")})

            if orden is not NO_DEFINIDO:
                otros = [x for x in self.atributo_repo.listar_por_clase(class_id) if x.id != attr.id]
                if attr.orden_de_posicion > len(otros) + 1:
                    raise OrdenAtributoFueraDeSecuenciaException()
                posicion = attr.orden_de_posicion
                otros.insert(posicion - 1, attr)
                for i, x in enumerate(otros, 1):
                    x.orden_de_posicion = i
                self.atributo_repo.guardar_varios(otros)
            else:
                self.atributo_repo.guardar(attr)

            clases_actualizadas.append(self._proyectar_clase(class_id))

        elif command.tipo == "ELIMINAR_ATRIBUTO":
            class_id = UUID(str(datos["id_clase"]))
            attr_id = UUID(str(datos["id_atributo"]))
            cierre = cascadas.cerrar_por_atributo(attr_id, class_id, command.diagrama_id)
            relaciones_eliminadas.extend(str(rid) for rid in cierre.relaciones_eliminadas)
            estructuras_nm_eliminadas.extend(str(nid) for nid in cierre.estructuras_nm_eliminadas)
            clases_eliminadas.extend(str(cid) for cid in cierre.clases_eliminadas)
            for cid in (cierre.clases_modificadas - cierre.clases_eliminadas):
                proj = self._proyectar_clase(cid)
                if proj:
                    clases_actualizadas.append(proj)

        elif command.tipo == "CREAR_RELACION":
            rel_id = UUID(str(datos["id_relacion"]))
            c_origen = UUID(str(datos["id_clase_origen"]))
            c_destino = UUID(str(datos["id_clase_destino"]))
            tipo_rel = str(datos["tipo_relacion"])

            mats_fk = []
            for m in datos.get("materializacion_fk", []):
                nuevo_cmd = None
                if m.get("atributo_fk_nuevo"):
                    n = m["atributo_fk_nuevo"]
                    nuevo_cmd = AtributoFkNuevoCommand(
                        id_atributo=UUID(str(n["id_atributo"])),
                        nombre=str(n["nombre"]),
                        tipo_dato=n.get("tipo_dato"),
                        longitud=n.get("longitud"),
                        precision=n.get("precision"),
                        escala=n.get("escala"),
                        permite_nulo=n.get("permite_nulo", True),
                        es_unico=n.get("es_unico", False),
                        valor_por_defecto=n.get("valor_por_defecto"),
                    )
                mats_fk.append(
                    MaterializacionFKCommand(
                        id_referencia_fk=UUID(str(m["id_referencia_fk"])),
                        id_atributo_referenciado=UUID(str(m["id_atributo_referenciado"])),
                        id_atributo_fk=UUID(str(m["id_atributo_fk"])) if m.get("id_atributo_fk") else None,
                        id_clase_fk=UUID(str(m["id_clase_fk"])) if m.get("id_clase_fk") else None,
                        atributo_fk_nuevo=nuevo_cmd,
                        on_delete=m.get("on_delete", "NO_ACTION"),
                        on_update=m.get("on_update", "NO_ACTION"),
                    )
                )

            use_case_rel = CrearRelacionUseCase(
                proyecto_repository=self.proyecto_repo,
                diagrama_repository=self.diagrama_repo,
                clase_repository=self.clase_repo,
                relacion_repository=self.relacion_repo,
                uow=self.uow,
                colaborador_repository=self.colaborador_repo,
                atributo_repository=self.atributo_repo,
                referencia_fk_repository=self.referencia_fk_repo,
            )
            con_orig = datos.get("conector_origen") or datos.get("conectorOrigen")
            con_dest = datos.get("conector_destino") or datos.get("conectorDestino")
            if not con_orig or not con_dest:
                origen_obj = self.clase_repo.obtener_por_id(c_origen)
                destino_obj = self.clase_repo.obtener_por_id(c_destino)
                if origen_obj and destino_obj:
                    rels = self.relacion_repo.listar_por_diagrama(command.diagrama_id)
                    calc_orig, calc_dest = calcular_mejores_conectores(origen_obj, destino_obj, rels, con_orig, con_dest)
                    con_orig = con_orig or calc_orig
                    con_dest = con_dest or calc_dest
                else:
                    con_orig = con_orig or "right"
                    con_dest = con_dest or "left"

            use_case_rel.execute(
                CrearRelacionCommand(
                    propietario_id=command.propietario_id,
                    diagrama_id=command.diagrama_id,
                    id_relacion=rel_id,
                    id_clase_origen=c_origen,
                    id_clase_destino=c_destino,
                    tipo_relacion=tipo_rel,
                    cardinalidad_origen=str(datos.get("cardinalidad_origen", "1")),
                    cardinalidad_destino=str(datos.get("cardinalidad_destino", "1")),
                    conector_origen=str(con_orig),
                    conector_destino=str(con_dest),
                    nombre=datos.get("nombre"),
                    materializacion_fk=mats_fk,
                ),
                confirmar=False,
            )
            relaciones_actualizadas.append(self._proyectar_relacion(rel_id))
            # Proyectar clases que recibieron nuevos atributos FK
            for mat in mats_fk:
                if mat.id_clase_fk:
                    clases_actualizadas.append(self._proyectar_clase(mat.id_clase_fk))

        elif command.tipo == "RENOMBRAR_RELACION":
            rel_id = UUID(str(datos["id_relacion"]))
            rel = self.relacion_repo.obtener_por_id(rel_id)
            if not rel or rel.id_diagrama != command.diagrama_id:
                raise RelacionNoEncontradaException()
            if rel.tipo_relacion != "asociacion":
                raise NombreRelacionInvalidoException()

            nuevo_nombre = str(datos.get("nombre", "")).strip()
            if not nuevo_nombre or len(nuevo_nombre) > 100:
                raise NombreRelacionInvalidoException()

            rel.actualizar_nombre(nuevo_nombre)
            self.relacion_repo.guardar(rel)
            relaciones_actualizadas.append(self._proyectar_relacion(rel_id))

        elif command.tipo == "ELIMINAR_RELACION":
            rel_id = UUID(str(datos["id_relacion"]))
            rel = self.relacion_repo.obtener_por_id(rel_id)
            if not rel or rel.id_diagrama != command.diagrama_id:
                raise RelacionNoEncontradaException()

            cierre = cascadas.cerrar_por_relacion(rel_id, command.diagrama_id)
            relaciones_eliminadas.extend(str(rid) for rid in cierre.relaciones_eliminadas)
            estructuras_nm_eliminadas.extend(str(nid) for nid in cierre.estructuras_nm_eliminadas)
            clases_eliminadas.extend(str(cid) for cid in cierre.clases_eliminadas)
            for cid in (cierre.clases_modificadas - cierre.clases_eliminadas):
                proj = self._proyectar_clase(cid)
                if proj:
                    clases_actualizadas.append(proj)

        elif command.tipo == "CREAR_ESTRUCTURA_NM":
            c_inter = datos.get("clase_intermedia") or datos.get("claseIntermedia") or {}
            r_orig = datos.get("relacion_origen") or datos.get("relacionOrigen") or {}
            r_dest = datos.get("relacion_destino") or datos.get("relacionDestino") or {}
            ref_orig = datos.get("referencia_fk_origen") or datos.get("referenciaFkOrigen") or {}
            ref_dest = datos.get("referencia_fk_destino") or datos.get("referenciaFkDestino") or {}

            id_struct = UUID(str(datos.get("id_estructura") or datos.get("id_estructura_nm") or datos.get("idEstructuraNm")))
            id_orig = UUID(str(datos.get("id_clase_origen") or datos.get("idClaseOrigen")))
            id_dest = UUID(str(datos.get("id_clase_destino") or datos.get("idClaseDestino")))
            id_inter = UUID(str(datos.get("id_clase_intermedia") or c_inter.get("id_clase") or c_inter.get("idClase")))
            id_pk = UUID(str(datos.get("id_atributo_inicial") or c_inter.get("id_atributo_pk") or c_inter.get("idAtributoPk")))
            id_fk_orig = UUID(str(datos.get("id_atributo_fk_origen") or ref_orig.get("id_atributo_fk") or ref_orig.get("idAtributoFk")))
            id_fk_dest = UUID(str(datos.get("id_atributo_fk_destino") or ref_dest.get("id_atributo_fk") or ref_dest.get("idAtributoFk")))
            id_rel_orig = UUID(str(datos.get("id_relacion_origen") or r_orig.get("id_relacion") or r_orig.get("idRelacion")))
            id_rel_dest = UUID(str(datos.get("id_relacion_destino") or r_dest.get("id_relacion") or r_dest.get("idRelacion")))
            id_ref_orig = UUID(str(datos.get("id_referencia_fk_origen") or ref_orig.get("id_referencia_fk") or ref_orig.get("idReferenciaFk")))
            id_ref_dest = UUID(str(datos.get("id_referencia_fk_destino") or ref_dest.get("id_referencia_fk") or ref_dest.get("idReferenciaFk")))

            raw_ref_attr_orig = datos.get("id_atributo_referenciado_origen") or ref_orig.get("id_atributo_referenciado") or ref_orig.get("idAtributoReferenciado")
            if raw_ref_attr_orig:
                id_ref_attr_orig = UUID(str(raw_ref_attr_orig))
            else:
                attrs_orig = self.atributo_repo.listar_por_clase(id_orig)
                pk_attr = next((a for a in attrs_orig if a.es_llave_primaria), None)
                id_ref_attr_orig = pk_attr.id if pk_attr else None

            raw_ref_attr_dest = datos.get("id_atributo_referenciado_destino") or ref_dest.get("id_atributo_referenciado") or ref_dest.get("idAtributoReferenciado")
            if raw_ref_attr_dest:
                id_ref_attr_dest = UUID(str(raw_ref_attr_dest))
            else:
                attrs_dest = self.atributo_repo.listar_por_clase(id_dest)
                pk_attr = next((a for a in attrs_dest if a.es_llave_primaria), None)
                id_ref_attr_dest = pk_attr.id if pk_attr else None

            nombre_inter = str(datos.get("nombre_intermedia") or c_inter.get("nombre") or "Intermedia")
            pos_x = float(datos.get("posicion_x") or c_inter.get("posicion_x") or c_inter.get("posicionX") or 0.0)
            pos_y = float(datos.get("posicion_y") or c_inter.get("posicion_y") or c_inter.get("posicionY") or 0.0)
            ancho = float(datos.get("ancho") or c_inter.get("ancho") or 280.0)

            use_case_nm = CrearEstructuraRelacionNmUseCase(
                proyecto_repository=self.proyecto_repo,
                diagrama_repository=self.diagrama_repo,
                clase_repository=self.clase_repo,
                atributo_repository=self.atributo_repo,
                relacion_repository=self.relacion_repo,
                referencia_fk_repository=self.referencia_fk_repo,
                estructura_repository=self.estructura_nm_repo,
                idempotencia=self.idempotencia_service,
                uow=self.uow,
                colaborador_repository=self.colaborador_repo,
            )
            con_orig = r_orig.get("conector_origen") or r_orig.get("conectorOrigen") or datos.get("conector_origen") or datos.get("conectorOrigen")
            con_dest = r_dest.get("conector_origen") or r_dest.get("conectorOrigen") or datos.get("conector_destino") or datos.get("conectorDestino")

            res_nm = use_case_nm.execute(
                CrearEstructuraRelacionNmCommand(
                    propietario_id=command.propietario_id,
                    diagrama_id=command.diagrama_id,
                    action_id=command.action_id,
                    id_estructura=id_struct,
                    id_clase_origen=id_orig,
                    id_clase_destino=id_dest,
                    id_clase_intermedia=id_inter,
                    id_atributo_inicial=id_pk,
                    id_atributo_fk_origen=id_fk_orig,
                    id_atributo_fk_destino=id_fk_dest,
                    id_relacion_origen=id_rel_orig,
                    id_relacion_destino=id_rel_dest,
                    id_referencia_fk_origen=id_ref_orig,
                    id_referencia_fk_destino=id_ref_dest,
                    id_atributo_referenciado_origen=id_ref_attr_orig,
                    id_atributo_referenciado_destino=id_ref_attr_dest,
                    nombre_intermedia=nombre_inter,
                    posicion_x=pos_x,
                    posicion_y=pos_y,
                    ancho=ancho,
                    conector_origen=con_orig,
                    conector_destino=con_dest,
                ),
                confirmar=False,
            )
            intermedia_id = UUID(res_nm["id_clase_intermedia"])
            rel_orig_id = UUID(res_nm["id_relacion_origen"])
            rel_dest_id = UUID(res_nm["id_relacion_destino"])
            struct_id = UUID(res_nm["id"])

            clases_actualizadas.append(self._proyectar_clase(intermedia_id))
            relaciones_actualizadas.append(self._proyectar_relacion(rel_orig_id))
            relaciones_actualizadas.append(self._proyectar_relacion(rel_dest_id))
            estructuras_nm_actualizadas.append(self._proyectar_estructura_nm(struct_id))

        elif command.tipo == "ELIMINAR_ESTRUCTURA_NM":
            struct_id = UUID(str(datos.get("id_estructura") or datos.get("id_estructura_nm") or datos.get("idEstructuraNm")))
            cierre = cascadas.cerrar_por_estructura_nm(struct_id, command.diagrama_id)
            estructuras_nm_eliminadas.extend(str(nid) for nid in cierre.estructuras_nm_eliminadas)
            clases_eliminadas.extend(str(cid) for cid in cierre.clases_eliminadas)
            relaciones_eliminadas.extend(str(rid) for rid in cierre.relaciones_eliminadas)
            for cid in (cierre.clases_modificadas - cierre.clases_eliminadas):
                proj = self._proyectar_clase(cid)
                if proj:
                    clases_actualizadas.append(proj)

        # Deduplicar clases_actualizadas y relaciones_actualizadas por id
        clases_dict = {c["id"]: c for c in clases_actualizadas if c and c["id"] not in clases_eliminadas}
        relaciones_dict = {r["id"]: r for r in relaciones_actualizadas if r and r["id"] not in relaciones_eliminadas}
        estructuras_dict = {s["id"]: s for s in estructuras_nm_actualizadas if s and s["id"] not in estructuras_nm_eliminadas}

        recibo = {
            "action_id": str(command.action_id),
            "id_diagrama": str(command.diagrama_id),
            "tipo": command.tipo,
            "efectos": {
                "clases_actualizadas": list(clases_dict.values()),
                "clases_eliminadas": list(set(clases_eliminadas)),
                "relaciones_actualizadas": list(relaciones_dict.values()),
                "relaciones_eliminadas": list(set(relaciones_eliminadas)),
                "estructuras_nm_actualizadas": list(estructuras_dict.values()),
                "estructuras_nm_eliminadas": list(set(estructuras_nm_eliminadas)),
            },
        }

        # 4. Registrar confirmación y confirmar de forma atómica en el mismo commit
        self.idempotencia_service.registrar_confirmacion(
            action_id=command.action_id,
            usuario_id=command.propietario_id,
            diagrama_id=command.diagrama_id,
            payload=payload_canonica,
            respuesta=recibo,
        )
        self.uow.commit()

        try:
            from app.core.dependencies import get_event_bus
            from app.modules.diagramas.domain.events.operacion_diagrama_confirmada import (
                OperacionDiagramaConfirmada,
            )

            get_event_bus().publish(
                OperacionDiagramaConfirmada(
                    diagrama_id=command.diagrama_id,
                    action_id=str(command.action_id),
                    tipo_operacion=command.tipo,
                    emisor_id=command.propietario_id,
                    efectos=recibo.get("efectos", {}),
                )
            )
        except Exception:
            pass

        return recibo

    def _proyectar_clase(self, clase_id: UUID) -> dict[str, Any] | None:
        clase = self.clase_repo.obtener_por_id(clase_id)
        if not clase:
            return None
        atributos = self.atributo_repo.listar_por_clase(clase_id)
        return {
            "id": str(clase.id),
            "id_diagrama": str(clase.id_diagrama),
            "nombre": clase.nombre,
            "posicion_x": float(clase.posicion_x),
            "posicion_y": float(clase.posicion_y),
            "ancho": float(clase.ancho),
            "atributos": [
                {
                    "id": str(a.id),
                    "id_clase": str(a.id_clase),
                    "nombre": a.nombre,
                    "tipo_dato": a.tipo_dato,
                    "longitud": a.longitud,
                    "precision": a.precision,
                    "escala": a.escala,
                    "permite_nulo": a.permite_nulo,
                    "es_unico": a.es_unico,
                    "valor_por_defecto": a.valor_por_defecto,
                    "orden_de_posicion": a.orden_de_posicion,
                    "es_llave_primaria": a.es_llave_primaria,
                    "procedencia": a.procedencia.value if hasattr(a.procedencia, "value") else str(a.procedencia),
                }
                for a in atributos
            ],
        }

    def _proyectar_relacion(self, relacion_id: UUID) -> dict[str, Any] | None:
        rel = self.relacion_repo.obtener_por_id(relacion_id)
        if not rel:
            return None
        referencias = self.referencia_fk_repo.listar_por_relacion(relacion_id)
        return {
            "id": str(rel.id),
            "id_diagrama": str(rel.id_diagrama),
            "id_clase_origen": str(rel.id_clase_origen),
            "id_clase_destino": str(rel.id_clase_destino),
            "tipo_relacion": rel.tipo_relacion,
            "cardinalidad_origen": rel.cardinalidad_origen,
            "cardinalidad_destino": rel.cardinalidad_destino,
            "conector_origen": rel.conector_origen,
            "conector_destino": rel.conector_destino,
            "nombre": rel.nombre,
            "referencias_fk": [
                {
                    "id": str(r.id),
                    "id_relacion": str(r.id_relacion),
                    "id_atributo_fk": str(r.id_atributo_fk),
                    "id_atributo_referenciado": str(r.id_atributo_referenciado),
                    "on_delete": r.on_delete,
                    "on_update": r.on_update,
                }
                for r in referencias
            ],
        }

    def _proyectar_estructura_nm(self, struct_id: UUID) -> dict[str, Any] | None:
        nm = self.estructura_nm_repo.obtener_por_id(struct_id)
        if not nm:
            return None
        return {
            "id": str(nm.id),
            "id_diagrama": str(nm.id_diagrama),
            "id_clase_origen": str(nm.id_clase_origen),
            "id_clase_destino": str(nm.id_clase_destino),
            "id_clase_intermedia": str(nm.id_clase_intermedia),
            "id_relacion_origen": str(nm.id_relacion_origen),
            "id_relacion_destino": str(nm.id_relacion_destino),
        }
