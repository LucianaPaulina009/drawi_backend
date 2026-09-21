from __future__ import annotations

import json
from uuid import UUID

from app.modules.diagramas.application.queries.diagrama.obtener_diagrama import (
    ObtenerDiagramaCompletoQueryHandler,
    ObtenerDiagramaQuery,
)
from app.modules.diagramas.application.queries.dtos import DiagramaDetalleDTO
from app.modules.inteligencia_artificial.domain.entities.interaccion_ia import (
    InteraccionIa,
)
from app.modules.inteligencia_artificial.domain.repositories.interaccion_ia_repository import (
    InteraccionIaRepository,
)


class ConstructorContextoDiagrama:
    """Construye el contexto estructural del diagrama y el historial conversacional reciente para el modelo IA."""

    def __init__(
        self,
        query_diagrama: ObtenerDiagramaCompletoQueryHandler,
        interaccion_repo: InteraccionIaRepository,
    ) -> None:
        self.query_diagrama = query_diagrama
        self.interaccion_repo = interaccion_repo

    def construir_contexto(
        self,
        *,
        proyecto_id: UUID,
        diagrama_id: UUID,
        usuario_id: str,
        limite_historial: int = 10,
    ) -> str:
        # 1. Obtener el estado estructural autorizado actual del diagrama
        diagrama_dto: DiagramaDetalleDTO = self.query_diagrama.execute(
            ObtenerDiagramaQuery(
                proyecto_id=proyecto_id,
                diagrama_id=diagrama_id,
                usuario_id=usuario_id,
            )
        )

        # 2. Resumir la estructura existente del diagrama
        estructura = {
            "diagrama": {
                "id": str(diagrama_dto.id),
                "nombre": diagrama_dto.nombre,
                "numero": diagrama_dto.numero,
            },
            "clases": [
                {
                    "id": str(c.id),
                    "nombre": c.nombre,
                    "posicion": {"x": c.posicion_x, "y": c.posicion_y},
                    "atributos": [
                        {
                            "id": str(a.id),
                            "nombre": a.nombre,
                            "tipo_dato": a.tipo_dato,
                            "es_llave_primaria": a.es_llave_primaria,
                            "permite_nulo": a.permite_nulo,
                            "es_unico": a.es_unico,
                        }
                        for a in c.atributos
                    ],
                }
                for c in diagrama_dto.clases
            ],
            "relaciones": [
                {
                    "id": str(r.id),
                    "nombre": r.nombre,
                    "id_clase_origen": str(r.id_clase_origen),
                    "id_clase_destino": str(r.id_clase_destino),
                    "tipo_relacion": r.tipo_relacion,
                    "cardinalidad_origen": r.cardinalidad_origen,
                    "cardinalidad_destino": r.cardinalidad_destino,
                }
                for r in diagrama_dto.relaciones
            ],
        }

        # 3. Obtener historial reciente del mismo diagrama
        interacciones: list[InteraccionIa] = self.interaccion_repo.listar_por_diagrama(
            id_diagrama=diagrama_id,
            limite=limite_historial,
        )
        historial = [
            {
                "autor_id": i.id_usuario,
                "usuario": i.entrada_usuario or "",
                "drawi": i.respuesta_ia or "",
                "estado": i.estado.value if hasattr(i.estado, "value") else str(i.estado),
            }
            for i in interacciones
            if i.estado.value == "completado" or str(i.estado) == "completado"
        ]

        # 4. Construir el prompt de sistema estructurado
        prompt_sistema = f"""Eres DRAWI, el asistente inteligente de modelado de bases de datos relacionales y diagramas UML/ER de Drawi App.
Tu función es ayudar a los usuarios respondiendo preguntas sobre diseño de bases de datos y, cuando el usuario lo solicite expresamente, generar o estructurar elementos en el diagrama (clases/tablas, atributos y relaciones).

REGLAS OBLIGATORIAS:
1. Responde SIEMPRE en formato JSON válido con la siguiente estructura exacta:
{{
  "respuesta_usuario": "Texto explicativo cordial y claro en español describiendo lo realizado o respondiendo a la consulta.",
  "acciones": []
}}
2. Si el usuario solo está saludando, preguntando algo conceptual o no solicita crear nada en el lienzo, "acciones" DEBE ser una lista vacía `[]`.
3. Cuando el usuario solicite crear elementos, puedes incluir acciones de los siguientes tipos:
   - Crear clase:
     {{
       "tipo": "crear_clase",
       "referencia": "alias_simbolico_unico",
       "nombre": "NombreClase",
       "posicion": {{ "x": 300, "y": 200 }}
     }}
   - Crear atributo:
     {{
       "tipo": "crear_atributo",
       "clase_referencia": "alias_simbolico_o_uuid_existente",
       "nombre": "nombre_campo",
       "tipo_dato": "varchar",  // tipos admitidos: integer, varchar, text, boolean, decimal, date, timestamp, uuid, float
       "longitud": 100,         // opcional para varchar
       "es_llave_primaria": false,
       "permite_nulo": true,
       "es_unico": false
     }}
   - Crear relación:
     {{
       "tipo": "crear_relacion",
       "clase_origen_referencia": "alias_simbolico_o_uuid_origen",
       "clase_destino_referencia": "alias_simbolico_o_uuid_destino",
       "tipo_relacion": "asociacion", // o asociacion_dirigida, herencia, agregacion, composicion
       "cardinalidad_origen": "1",
       "cardinalidad_destino": "1..*",
       "nombre": "NombreRelacion"
     }}
4. No inventes UUIDs para nuevas clases; usa referencias simbólicas (alias en minúsculas como 'cliente', 'pedido'). Para clases existentes, puedes usar su UUID o nombre.
5. Cada clase creada automáticamente por el sistema recibe un atributo inicial 'id' (INTEGER, PK), por lo que NO debes crear otro atributo 'id' para la misma clase salvo que se necesiten atributos adicionales.
6. Mantén las posiciones organizadas y no superpuestas.

ESTRUCTURA ACTUAL DEL DIAGRAMA:
{json.dumps(estructura, indent=2, ensure_ascii=False)}

HISTORIAL RECIENTE DE LA CONVERSACIÓN:
{json.dumps(historial, indent=2, ensure_ascii=False)}
"""
        return prompt_sistema
