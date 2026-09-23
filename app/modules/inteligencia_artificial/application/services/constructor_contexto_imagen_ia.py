from __future__ import annotations

import json
import re
from typing import Final

from app.modules.inteligencia_artificial.application.schemas.diagrama_reconocido_ia import (
    DiagramaReconocidoIa,
)
from app.modules.inteligencia_artificial.domain.exceptions import RespuestaIaInvalidaException


PROMPT_RECONOCIMIENTO_UML_IMAGEN: Final[str] = (
    "Eres un asistente experto en ingeniería de software y modelado de datos para DRAWI. "
    "Tu tarea es analizar la imagen proporcionada y extraer la estructura completa de un "
    "DIAGRAMA DE CLASES UML ORIENTADO A BASES DE DATOS RELACIONALES.\n\n"
    "REGLAS OBLIGATORIAS:\n"
    "1. Extrae todas las clases/tablas visibles, asignando a cada una una 'referencia_semantica' única (ej: 'ref_1', 'ref_2', etc.) y su 'nombre'. Usa esa misma 'referencia_semantica' de forma estricta y consistente en 'origen_ref' y 'destino_ref' de las relaciones.\n"
    "2. Para cada clase, extrae sus atributos con:\n"
    "   - 'nombre': nombre exacto del atributo/campo.\n"
    "   - 'tipo_detectado': tipo normalizado (uno de: 'varchar', 'integer', 'bigint', 'decimal', 'boolean', 'date', 'timestamp', 'text'). Si no es visible, usa 'varchar'.\n"
    "   - 'es_pk': true si tiene indicador PK, llave, subrayado o estereotipo <<PK>> (en DRAWI, toda clase recibe automáticamente su llave primaria 'id').\n"
    "   - 'es_fk': true si tiene indicador FK, estereotipo <<FK>> o representa explícitamente una llave foránea.\n"
    "   - 'fk_destino_ref': referencia_semantica de la clase a la que apunta la FK si es deducible (opcional, ej: 'ref_1').\n"
    "   - 'permite_nulo': true si tiene indicador NULL o '?' o '0..1'.\n"
    "3. Para cada relación visible, extrae:\n"
    "   - 'origen_ref': referencia_semantica exacta de la clase de origen (debe coincidir con la 'referencia_semantica' de una de las clases declaradas en 'clases').\n"
    "   - 'destino_ref': referencia_semantica exacta de la clase de destino (debe coincidir con la 'referencia_semantica' de una de las clases declaradas en 'clases').\n"
    "   - 'tipo': tipo de relación UML (uno de: 'asociacion', 'asociacion_dirigida', 'agregacion', 'composicion', 'herencia', 'realizacion', 'dependencia'). Por defecto: 'asociacion'.\n"
    "   - 'cardinalidad_origen': cardinalidad en el origen (ej: '1', '0..1', '1..*', '0..*').\n"
    "   - 'cardinalidad_destino': cardinalidad en el destino (ej: '1', '0..1', '1..*', '0..*').\n"
    "   - 'nombre': nombre o verbo de la relación si aparece en la línea (opcional).\n"
    "   - 'es_nm': true si la relación es de muchos a muchos (* a *, N:M, N a M, o si vincula dos entidades mediante una tabla/clase intermedia asociativa con FKs a ambas entidades).\n"
    "   - 'es_recursiva': true si origen y destino son la misma clase.\n\n"
    "REGLAS ESTRICTAS DE CARDINALIDAD:\n"
    "- Si la relación es de MUCHOS A MUCHOS (N:M, * a *, N a M, o mediada por una tabla intermedia con FKs a ambas entidades):\n"
    "  * Establece 'cardinalidad_origen': '0..*' (o '1..*') y 'cardinalidad_destino': '0..*' (o '1..*').\n"
    "  * Establece 'es_nm': true.\n"
    "  * NUNCA coloques cardinalidad '1' a '0..*' para relaciones conceptuales de muchos a muchos.\n"
    "- Si la relación es de UNO A MUCHOS (1:N), coloca 'cardinalidad_origen': '1', 'cardinalidad_destino': '0..*' (o '1..*') y 'es_nm': false.\n"
    "- Si la relación es de UNO A UNO (1:1), coloca 'cardinalidad_origen': '1', 'cardinalidad_destino': '1' y 'es_nm': false.\n\n"
    "4. Estima la posición espacial relativa aproximada de cada clase en la imagen: 'posicion_relativa_x' [0.0 (izquierda) a 1.0 (derecha)] y 'posicion_relativa_y' [0.0 (arriba) a 1.0 (abajo)].\n"
    "5. Si algún elemento o texto es borroso, ilegible o ambiguo, omítelo y añade una breve descripción en la lista 'advertencias'. NO inventes datos.\n"
    "6. NUNCA generes UUIDs, consultas SQL, código ni explicaciones conversacionales fuera del JSON.\n\n"
    "Responde EXCLUSIVAMENTE con un objeto JSON válido con la siguiente estructura:\n"
    "{\n"
    '  "clases": [\n'
    "    {\n"
    '      "referencia_semantica": "ref_1",\n'
    '      "nombre": "NombreClase",\n'
    '      "atributos": [\n'
    '        {"nombre": "id", "tipo_detectado": "integer", "es_pk": true, "es_fk": false, "permite_nulo": false},\n'
    '        {"nombre": "cliente_id", "tipo_detectado": "integer", "es_pk": false, "es_fk": true, "fk_destino_ref": "ref_2", "permite_nulo": false}\n'
    '      ],\n'
    '      "posicion_relativa_x": 0.2,\n'
    '      "posicion_relativa_y": 0.3\n'
    "    }\n"
    "  ],\n"
    '  "relaciones": [\n'
    "    {\n"
    '      "origen_ref": "ref_1",\n'
    '      "destino_ref": "ref_2",\n'
    '      "tipo": "asociacion",\n'
    '      "cardinalidad_origen": "0..*",\n'
    '      "cardinalidad_destino": "0..*",\n'
    '      "nombre": "tiene",\n'
    '      "es_nm": true,\n'
    '      "es_recursiva": false\n'
    "    }\n"
    "  ],\n"
    '  "advertencias": []\n'
    "}"
)


class ConstructorContextoImagenIa:
    """Construye el prompt y parsea la respuesta JSON de reconocimiento de imagen."""

    @classmethod
    def obtener_prompt_sistema(cls) -> str:
        return PROMPT_RECONOCIMIENTO_UML_IMAGEN

    @classmethod
    def parsear_respuesta_json(cls, texto_respuesta: str) -> DiagramaReconocidoIa:
        if not texto_respuesta or not texto_respuesta.strip():
            raise RespuestaIaInvalidaException("La IA retornó una respuesta vacía al analizar la imagen.")

        contenido = texto_respuesta.strip()

        # 1. Extraer bloque de markdown ```json ... ``` si estuviera presente
        match_bloque = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", contenido)
        if match_bloque:
            contenido = match_bloque.group(1).strip()
        else:
            # 2. Si no hay bloque markdown, buscar el objeto JSON delimitado por { ... }
            match_llaves = re.search(r"(\{[\s\S]*\})", contenido)
            if match_llaves:
                contenido = match_llaves.group(1).strip()

        # 3. Intentar parseo directo
        try:
            datos = json.loads(contenido)
        except Exception:
            # 4. Limpieza defensiva de comentarios JS y comas finales antes de fallar
            try:
                # Quitar comentarios de una línea // ...
                limpio = re.sub(r"//.*", "", contenido)
                # Quitar comentarios multilínea /* ... */
                limpio = re.sub(r"/\*[\s\S]*?\*/", "", limpio)
                # Quitar comas colgantes antes de } o ]
                limpio = re.sub(r",\s*([\]}])", r"\1", limpio)
                datos = json.loads(limpio)
            except Exception as err:
                raise RespuestaIaInvalidaException(
                    f"La IA no devolvió un JSON válido: {str(err)}"
                ) from err

        try:
            return DiagramaReconocidoIa.model_validate(datos)
        except Exception as err:
            raise RespuestaIaInvalidaException(
                f"El JSON reconocido no cumple con el schema esperado de diagrama: {str(err)}"
            ) from err
