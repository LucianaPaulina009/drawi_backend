from __future__ import annotations

from uuid import UUID

from app.modules.diagramas.application.queries.diagrama.obtener_diagrama import (
    ObtenerDiagramaCompletoQueryHandler,
    ObtenerDiagramaQuery,
)
from app.modules.diagramas.application.queries.dtos import (
    DiagramaDetalleDTO,
)
from app.modules.generacion_backend.application.dtos.diagrama_generable_dto import (
    AtributoGenerable,
    ClaseGenerable,
    DiagramaGenerable,
    EstructuraRelacionNmGenerable,
    ReferenciaFKGenerable,
    RelacionGenerable,
)


class ObtenerDiagramaGenerableQueryHandler:
    """Obtiene un snapshot inmutable DiagramaGenerable a partir del backend de diagramas."""

    def __init__(
        self,
        query_handler_completo: ObtenerDiagramaCompletoQueryHandler,
    ) -> None:
        self.query_handler_completo = query_handler_completo

    def execute(self, *, proyecto_id: UUID, diagrama_id: UUID, usuario_id: str) -> DiagramaGenerable:
        query = ObtenerDiagramaQuery(
            proyecto_id=proyecto_id,
            diagrama_id=diagrama_id,
            usuario_id=usuario_id,
        )
        detalle: DiagramaDetalleDTO = self.query_handler_completo.execute(query)
        return self._convertir_a_generable(detalle)

    def _convertir_a_generable(self, detalle: DiagramaDetalleDTO) -> DiagramaGenerable:
        clases_generables = []
        for c in detalle.clases:
            atributos_generables = [
                AtributoGenerable(
                    id=a.id,
                    id_clase=a.id_clase,
                    tipo_dato=a.tipo_dato,
                    nombre=a.nombre,
                    longitud=a.longitud,
                    precision=a.precision,
                    escala=a.escala,
                    es_llave_primaria=a.es_llave_primaria,
                    permite_nulo=a.permite_nulo,
                    es_unico=a.es_unico,
                    valor_por_defecto=a.valor_por_defecto,
                    orden_de_posicion=a.orden_de_posicion,
                    procedencia=a.procedencia,
                )
                for a in c.atributos
            ]
            clases_generables.append(
                ClaseGenerable(
                    id=c.id,
                    id_diagrama=c.id_diagrama,
                    nombre=c.nombre,
                    posicion_x=c.posicion_x,
                    posicion_y=c.posicion_y,
                    ancho=c.ancho,
                    atributos=tuple(atributos_generables),
                )
            )

        relaciones_generables = []
        for r in detalle.relaciones:
            referencias = [
                ReferenciaFKGenerable(
                    id=rf.id,
                    id_relacion=rf.id_relacion,
                    id_atributo_fk=rf.id_atributo_fk,
                    id_atributo_referenciado=rf.id_atributo_referenciado,
                    on_delete=rf.on_delete,
                    on_update=rf.on_update,
                )
                for rf in r.referencias_fk
            ]
            relaciones_generables.append(
                RelacionGenerable(
                    id=r.id,
                    id_diagrama=r.id_diagrama,
                    id_clase_origen=r.id_clase_origen,
                    id_clase_destino=r.id_clase_destino,
                    tipo_relacion=r.tipo_relacion,
                    cardinalidad_origen=r.cardinalidad_origen,
                    cardinalidad_destino=r.cardinalidad_destino,
                    conector_origen=r.conector_origen,
                    conector_destino=r.conector_destino,
                    nombre=r.nombre,
                    referencias_fk=tuple(referencias),
                )
            )

        ids_clases_presentes = {c.id for c in detalle.clases}
        estructuras_nm = [
            EstructuraRelacionNmGenerable(
                id=e.id,
                id_diagrama=e.id_diagrama,
                id_clase_origen=e.id_clase_origen,
                id_clase_destino=e.id_clase_destino,
                id_clase_intermedia=e.id_clase_intermedia,
                id_relacion_origen=e.id_relacion_origen,
                id_relacion_destino=e.id_relacion_destino,
            )
            for e in detalle.estructuras_nm
            if e.id_clase_intermedia in ids_clases_presentes
            and e.id_clase_origen in ids_clases_presentes
            and e.id_clase_destino in ids_clases_presentes
        ]

        return DiagramaGenerable(
            id=detalle.id,
            id_proyecto=detalle.id_proyecto,
            nombre=detalle.nombre,
            numero=detalle.numero,
            clases=tuple(clases_generables),
            relaciones=tuple(relaciones_generables),
            estructuras_nm=tuple(estructuras_nm),
        )
