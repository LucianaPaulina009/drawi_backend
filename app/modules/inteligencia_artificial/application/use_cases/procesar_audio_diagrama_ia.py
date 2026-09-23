from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.modules.diagramas.application.validaciones import (
    obtener_diagrama_autorizado,
)
from app.modules.diagramas.domain.repositories.clase_repository import (
    ClaseRepository,
)
from app.modules.diagramas.domain.repositories.diagrama_repository import (
    DiagramaRepository,
)
from app.modules.gestion_colaboradores.domain.repositories.colaborador_proyecto_repository import (
    ColaboradorProyectoRepository,
)
from app.modules.gestion_proyectos.domain.repositories.proyecto_repository import (
    ProyectoRepository,
)
from app.modules.inteligencia_artificial.application.services.constructor_contexto_diagrama import (
    ConstructorContextoDiagrama,
)
from app.modules.inteligencia_artificial.application.services.ejecutor_plan_ia import (
    EjecutorPlanIa,
)
from app.modules.inteligencia_artificial.application.services.estrategia_modelos_gemini import (
    EstrategiaModelosGemini,
)
from app.modules.inteligencia_artificial.application.services.planificador_acciones_ia import (
    PlanificadorAccionesIa,
)
from app.modules.inteligencia_artificial.application.services.validador_respuesta_ia import (
    ValidadorRespuestaIa,
)
from app.modules.inteligencia_artificial.domain.entities.interaccion_ia import (
    InteraccionIa,
)
from app.modules.inteligencia_artificial.domain.exceptions import (
    AudioVacioException,
    ClaveIdempotenciaConflictoException,
    DuracionAudioExcedidaException,
    FormatoAudioNoSoportadoException,
    TamanoAudioExcedidoException,
)
from app.modules.inteligencia_artificial.domain.repositories.interaccion_ia_repository import (
    InteraccionIaRepository,
)
from app.shared.application.ports import UnitOfWork

logger = logging.getLogger(__name__)

MAX_AUDIO_BYTES = 10 * 1024 * 1024
MAX_DURACION_SEGUNDOS = 60.0

MIMES_SOPORTADOS = {
    "audio/webm",
    "audio/ogg",
    "audio/wav",
    "audio/x-wav",
    "audio/wave",
    "audio/mp4",
    "audio/x-m4a",
    "audio/m4a",
    "audio/aac",
    "audio/mpeg",
    "audio/mp3",
    "audio/flac",
    "audio/x-flac",
}


@dataclass(slots=True)
class ProcesarAudioDiagramaIaCommand:
    usuario_id: str
    diagrama_id: UUID
    contenido_audio: bytes
    mime_type: str
    clave_idempotencia: UUID
    duracion_segundos: float | None = None
    idioma: str | None = None


class ProcesarAudioDiagramaIaUseCase:
    """
    Caso de uso para procesar un mensaje de voz/audio directamente con Gemini multimodal
    en una sola llamada, interpretando la intención, transcribiendo lo dicho y ejecutando
    las acciones requeridas sobre el diagrama de forma determinista y sin solapamientos.
    """

    def __init__(
        self,
        proyecto_repository: ProyectoRepository,
        diagrama_repository: DiagramaRepository,
        interaccion_repository: InteraccionIaRepository,
        clase_repository: ClaseRepository,
        constructor_contexto: ConstructorContextoDiagrama,
        coordinador_gemini: EstrategiaModelosGemini,
        ejecutor_plan: EjecutorPlanIa,
        uow: UnitOfWork,
        colaborador_repository: ColaboradorProyectoRepository | None = None,
    ) -> None:
        self.proyecto_repo = proyecto_repository
        self.diagrama_repo = diagrama_repository
        self.interaccion_repo = interaccion_repository
        self.clase_repo = clase_repository
        self.constructor_contexto = constructor_contexto
        self.coordinador_gemini = coordinador_gemini
        self.ejecutor_plan = ejecutor_plan
        self.uow = uow
        self.colaborador_repo = colaborador_repository

    def execute(self, command: ProcesarAudioDiagramaIaCommand) -> InteraccionIa:
        inicio_total = time.monotonic()

        # 1. Autorización estricta de edición
        diagrama = obtener_diagrama_autorizado(
            propietario_id=command.usuario_id,
            diagrama_id=command.diagrama_id,
            proyecto_repository=self.proyecto_repo,
            diagrama_repository=self.diagrama_repo,
            colaborador_repository=self.colaborador_repo,
            exigir_edicion=True,
        )

        # 2. Validación de idempotencia previa
        existente = self.interaccion_repo.obtener_por_idempotencia(
            command.usuario_id, command.diagrama_id, command.clave_idempotencia
        )
        if existente:
            tipo_actual = (
                existente.tipo_interaccion.value
                if hasattr(existente.tipo_interaccion, "value")
                else str(existente.tipo_interaccion)
            )
            if tipo_actual == "audio":
                return existente
            raise ClaveIdempotenciaConflictoException(
                "Clave de idempotencia ya utilizada con otro tipo de interacción."
            )

        # 3. Validación de audio
        if not command.contenido_audio or len(command.contenido_audio) == 0:
            raise AudioVacioException()
        if len(command.contenido_audio) > MAX_AUDIO_BYTES:
            raise TamanoAudioExcedidoException()
        if (
            command.duracion_segundos is not None
            and command.duracion_segundos > MAX_DURACION_SEGUNDOS
        ):
            raise DuracionAudioExcedidaException()

        mime_base = (command.mime_type or "").split(";")[0].strip().lower()
        if not mime_base or mime_base not in MIMES_SOPORTADOS:
            raise FormatoAudioNoSoportadoException()

        # 4. Registrar interacción en estado PENDIENTE / PROCESANDO
        interaccion = InteraccionIa.crear(
            id_usuario=command.usuario_id,
            id_diagrama=command.diagrama_id,
            clave_idempotencia=command.clave_idempotencia,
            tipo_interaccion="audio",
            entrada_usuario="[Procesando audio...]",
        )
        self.interaccion_repo.guardar(interaccion)
        self.uow.commit()

        interaccion.marcar_procesando()
        self.interaccion_repo.guardar(interaccion)
        self.uow.commit()

        # 5. Construir contexto del diagrama con prompt de audio
        prompt_sistema = self.constructor_contexto.construir_contexto_audio(
            proyecto_id=diagrama.id_proyecto,
            diagrama_id=command.diagrama_id,
            usuario_id=command.usuario_id,
        )

        try:
            # 6. Invocar a Gemini multimodal en UNA SOLA llamada
            resultado_gemini = self.coordinador_gemini.ejecutar_audio_con_fallback(
                prompt_sistema=prompt_sistema,
                contenido_audio=command.contenido_audio,
                mime_type=mime_base,
            )

            # 7. Validar estructura JSON devuelta
            interpretacion = ValidadorRespuestaIa.validar(resultado_gemini.texto_respuesta)

            texto_transcrito = (interpretacion.transcripcion_usuario or "").strip()
            if not texto_transcrito:
                interaccion.marcar_error(
                    respuesta_ia="No se detectó contenido comprensible en el audio grabado.",
                )
                self.interaccion_repo.guardar(interaccion)
                self.uow.commit()
                from fastapi import HTTPException
                raise HTTPException(
                    status_code=422,
                    detail="No se detectó contenido comprensible en el audio grabado.",
                )

            # Actualizar la entrada de usuario con la transcripción/interpretación de Gemini
            interaccion.entrada_usuario = texto_transcrito

            resultados_pasos: list[dict[str, Any]] | None = None
            if interpretacion.acciones:
                clases_dto = self.clase_repo.listar_por_diagrama(command.diagrama_id)
                clases_existentes: dict[str, UUID] = {
                    c.nombre: c.id for c in clases_dto
                }
                for c in clases_dto:
                    clases_existentes[str(c.id)] = c.id

                acciones_ordenadas = PlanificadorAccionesIa.planificar(
                    interpretacion.acciones,
                    clases_existentes=clases_existentes,
                )

                resultados_pasos = self.ejecutor_plan.ejecutar_plan(
                    usuario_id=command.usuario_id,
                    diagrama_id=command.diagrama_id,
                    acciones=acciones_ordenadas,
                    clases_existentes=clases_existentes,
                )

            # 8. Marcar interacción completada
            interaccion.completar(
                respuesta_ia=interpretacion.respuesta_usuario,
                modelo_utilizado=resultado_gemini.modelo,
                detalle_ejecucion={
                    "transcripcion": texto_transcrito,
                    "acciones_ejecutadas": len(interpretacion.acciones),
                    "pasos": resultados_pasos or [],
                    "duracion_total_ms": (time.monotonic() - inicio_total) * 1000.0,
                },
            )
            self.interaccion_repo.guardar(interaccion)
            self.uow.commit()

            return interaccion

        except Exception as err:
            logger.error("Error al procesar interacción de audio con IA: %s", str(err), exc_info=True)
            interaccion.marcar_error(
                respuesta_ia="DRAWI no pudo interpretar el audio. Por favor intenta grabarlo nuevamente o escribe tu solicitud.",
            )
            self.interaccion_repo.guardar(interaccion)
            self.uow.commit()
            raise
