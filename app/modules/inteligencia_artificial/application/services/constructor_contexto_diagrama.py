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
            "estructuras_nm": [
                {
                    "id": str(s.id),
                    "id_clase_origen": str(s.id_clase_origen),
                    "id_clase_destino": str(s.id_clase_destino),
                    "id_clase_intermedia": str(s.id_clase_intermedia),
                }
                for s in (diagrama_dto.estructuras_nm or [])
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
Tu función es ayudar a los usuarios respondiendo preguntas sobre diseño de bases de datos, consultando la estructura del diagrama activo y, cuando el usuario lo solicite expresamente, crear, actualizar o eliminar elementos en el lienzo.

REGLAS OBLIGATORIAS:
1. Responde SIEMPRE en formato JSON válido con la siguiente estructura exacta:
{{
  "respuesta_usuario": "Texto explicativo cordial y claro en español describiendo lo realizado, respondiendo a la consulta o solicitando aclaración.",
  "acciones": []
}}
2. CONSULTAS Y SOLO LECTURA:
   - Si el usuario pregunta por la estructura existente ("¿Qué tablas hay?", "¿Qué atributos tiene Cliente?"), saluda, o pide consejos conceptuales, responde detalladamente en "respuesta_usuario" y "acciones" DEBE ser una lista vacía `[]`.
   - Si la consulta está fuera del alcance del modelado de bases de datos del diagrama actual, responde brevemente recordando que tu enfoque es consultar y diseñar el diagrama activo, manteniendo `acciones = []`.
3. ACCIONES ESTRUCTURADAS SOPORTADAS:
   - Crear clase: {{"tipo": "crear_clase", "referencia": "alias_simbolico", "nombre": "NombreClase", "posicion": {{"x": 300, "y": 200}}}}
   - Crear atributo: {{"tipo": "crear_atributo", "clase_referencia": "NombreClase_o_alias", "nombre": "campo", "tipo_dato": "varchar", "longitud": 100, "es_llave_primaria": false, "permite_nulo": true, "es_unico": false}}
   - Crear relación (1:1 o 1:N): {{"tipo": "crear_relacion", "clase_origen_referencia": "ClaseA", "clase_destino_referencia": "ClaseB", "tipo_relacion": "asociacion", "cardinalidad_origen": "1", "cardinalidad_destino": "1..*", "nombre": "NombreRelacion"}}
   - Crear estructura N:M (muchos a muchos): {{"tipo": "crear_estructura_nm", "referencia_intermedia": "alias_intermedia", "clase_origen_referencia": "ClaseA", "clase_destino_referencia": "ClaseB", "nombre_intermedia": "ClaseA_ClaseB", "posicion": {{"x": 350, "y": 250}}}}
   - Actualizar clase: {{"tipo": "actualizar_clase", "clase_referencia": "NombreClaseActual", "nuevo_nombre": "NuevoNombreClase"}}
   - Actualizar atributo: {{"tipo": "actualizar_atributo", "clase_referencia": "NombreClase", "atributo_referencia": "nombre_actual", "nuevo_nombre": "nuevo_nombre", "tipo_dato": "varchar"}}
   - Actualizar relación: {{"tipo": "actualizar_relacion", "clase_origen_referencia": "ClaseA", "clase_destino_referencia": "ClaseB", "nuevo_nombre": "nuevo_nombre_relacion"}}
   - Eliminar clase: {{"tipo": "eliminar_clase", "clase_referencia": "NombreClase"}}
   - Eliminar atributo: {{"tipo": "eliminar_atributo", "clase_referencia": "NombreClase", "atributo_referencia": "nombre_campo"}}
   - Eliminar relación: {{"tipo": "eliminar_relacion", "clase_origen_referencia": "ClaseA", "clase_destino_referencia": "ClaseB", "nombre": "nombre_opcional"}}
   - Eliminar estructura N:M: {{"tipo": "eliminar_estructura_nm", "clase_origen_referencia": "ClaseA", "clase_destino_referencia": "ClaseB"}}
4. RELACIONES MUCHOS A MUCHOS (N:M):
   - Cuando el usuario solicite crear una relación de muchos a muchos (N:M / N a M / many-to-many) entre dos tablas (ej: "Crea una relación de la tabla Cliente con Vehiculo, una relación de muchos a muchos"), debes usar la acción `crear_estructura_nm`.
   - `crear_estructura_nm` crea automáticamente en el sistema la clase intermedia (por defecto nombrada como `{{Origen}}_{{Destino}}` o el nombre indicado), su llave primaria `id`, las llaves foráneas hacia las dos clases, las dos relaciones 1:N correspondientes y la estructura N:M.
   - Si el usuario solicita además agregar atributos en la tabla intermedia de la relación de muchos a muchos (ej: "en la tabla de muchos a muchos crea un atributo llamado prueba de tipo texto"), agrega inmediatamente una acción `crear_atributo` con `clase_referencia` apuntando al nombre o alias de la clase intermedia (ej. `"Cliente_Vehiculo"` o `referencia_intermedia`).
   - Para tipos de datos de texto, usa tipos válidos como `"varchar"` (con `longitud`) o `"text"`.
5. REFERENCIAS SEMÁNTICAS:
   - Para modificar o eliminar, usa siempre los nombres semánticos reales de las clases y atributos según la ESTRUCTURA ACTUAL DEL DIAGRAMA.
   - NUNCA inventes identificadores UUID técnicos.
6. AMBIGÜEDAD Y ACLARACIÓN:
   - Si la solicitud del usuario es ambigua (por ejemplo, "elimina el campo codigo" cuando varias tablas tienen un campo "codigo"), NO incluyas acciones (`"acciones": []`) y pide aclaración cordial en "respuesta_usuario" preguntando sobre qué tabla específica desea realizar la operación.
7. INVARIANTES:
   - Cada clase nueva recibe automáticamente un atributo 'id' (INTEGER, PK), por lo que NO debes crear otro atributo 'id' duplicado para la misma clase.

ESTRUCTURA ACTUAL DEL DIAGRAMA:
{json.dumps(estructura, indent=2, ensure_ascii=False)}

HISTORIAL RECIENTE DE LA CONVERSACIÓN:
{json.dumps(historial, indent=2, ensure_ascii=False)}
"""
        return prompt_sistema
