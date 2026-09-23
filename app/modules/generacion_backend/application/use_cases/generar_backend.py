from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.modules.inteligencia_artificial.domain.entities.interaccion_ia import (
    InteraccionIa,
)
from app.modules.inteligencia_artificial.domain.repositories.interaccion_ia_repository import (
    InteraccionIaRepository,
)
from app.modules.inteligencia_artificial.domain.value_objects.tipo_interaccion_ia import (
    TipoInteraccionIa,
)

from app.modules.diagramas.application.queries.diagrama.obtener_diagrama import (
    ObtenerDiagramaCompletoQueryHandler,
)
from app.modules.diagramas.application.validaciones import (
    obtener_diagrama_autorizado,
)
from app.modules.diagramas.domain.repositories.clase_repository import ClaseRepository
from app.modules.diagramas.domain.repositories.diagrama_repository import (
    DiagramaRepository,
)
from app.modules.diagramas.domain.repositories.estructura_relacion_nm_repository import (
    EstructuraRelacionNmRepository,
)
from app.modules.diagramas.domain.repositories.referencia_fk_repository import (
    ReferenciaFKRepository,
)
from app.modules.diagramas.domain.repositories.relacion_repository import (
    RelacionRepository,
)
from app.modules.diagramas.domain.repositories.atributo_repository import (
    AtributoRepository,
)
from app.modules.gestion_colaboradores.domain.repositories.colaborador_proyecto_repository import (
    ColaboradorProyectoRepository,
)
from app.modules.gestion_proyectos.domain.repositories.proyecto_repository import (
    ProyectoRepository,
)
from app.modules.generacion_backend.application.dtos.diagnostico_generacion_dto import (
    DiagnosticoGeneracion,
)
from app.modules.generacion_backend.application.queries.obtener_diagrama_generable import (
    ObtenerDiagramaGenerableQueryHandler,
)
from app.modules.generacion_backend.application.services.empaquetador_zip import (
    EmpaquetadorZip,
)
from app.modules.generacion_backend.application.services.normalizador_modelo_generado import (
    NormalizadorModeloGenerado,
)
from app.modules.generacion_backend.application.services.renderizador_plantillas_backend import (
    RenderizadorPlantillasBackend,
)
from app.modules.generacion_backend.application.services.validador_diagrama_generable import (
    ValidadorDiagramaGenerable,
)
from app.modules.generacion_backend.domain.entities.generacion_backend import (
    GeneracionBackend,
)
from app.modules.generacion_backend.domain.exceptions import (
    DiagramaNoGenerableException,
    GeneracionBackendException,
)
from app.modules.generacion_backend.domain.repositories.generacion_backend_repository import (
    GeneracionBackendRepository,
)
from app.shared.application.ports import UnitOfWork

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class GenerarBackendCommand:
    usuario_id: str
    diagrama_id: UUID
    version_plantilla: str = "1.0.0"


@dataclass(slots=True)
class ResultadoGeneracionExito:
    generacion_id: UUID
    nombre_archivo: str
    contenido_zip: bytes
    interaccion_id: UUID | None = None
    mensaje_chat: str | None = None


@dataclass(slots=True)
class ResultadoGeneracionError:
    generacion_id: UUID
    diagnostico: DiagnosticoGeneracion
    interaccion_id: UUID | None = None
    mensaje_chat: str | None = None


class GenerarBackendUseCase:
    """Caso de uso orquestador para la generación y empaquetado de backend."""

    def __init__(
        self,
        uow: UnitOfWork,
        proyecto_repository: ProyectoRepository,
        diagrama_repository: DiagramaRepository,
        generacion_repository: GeneracionBackendRepository,
        clase_repository: ClaseRepository,
        atributo_repository: AtributoRepository,
        relacion_repository: RelacionRepository,
        referencia_fk_repository: ReferenciaFKRepository,
        estructura_nm_repository: EstructuraRelacionNmRepository,
        colaborador_repository: ColaboradorProyectoRepository | None = None,
        interaccion_repository: InteraccionIaRepository | None = None,
        validador: ValidadorDiagramaGenerable | None = None,
        normalizador: NormalizadorModeloGenerado | None = None,
        renderizador: RenderizadorPlantillasBackend | None = None,
        empaquetador: EmpaquetadorZip | None = None,
    ) -> None:
        self.uow = uow
        self.proyecto_repository = proyecto_repository
        self.diagrama_repository = diagrama_repository
        self.generacion_repository = generacion_repository
        self.clase_repository = clase_repository
        self.atributo_repository = atributo_repository
        self.relacion_repository = relacion_repository
        self.referencia_fk_repository = referencia_fk_repository
        self.estructura_nm_repository = estructura_nm_repository
        self.colaborador_repository = colaborador_repository
        self.interaccion_repository = interaccion_repository
        self.validador = validador or ValidadorDiagramaGenerable()
        self.normalizador = normalizador or NormalizadorModeloGenerado()
        self.renderizador = renderizador or RenderizadorPlantillasBackend()
        self.empaquetador = empaquetador or EmpaquetadorZip()

        self._query_handler = ObtenerDiagramaGenerableQueryHandler(
            ObtenerDiagramaCompletoQueryHandler(
                proyecto_repository=self.proyecto_repository,
                diagrama_repository=self.diagrama_repository,
                clase_repository=self.clase_repository,
                atributo_repository=self.atributo_repository,
                colaborador_repository=self.colaborador_repository,
                relacion_repository=self.relacion_repository,
                referencia_fk_repository=self.referencia_fk_repository,
                estructura_nm_repository=self.estructura_nm_repository,
            )
        )

    def execute(
        self, command: GenerarBackendCommand
    ) -> ResultadoGeneracionExito | ResultadoGeneracionError:
        # 1. Autorización
        diagrama = obtener_diagrama_autorizado(
            propietario_id=command.usuario_id,
            diagrama_id=command.diagrama_id,
            proyecto_repository=self.proyecto_repository,
            diagrama_repository=self.diagrama_repository,
            colaborador_repository=self.colaborador_repository,
            exigir_edicion=True,
        )

        # 2. Snapshot
        snapshot = self._query_handler.execute(
            proyecto_id=diagrama.id_proyecto,
            diagrama_id=command.diagrama_id,
            usuario_id=command.usuario_id,
        )

        # 3. Registrar GENERACION_BACKEND con estado validando y fecha de inicio
        fecha_inicio = datetime.now(timezone.utc)
        generacion = GeneracionBackend.iniciar(
            id_diagrama=command.diagrama_id,
            id_usuario=command.usuario_id,
            version_plantilla=command.version_plantilla,
            fecha_inicio=fecha_inicio,
        )
        self.generacion_repository.guardar(generacion)
        self.uow.commit()

        # 4. Validar
        diagnostico = self.validador.validar(snapshot)
        if not diagnostico.valido:
            detalle = f"Errores estructurales: {len(diagnostico.errores_bloqueantes)} error(es) detectado(s)."
            generacion.marcar_error(detalle)
            self.generacion_repository.guardar(generacion)

            interaccion_id = None
            lineas_errores = [f"• {e.mensaje}" for e in diagnostico.errores_bloqueantes]
            texto_errores = "\n".join(lineas_errores)
            respuesta_ia = (
                "No se pudo generar el backend porque el diagrama contiene los siguientes errores:\n\n"
                f"{texto_errores}"
            )
            if self.interaccion_repository:
                interaccion = InteraccionIa.crear(
                    id_usuario=command.usuario_id,
                    id_diagrama=command.diagrama_id,
                    clave_idempotencia=uuid4(),
                    tipo_interaccion=TipoInteraccionIa.GENERACION_BACKEND,
                    entrada_usuario=None,
                )
                interaccion.marcar_error(
                    respuesta_ia=respuesta_ia,
                    detalle_ejecucion={
                        "errores": [e.a_dict() for e in diagnostico.errores_bloqueantes]
                    },
                )
                self.interaccion_repository.guardar(interaccion)
                interaccion_id = interaccion.id

            self.uow.commit()
            return ResultadoGeneracionError(
                generacion_id=generacion.id,
                diagnostico=diagnostico,
                interaccion_id=interaccion_id,
                mensaje_chat=respuesta_ia,
            )

        try:
            # 5. Generar / Renderizar
            generacion.iniciar_generacion()
            self.generacion_repository.guardar(generacion)
            self.uow.commit()

            proyecto_spring = self.normalizador.normalizar(
                snapshot,
                version_plantilla=command.version_plantilla,
            )
            archivos = self.renderizador.renderizar(proyecto_spring)

            # 6. Empaquetar
            generacion.iniciar_empaquetado()
            self.generacion_repository.guardar(generacion)
            self.uow.commit()

            zip_bytes = self.empaquetador.empaquetar(archivos)

            # 7. Completado
            generacion.completar()
            self.generacion_repository.guardar(generacion)

            nombre_archivo = f"drawi-backend-{proyecto_spring.slug}.zip"

            interaccion_id = None
            mensaje_chat = "Backend generado correctamente."
            if self.interaccion_repository:
                interaccion = InteraccionIa.crear(
                    id_usuario=command.usuario_id,
                    id_diagrama=command.diagrama_id,
                    clave_idempotencia=uuid4(),
                    tipo_interaccion=TipoInteraccionIa.GENERACION_BACKEND,
                    entrada_usuario=None,
                )
                interaccion.completar(
                    respuesta_ia=mensaje_chat,
                    detalle_ejecucion={
                        "generacion_id": str(generacion.id),
                        "archivo": nombre_archivo,
                    },
                )
                self.interaccion_repository.guardar(interaccion)
                interaccion_id = interaccion.id

            self.uow.commit()

            return ResultadoGeneracionExito(
                generacion_id=generacion.id,
                nombre_archivo=nombre_archivo,
                contenido_zip=zip_bytes,
                interaccion_id=interaccion_id,
                mensaje_chat=mensaje_chat,
            )

        except Exception as e:
            logger.error("Error durante la generación de backend: %s", e, exc_info=True)
            generacion.marcar_error(f"Error técnico durante el renderizado o empaquetado: {str(e)}")
            self.generacion_repository.guardar(generacion)

            if self.interaccion_repository:
                try:
                    interaccion = InteraccionIa.crear(
                        id_usuario=command.usuario_id,
                        id_diagrama=command.diagrama_id,
                        clave_idempotencia=uuid4(),
                        tipo_interaccion=TipoInteraccionIa.GENERACION_BACKEND,
                        entrada_usuario=None,
                    )
                    interaccion.marcar_error(
                        respuesta_ia="No se pudo generar el backend por un error técnico. Inténtalo nuevamente.",
                        detalle_ejecucion={"error": str(e)},
                    )
                    self.interaccion_repository.guardar(interaccion)
                except Exception:
                    pass

            self.uow.commit()
            raise GeneracionBackendException(f"Error técnico durante la generación: {str(e)}") from e
