from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from app.modules.diagramas.domain.entities.atributo import ProcedenciaAtributo
from app.modules.diagramas.domain.exceptions import (
    MaterializacionRelacionRequeridaException,
    LlavePrimariaProtegidaException,
)
from app.modules.diagramas.domain.repositories.atributo_repository import AtributoRepository
from app.modules.diagramas.domain.repositories.clase_repository import ClaseRepository
from app.modules.diagramas.domain.repositories.estructura_relacion_nm_repository import (
    EstructuraRelacionNmRepository,
)
from app.modules.diagramas.domain.repositories.referencia_fk_repository import (
    ReferenciaFKRepository,
)
from app.modules.diagramas.domain.repositories.relacion_repository import RelacionRepository
from app.modules.diagramas.application.use_cases.relacion.materializacion import (
    asegurar_materializacion_valida,
)


@dataclass
class CierreCascadaResultado:
    clases_eliminadas: set[UUID] = field(default_factory=set)
    relaciones_eliminadas: set[UUID] = field(default_factory=set)
    atributos_eliminados: set[UUID] = field(default_factory=set)
    referencias_eliminadas: set[UUID] = field(default_factory=set)
    estructuras_nm_eliminadas: set[UUID] = field(default_factory=set)


class CascadasDiagramaService:
    def __init__(
        self,
        clase_repository: ClaseRepository,
        atributo_repository: AtributoRepository,
        relacion_repository: RelacionRepository,
        referencia_fk_repository: ReferenciaFKRepository,
        estructura_nm_repository: EstructuraRelacionNmRepository | None = None,
    ) -> None:
        self.clase_repo = clase_repository
        self.atributo_repo = atributo_repository
        self.relacion_repo = relacion_repository
        self.referencia_fk_repo = referencia_fk_repository
        self.estructura_nm_repo = estructura_nm_repository

    def cerrar_por_clase(
        self,
        clase_id: UUID,
        diagrama_id: UUID,
        resultado: CierreCascadaResultado | None = None,
    ) -> CierreCascadaResultado:
        if resultado is None:
            resultado = CierreCascadaResultado()

        if clase_id in resultado.clases_eliminadas:
            return resultado
        resultado.clases_eliminadas.add(clase_id)

        # 1. Estructuras N:M donde participa la clase
        if self.estructura_nm_repo is not None:
            todas_nm = self.estructura_nm_repo.listar_por_diagrama(diagrama_id)
            for nm in todas_nm:
                if nm.id in resultado.estructuras_nm_eliminadas:
                    continue
                if (
                    nm.id_clase_intermedia == clase_id
                    or nm.id_clase_origen == clase_id
                    or nm.id_clase_destino == clase_id
                ):
                    self.cerrar_por_estructura_nm(nm.id, diagrama_id, resultado)

        # 2. Relaciones entrantes o salientes de esta clase
        relaciones = self.relacion_repo.listar_por_diagrama(diagrama_id)
        for rel in relaciones:
            if rel.id in resultado.relaciones_eliminadas:
                continue
            if rel.id_clase_origen == clase_id or rel.id_clase_destino == clase_id:
                self.cerrar_por_relacion(rel.id, diagrama_id, resultado)

        # 3. Atributos de la clase
        atributos = self.atributo_repo.listar_por_clase(clase_id)
        for attr in atributos:
            if attr.id not in resultado.atributos_eliminados:
                resultado.atributos_eliminados.add(attr.id)
                for ref in self.referencia_fk_repo.listar_por_atributo(attr.id):
                    if ref.id not in resultado.referencias_eliminadas:
                        resultado.referencias_eliminadas.add(ref.id)
                        self.referencia_fk_repo.eliminar(ref.id)
                self.atributo_repo.eliminar(attr.id)

        # 4. Eliminar la clase
        self.clase_repo.eliminar(clase_id)
        return resultado

    def cerrar_por_relacion(
        self,
        relacion_id: UUID,
        diagrama_id: UUID,
        resultado: CierreCascadaResultado | None = None,
    ) -> CierreCascadaResultado:
        if resultado is None:
            resultado = CierreCascadaResultado()

        # Si esta relación forma parte de una estructura N:M, cerrar toda la estructura
        if self.estructura_nm_repo is not None:
            todas_nm = self.estructura_nm_repo.listar_por_diagrama(diagrama_id)
            for nm in todas_nm:
                if nm.id in resultado.estructuras_nm_eliminadas:
                    continue
                if nm.id_relacion_origen == relacion_id or nm.id_relacion_destino == relacion_id:
                    self.cerrar_por_estructura_nm(nm.id, diagrama_id, resultado)
                    return resultado

        if relacion_id in resultado.relaciones_eliminadas:
            return resultado
        resultado.relaciones_eliminadas.add(relacion_id)

        # Referencias de la relación
        referencias = self.referencia_fk_repo.listar_por_relacion(relacion_id)
        for ref in referencias:
            if ref.id not in resultado.referencias_eliminadas:
                resultado.referencias_eliminadas.add(ref.id)
                self.referencia_fk_repo.eliminar(ref.id)
                self._limpiar_atributo_fk_si_exclusivo(ref.id_atributo_fk, resultado)

        self.relacion_repo.eliminar(relacion_id)
        return resultado

    def cerrar_por_referencia_fk(
        self,
        referencia_id: UUID,
        relacion_id: UUID,
        diagrama_id: UUID,
        resultado: CierreCascadaResultado | None = None,
    ) -> CierreCascadaResultado:
        if resultado is None:
            resultado = CierreCascadaResultado()

        if referencia_id in resultado.referencias_eliminadas:
            return resultado
        resultado.referencias_eliminadas.add(referencia_id)

        ref = self.referencia_fk_repo.obtener_por_id(referencia_id)
        self.referencia_fk_repo.eliminar(referencia_id)

        if ref is not None:
            self._limpiar_atributo_fk_si_exclusivo(ref.id_atributo_fk, resultado)

        # Verificar si la relación pierde materialización
        relacion = self.relacion_repo.obtener_por_id(relacion_id)
        if relacion is not None and relacion.id not in resultado.relaciones_eliminadas:
            refs_restantes = [
                r for r in self.referencia_fk_repo.listar_por_relacion(relacion.id)
                if r.id not in resultado.referencias_eliminadas
            ]
            try:
                asegurar_materializacion_valida(
                    relacion,
                    refs_restantes,
                    self.atributo_repo.obtener_por_id,
                )
            except MaterializacionRelacionRequeridaException:
                self.cerrar_por_relacion(relacion.id, diagrama_id, resultado)

        return resultado

    def cerrar_por_atributo(
        self,
        atributo_id: UUID,
        clase_id: UUID,
        diagrama_id: UUID,
        resultado: CierreCascadaResultado | None = None,
    ) -> CierreCascadaResultado:
        if resultado is None:
            resultado = CierreCascadaResultado()

        if atributo_id in resultado.atributos_eliminados:
            return resultado

        attr = self.atributo_repo.obtener_por_id(atributo_id)
        if attr is None:
            return resultado

        if attr.procedencia == ProcedenciaAtributo.SISTEMA_CLASE or attr.es_llave_primaria:
            raise LlavePrimariaProtegidaException()

        resultado.atributos_eliminados.add(atributo_id)

        # Limpiar todas las referencias FK asociadas a este atributo (como origen o destino)
        refs = self.referencia_fk_repo.listar_por_atributo(atributo_id)
        for ref in refs:
            if ref.id not in resultado.referencias_eliminadas:
                self.cerrar_por_referencia_fk(ref.id, ref.id_relacion, diagrama_id, resultado)

        self.atributo_repo.eliminar(atributo_id)

        # Reordenar atributos restantes en la clase
        restantes = [
            a for a in self.atributo_repo.listar_por_clase(clase_id)
            if a.id not in resultado.atributos_eliminados
        ]
        for i, a in enumerate(restantes, 1):
            a.orden_de_posicion = i
        if restantes:
            self.atributo_repo.guardar_varios(restantes)

        return resultado

    def cerrar_por_estructura_nm(
        self,
        estructura_id: UUID,
        diagrama_id: UUID,
        resultado: CierreCascadaResultado | None = None,
    ) -> CierreCascadaResultado:
        if resultado is None:
            resultado = CierreCascadaResultado()

        if estructura_id in resultado.estructuras_nm_eliminadas:
            return resultado
        resultado.estructuras_nm_eliminadas.add(estructura_id)

        if self.estructura_nm_repo is None:
            return resultado

        estructura = self.estructura_nm_repo.obtener_por_id(estructura_id)
        if estructura is None:
            return resultado

        # 1. Eliminar relaciones internas (origen e intermedia, destino e intermedia)
        for rel_id in (estructura.id_relacion_origen, estructura.id_relacion_destino):
            if rel_id not in resultado.relaciones_eliminadas:
                resultado.relaciones_eliminadas.add(rel_id)
                for ref in self.referencia_fk_repo.listar_por_relacion(rel_id):
                    if ref.id not in resultado.referencias_eliminadas:
                        resultado.referencias_eliminadas.add(ref.id)
                        self.referencia_fk_repo.eliminar(ref.id)
                        self._limpiar_atributo_fk_si_exclusivo(ref.id_atributo_fk, resultado)
                self.relacion_repo.eliminar(rel_id)

        # 2. Relaciones EXTERNAS conectadas a la clase intermedia
        relaciones_diag = self.relacion_repo.listar_por_diagrama(diagrama_id)
        for rel in relaciones_diag:
            if rel.id in resultado.relaciones_eliminadas:
                continue
            if (
                rel.id_clase_origen == estructura.id_clase_intermedia
                or rel.id_clase_destino == estructura.id_clase_intermedia
            ):
                self.cerrar_por_relacion(rel.id, diagrama_id, resultado)

        # 3. Eliminar todos los atributos de la clase intermedia y la clase intermedia
        if estructura.id_clase_intermedia not in resultado.clases_eliminadas:
            resultado.clases_eliminadas.add(estructura.id_clase_intermedia)
            attrs_intermedia = self.atributo_repo.listar_por_clase(estructura.id_clase_intermedia)
            for a in attrs_intermedia:
                if a.id not in resultado.atributos_eliminados:
                    resultado.atributos_eliminados.add(a.id)
                    for ref in self.referencia_fk_repo.listar_por_atributo(a.id):
                        if ref.id not in resultado.referencias_eliminadas:
                            resultado.referencias_eliminadas.add(ref.id)
                            self.referencia_fk_repo.eliminar(ref.id)
                    self.atributo_repo.eliminar(a.id)
            self.clase_repo.eliminar(estructura.id_clase_intermedia)

        # 4. Eliminar el registro de estructura N:M
        self.estructura_nm_repo.eliminar(estructura_id)
        return resultado

    def cerrar_por_diagrama(
        self,
        diagrama_id: UUID,
        resultado: CierreCascadaResultado | None = None,
    ) -> CierreCascadaResultado:
        if resultado is None:
            resultado = CierreCascadaResultado()

        if self.estructura_nm_repo is not None:
            for nm in self.estructura_nm_repo.listar_por_diagrama(diagrama_id):
                self.cerrar_por_estructura_nm(nm.id, diagrama_id, resultado)

        if self.referencia_fk_repo is not None:
            self.referencia_fk_repo.eliminar_por_diagrama(diagrama_id)

        if self.relacion_repo is not None:
            self.relacion_repo.eliminar_por_diagrama(diagrama_id)

        self.atributo_repo.eliminar_por_diagrama(diagrama_id)
        self.clase_repo.eliminar_por_diagrama(diagrama_id)
        return resultado

    def _limpiar_atributo_fk_si_exclusivo(
        self,
        atributo_id: UUID,
        resultado: CierreCascadaResultado,
    ) -> None:
        if atributo_id in resultado.atributos_eliminados:
            return
        atributo = self.atributo_repo.obtener_por_id(atributo_id)
        if atributo is None or atributo.procedencia != ProcedenciaAtributo.SISTEMA_FK:
            return

        otras_refs = [
            r for r in self.referencia_fk_repo.listar_por_atributo(atributo_id)
            if r.id not in resultado.referencias_eliminadas
        ]
        if not otras_refs:
            resultado.atributos_eliminados.add(atributo_id)
            self.atributo_repo.eliminar(atributo_id)
            restantes = [
                a for a in self.atributo_repo.listar_por_clase(atributo.id_clase)
                if a.id not in resultado.atributos_eliminados
            ]
            for i, a in enumerate(restantes, 1):
                a.orden_de_posicion = i
            if restantes:
                self.atributo_repo.guardar_varios(restantes)
