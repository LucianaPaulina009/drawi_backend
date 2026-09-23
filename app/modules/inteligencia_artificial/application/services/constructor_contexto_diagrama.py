from __future__ import annotations

import json
import re
from uuid import UUID

from app.core.config import settings
from app.modules.diagramas.application.queries.diagrama.obtener_diagrama import (
    ObtenerDiagramaCompletoQueryHandler,
    ObtenerDiagramaQuery,
)
from app.modules.diagramas.application.queries.dtos import (
    ClaseDetalleDTO,
    DiagramaDetalleDTO,
    RelacionDetalleDTO,
)
from app.modules.inteligencia_artificial.domain.entities.interaccion_ia import (
    InteraccionIa,
)
from app.modules.inteligencia_artificial.domain.repositories.interaccion_ia_repository import (
    InteraccionIaRepository,
)

PALABRAS_CLAVE_GLOBALES = {
    "analiza", "analizar", "analisis", "análisis",
    "revisa", "revisar", "revision", "revisión",
    "todo", "todos", "todas",
    "redundancia", "redundancias",
    "mejora", "mejoras", "sugerencias", "sugerencia",
    "optimiza", "optimizar", "optimizacion", "optimización",
    "esquema", "completo", "general", "panorama",
    "cómo está", "como esta", "esta bien", "está bien",
    "diagrama completo", "todas las tablas", "todas las clases",
}

PATRONES_REFERENCIALES = (
    r"\bagr[eé]gale\b",
    r"\belim[ií]nala\b",
    r"\bc[aá]mbialo\b",
    r"\bc[aá]mbiala\b",
    r"\bmodif[ií]cala\b",
    r"\bqu[ií]tala\b",
    r"\bqu[ií]tale\b",
    r"\bborrala\b",
    r"\bb[oó]rrala\b",
    r"\besa tabla\b",
    r"\besa clase\b",
    r"\bla tabla\b",
    r"\bla clase\b",
    r"\bdicha tabla\b",
    r"\bdicha clase\b",
    r"\ba ella\b",
    r"\ben ella\b",
    r"\bde ella\b",
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

    def seleccionar_nivel_contexto(
        self,
        mensaje_usuario: str,
        clases: list[ClaseDetalleDTO],
        relaciones: list[RelacionDetalleDTO],
        historial_interacciones: list[InteraccionIa] | None = None,
    ) -> tuple[int, set[str]]:
        """
        Determina de forma determinista y sin costo de LLM el nivel de contexto requerido:
        - Nivel 1: Resumen mínimo / estructura compacta (consultas simples, creación de clases independientes).
        - Nivel 2: Contexto relevante detallado (modificación o relaciones entre clases específicas o resueltas por historial).
        - Nivel 3: Diagrama completo (análisis global, detección de redundancias, mejoras generales o ambigüedad).

        Retorna una tupla con (nivel_seleccionado, nombres_clases_relevantes).
        """
        texto = (mensaje_usuario or "").strip().lower()
        if not texto:
            return 1, set()

        # 1. Verificar palabras clave globales -> Nivel 3
        for kw in PALABRAS_CLAVE_GLOBALES:
            if kw in texto:
                return 3, set()

        # 2. Identificar clases mencionadas explícitamente en el mensaje actual
        clases_mencionadas: set[str] = set()
        for c in clases:
            patron = r"\b" + re.escape(c.nombre.lower()) + r"\b"
            if re.search(patron, texto):
                clases_mencionadas.add(c.nombre)

        # Si se mencionan clases existentes específicas -> Nivel 2 con esas clases
        if clases_mencionadas:
            return 2, clases_mencionadas

        # 3. Si no hay mención directa, verificar patrones anafóricos / referenciales
        es_referencial = any(re.search(p, texto) for p in PATRONES_REFERENCIALES)
        if es_referencial and historial_interacciones:
            # Buscar referente en las interacciones recientes (de más reciente a más antigua)
            for interaccion in historial_interacciones:
                texto_historial = f"{interaccion.entrada_usuario or ''} {interaccion.respuesta_ia or ''}".lower()
                candidatos: set[str] = set()
                for c in clases:
                    patron = r"\b" + re.escape(c.nombre.lower()) + r"\b"
                    if re.search(patron, texto_historial):
                        candidatos.add(c.nombre)

                # Si se encuentra exactamente un referente no ambiguo -> Nivel 2
                if len(candidatos) == 1:
                    return 2, candidatos
                # Si se encontraron múltiples o conflicto en la misma interacción -> Nivel 3 por ambigüedad
                if len(candidatos) > 1:
                    return 3, set()

            # Si era referencial pero no se pudo resolver con certeza -> Nivel 3
            return 3, set()

        # 4. Si no hay clases existentes mencionadas ni referencias anafóricas (ej: "Crea una clase Cliente") -> Nivel 1
        return 1, set()

    def _construir_estructura_nivel(
        self,
        diagrama_dto: DiagramaDetalleDTO,
        nivel: int,
        nombres_clases_relevantes: set[str],
    ) -> dict:
        metadata_diagrama = {
            "id": str(diagrama_dto.id),
            "nombre": diagrama_dto.nombre,
            "numero": diagrama_dto.numero,
        }

        if nivel == 1:
            return {
                "diagrama": metadata_diagrama,
                "nivel_contexto": "1_resumen_compacto",
                "clases_existentes": [c.nombre for c in diagrama_dto.clases],
                "relaciones_existentes": [
                    {
                        "origen": next((c.nombre for c in diagrama_dto.clases if c.id == r.id_clase_origen), str(r.id_clase_origen)),
                        "destino": next((c.nombre for c in diagrama_dto.clases if c.id == r.id_clase_destino), str(r.id_clase_destino)),
                        "tipo": r.tipo_relacion,
                    }
                    for r in diagrama_dto.relaciones
                ],
            }

        if nivel == 2:
            nombres_lower = {n.lower() for n in nombres_clases_relevantes}
            ids_clases_relevantes: set[UUID] = {
                c.id for c in diagrama_dto.clases if c.nombre.lower() in nombres_lower
            }

            clases_detalladas = []
            otras_clases = []
            for c in diagrama_dto.clases:
                if c.id in ids_clases_relevantes:
                    clases_detalladas.append({
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
                    })
                else:
                    otras_clases.append(c.nombre)

            relaciones_relevantes = [
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
                if r.id_clase_origen in ids_clases_relevantes or r.id_clase_destino in ids_clases_relevantes
            ]

            return {
                "diagrama": metadata_diagrama,
                "nivel_contexto": "2_detalle_relevante",
                "clases_relevantes": clases_detalladas,
                "otras_clases_existentes": otras_clases,
                "relaciones_relevantes": relaciones_relevantes,
            }

        # Nivel 3: Diagrama completo
        return {
            "diagrama": metadata_diagrama,
            "nivel_contexto": "3_diagrama_completo",
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

    def construir_contexto_con_metadatos(
        self,
        *,
        proyecto_id: UUID,
        diagrama_id: UUID,
        usuario_id: str,
        mensaje_usuario: str = "",
        limite_historial: int | None = None,
    ) -> tuple[str, int]:
        # 1. Obtener siempre el estado estructural fresco y autorizado del diagrama desde la BD
        diagrama_dto: DiagramaDetalleDTO = self.query_diagrama.execute(
            ObtenerDiagramaQuery(
                proyecto_id=proyecto_id,
                diagrama_id=diagrama_id,
                usuario_id=usuario_id,
            )
        )

        # 2. Historial reciente acotado exactamente a IA_HISTORIAL_LIMITE (5 por defecto)
        limite_efectivo = (
            limite_historial
            if limite_historial is not None
            else settings.IA_HISTORIAL_LIMITE
        )
        if hasattr(self.interaccion_repo, "listar_recientes_por_diagrama"):
            interacciones = self.interaccion_repo.listar_recientes_por_diagrama(
                id_diagrama=diagrama_id,
                limite=limite_efectivo,
            )
        else:
            interacciones = self.interaccion_repo.listar_por_diagrama(
                id_diagrama=diagrama_id,
                limite=limite_efectivo,
            )
        interacciones_completadas = [
            i for i in interacciones
            if (i.estado.value == "completado" if hasattr(i.estado, "value") else str(i.estado) == "completado")
        ]

        # 3. Selección determinista del nivel de contexto (1, 2 o 3) y clases relevantes
        nivel, nombres_relevantes = self.seleccionar_nivel_contexto(
            mensaje_usuario=mensaje_usuario,
            clases=diagrama_dto.clases,
            relaciones=diagrama_dto.relaciones,
            historial_interacciones=interacciones_completadas,
        )

        # 4. Construir estructura resumida según el nivel seleccionado
        estructura = self._construir_estructura_nivel(
            diagrama_dto=diagrama_dto,
            nivel=nivel,
            nombres_clases_relevantes=nombres_relevantes,
        )

        historial = [
            {
                "autor_id": i.id_usuario,
                "usuario": i.entrada_usuario or "",
                "drawi": i.respuesta_ia or "",
                "estado": i.estado.value if hasattr(i.estado, "value") else str(i.estado),
            }
            for i in interacciones_completadas
        ]

        # 5. Construir prompt del sistema optimizado
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
   - Crear clase: {{"tipo": "crear_clase", "referencia": "alias_simbolico", "nombre": "NombreClase"}} (o con "posicion": {{"x": float, "y": float}} en un espacio despejado del lienzo sin solapar otras clases)
     * Toda clase creada recibe automáticamente su identificador primario 'id' (INTEGER, PK).
   - Crear atributo: {{"tipo": "crear_atributo", "clase_referencia": "NombreClase_o_alias", "nombre": "campo", "tipo_dato": "varchar", "longitud": 100, "es_llave_primaria": false, "permite_nulo": true, "es_unico": false}}
     * NO generes acciones 'crear_atributo' para 'id' ni para llaves primarias (PK), ya que el sistema las provee de forma automática.
     * TIPOS DE DATOS VÁLIDOS EN `tipo_dato`: "integer", "bigint", "varchar", "text", "decimal", "boolean", "date", "timestamp".
     * Infiere siempre el tipo adecuado según el nombre solicitado:
       - Para números o cantidades (ej: "número", "numero", "cantidad", "stock", "edad", "orden"): usa `tipo_dato: "integer"`.
       - Para valores monetarios o precios (ej: "precio", "monto", "total", "saldo", "tarifa"): usa `tipo_dato: "decimal"`.
       - Para nombres, códigos o texto corto: usa `tipo_dato: "varchar"` (con `longitud` 50 o 100).
       - Para descripciones extensas: usa `tipo_dato: "text"`.
       - Para fechas: usa `tipo_dato: "date"`.
       - Para estados o banderas: usa `tipo_dato: "boolean"`.
       - NUNCA dejes `tipo_dato` vacío ni nulo.
   - Crear relación (1:1 o 1:N): {{"tipo": "crear_relacion", "clase_origen_referencia": "ClaseA", "clase_destino_referencia": "ClaseB", "tipo_relacion": "asociacion", "cardinalidad_origen": "1", "cardinalidad_destino": "1..*", "nombre": "NombreRelacion"}}
     * Las relaciones 1:1 y 1:N materializan y vinculan automáticamente su llave foránea (FK) en la entidad correspondiente, por lo que NO debes enviar un 'crear_atributo' separado para la llave foránea.
   - Crear estructura N:M (muchos a muchos): {{"tipo": "crear_estructura_nm", "referencia_intermedia": "alias_intermedia", "clase_origen_referencia": "ClaseA", "clase_destino_referencia": "ClaseB", "nombre_intermedia": "ClaseA_ClaseB"}} (o con "posicion" despejada)
   - Actualizar clase: {{"tipo": "actualizar_clase", "clase_referencia": "NombreClaseActual", "nuevo_nombre": "NuevoNombreClase"}}
   - Actualizar atributo: {{"tipo": "actualizar_atributo", "clase_referencia": "NombreClase", "atributo_referencia": "nombre_actual", "nuevo_nombre": "nuevo_nombre", "tipo_dato": "varchar"}}
   - Actualizar relación: {{"tipo": "actualizar_relacion", "clase_origen_referencia": "ClaseA", "clase_destino_referencia": "ClaseB", "nuevo_nombre": "nuevo_nombre_relacion"}}
   - Eliminar clase: {{"tipo": "eliminar_clase", "clase_referencia": "NombreClase"}}
   - Eliminar atributo: {{"tipo": "eliminar_atributo", "clase_referencia": "NombreClase", "atributo_referencia": "nombre_campo"}}
   - Eliminar relación: {{"tipo": "eliminar_relacion", "clase_origen_referencia": "ClaseA", "clase_destino_referencia": "ClaseB", "nombre": "nombre_opcional"}}
   - Eliminar estructura N:M: {{"tipo": "eliminar_estructura_nm", "clase_origen_referencia": "ClaseA", "clase_destino_referencia": "ClaseB"}}
4. RELACIONES MUCHOS A MUCHOS (N:M):
   - Cuando el usuario solicite crear una relación de muchos a muchos (N:M / N a M / many-to-many) entre dos tablas (ej: "Crea una relación de la tabla Cliente con Vehiculo, una relación de muchos a muchos"), debes usar la acción `crear_estructura_nm`.
   - `crear_estructura_nm` crea automáticamente en el sistema la clase intermedia, su llave primaria `id`, las llaves foráneas hacia las dos clases (`id_origen`, `id_destino`), las dos relaciones 1:N correspondientes y la estructura N:M.
   - Por tanto, NO crees acciones 'crear_atributo' para 'id' ni para las llaves foráneas de la tabla intermedia.
   - Si el usuario solicita además agregar atributos adicionales en la tabla intermedia (ej: "cantidad", "precio_unitario", "fecha"), agrega inmediatamente una acción `crear_atributo` con `clase_referencia` apuntando al nombre o alias de la clase intermedia únicamente para esos atributos de datos.
5. REFERENCIAS SEMÁNTICAS:
   - Para modificar o eliminar, usa siempre los nombres semánticos reales de las clases y atributos según la ESTRUCTURA ACTUAL DEL DIAGRAMA.
   - NUNCA inventes identificadores UUID técnicos.
6. AMBIGÜEDAD Y ACLARACIÓN:
   - Si la solicitud del usuario es ambigua (por ejemplo, "elimina el campo codigo" cuando varias tablas tienen un campo "codigo"), NO incluyas acciones (`"acciones": []`) y pide aclaración cordial en "respuesta_usuario" preguntando sobre qué tabla específica desea realizar la operación.
7. INVARIANTES:
   - Cada clase nueva recibe automáticamente un atributo 'id' (INTEGER, PK), por lo que NO debes crear otro atributo 'id' duplicado para la misma clase.
   - Las relaciones gestionan automáticamente sus llaves foráneas, evitando crear campos foráneos sueltos o duplicados.

ESTRUCTURA ACTUAL DEL DIAGRAMA:
{json.dumps(estructura, indent=2, ensure_ascii=False)}

HISTORIAL RECIENTE DE LA CONVERSACIÓN:
{json.dumps(historial, indent=2, ensure_ascii=False)}
"""
        return prompt_sistema, nivel

    def construir_contexto(
        self,
        *,
        proyecto_id: UUID,
        diagrama_id: UUID,
        usuario_id: str,
        mensaje_usuario: str = "",
        limite_historial: int | None = None,
    ) -> str:
        prompt, _ = self.construir_contexto_con_metadatos(
            proyecto_id=proyecto_id,
            diagrama_id=diagrama_id,
            usuario_id=usuario_id,
            mensaje_usuario=mensaje_usuario,
            limite_historial=limite_historial,
        )
        return prompt

    def construir_contexto_audio(
        self,
        *,
        proyecto_id: UUID,
        diagrama_id: UUID,
        usuario_id: str,
        limite_historial: int | None = None,
    ) -> str:
        prompt_base, _ = self.construir_contexto_con_metadatos(
            proyecto_id=proyecto_id,
            diagrama_id=diagrama_id,
            usuario_id=usuario_id,
            mensaje_usuario="revisa todo el diagrama",
            limite_historial=limite_historial,
        )
        prompt_audio = f"""{prompt_base}

INSTRUCCIÓN ESPECIAL PARA ENTRADA DE AUDIO:
Escucha atentamente el audio adjunto grabado por el usuario en español y analiza la solicitud en relación con el diagrama UML/relacional actual.
Debes responder SIEMPRE en formato JSON válido con la siguiente estructura exacta:
{{
  "transcripcion_usuario": "Texto exacto o transcripción/interpretación clara y concisa de lo que el usuario dijo en el audio.",
  "respuesta_usuario": "Texto explicativo cordial y claro en español describiendo lo realizado o respondiendo al usuario.",
  "acciones": []
}}
Reglas obligatorias para audio:
- 'transcripcion_usuario' DEBE contener de forma fiel, clara y exacta lo que el usuario dijo en el audio. NUNCA lo dejes vacío.
- 'respuesta_usuario' es tu mensaje explicativo como asistente DRAWI dirigiéndote al usuario.
- 'acciones' contiene las operaciones sobre el diagrama (crear_clase, crear_atributo, crear_relacion, etc.) si el usuario las solicitó en el audio, o una lista vacía [] si fue una consulta o saludo.
- Al crear clases o estructuras N:M, ubícalas en posiciones libres y ordenadas sobre el lienzo sin encimarlas sobre clases existentes.
"""
        return prompt_audio
