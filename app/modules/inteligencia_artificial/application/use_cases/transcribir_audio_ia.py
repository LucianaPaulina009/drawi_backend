from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.core.config import settings
from app.modules.diagramas.application.validaciones import (
    obtener_diagrama_autorizado,
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
from app.modules.inteligencia_artificial.application.ports.providers.proveedor_transcripcion import (
    ProveedorTranscripcion,
    ResultadoTranscripcion,
)
from app.modules.inteligencia_artificial.domain.exceptions import (
    AudioVacioException,
    DuracionAudioExcedidaException,
    FormatoAudioNoSoportadoException,
    TamanoAudioExcedidoException,
)

# Límite máximo de tamaño de audio: 10 MiB
MAX_AUDIO_BYTES = 10 * 1024 * 1024
# Límite máximo de duración: 60 segundos
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
class TranscribirAudioIaCommand:
    usuario_id: str
    diagrama_id: UUID
    contenido_audio: bytes
    mime_type: str
    duracion_segundos: float | None = None
    idioma: str | None = None


class TranscribirAudioIaUseCase:
    """Caso de uso para validar y transcribir un archivo de audio temporal a texto."""

    def __init__(
        self,
        proyecto_repository: ProyectoRepository,
        diagrama_repository: DiagramaRepository,
        proveedor_transcripcion: ProveedorTranscripcion,
        colaborador_repository: ColaboradorProyectoRepository | None = None,
    ) -> None:
        self.proyecto_repo = proyecto_repository
        self.diagrama_repo = diagrama_repository
        self.proveedor_transcripcion = proveedor_transcripcion
        self.colaborador_repo = colaborador_repository

    def execute(self, command: TranscribirAudioIaCommand) -> ResultadoTranscripcion:
        # 1. Autorización de lectura/acceso al diagrama
        obtener_diagrama_autorizado(
            propietario_id=command.usuario_id,
            diagrama_id=command.diagrama_id,
            proyecto_repository=self.proyecto_repo,
            diagrama_repository=self.diagrama_repo,
            colaborador_repository=self.colaborador_repo,
            exigir_edicion=False,
        )

        # 2. Validación de audio no vacío
        if not command.contenido_audio or len(command.contenido_audio) == 0:
            raise AudioVacioException()

        # 3. Validación de tamaño máximo (10 MiB)
        if len(command.contenido_audio) > MAX_AUDIO_BYTES:
            raise TamanoAudioExcedidoException()

        # 4. Validación de duración máxima (60 segundos)
        if (
            command.duracion_segundos is not None
            and command.duracion_segundos > MAX_DURACION_SEGUNDOS
        ):
            raise DuracionAudioExcedidaException()

        # 5. Validación de tipo MIME
        mime_base = (command.mime_type or "").split(";")[0].strip().lower()
        if not mime_base or mime_base not in MIMES_SOPORTADOS:
            raise FormatoAudioNoSoportadoException()

        # 6. Transcribir audio mediante el proveedor
        idioma_objetivo = command.idioma or settings.IA_TRANSCRIPCION_IDIOMA
        resultado = self.proveedor_transcripcion.transcribir_audio(
            contenido_audio=command.contenido_audio,
            mime_type=command.mime_type,
            idioma=idioma_objetivo,
        )

        # Normalizar texto (trim)
        texto_limpio = (resultado.texto or "").strip()

        return ResultadoTranscripcion(
            texto=texto_limpio,
            idioma=resultado.idioma or idioma_objetivo,
        )
