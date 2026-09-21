from __future__ import annotations

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
    ClaveIdempotenciaConflictoException,
)
from app.modules.inteligencia_artificial.domain.repositories.interaccion_ia_repository import (
    InteraccionIaRepository,
)
from app.shared.application.ports import UnitOfWork


@dataclass(slots=True)
class ProcesarMensajeIaCommand:
    usuario_id: str
    diagrama_id: UUID
    texto: str
    clave_idempotencia: UUID


class ProcesarMensajeIaUseCase:
    """Caso de uso para procesar un mensaje de conversación con DRAWI y ejecutar acciones estructurales si aplica."""

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

    def execute(self, command: ProcesarMensajeIaCommand) -> InteraccionIa:
        # 1. Autorización de lectura/acceso al diagrama
        diagrama = obtener_diagrama_autorizado(
            propietario_id=command.usuario_id,
            diagrama_id=command.diagrama_id,
            proyecto_repository=self.proyecto_repo,
            diagrama_repository=self.diagrama_repo,
            colaborador_repository=self.colaborador_repo,
            exigir_edicion=False,
        )

        # 2. Comprobar idempotencia
        texto_limpio = command.texto.strip()
        existente = self.interaccion_repo.obtener_por_idempotencia(
            command.usuario_id, command.diagrama_id, command.clave_idempotencia
        )
        if existente:
            if (existente.entrada_usuario or "").strip() == texto_limpio:
                return existente
            raise ClaveIdempotenciaConflictoException()

        # 3. Registrar interacción en estado PENDIENTE
        interaccion = InteraccionIa.crear(
            id_usuario=command.usuario_id,
            id_diagrama=command.diagrama_id,
            clave_idempotencia=command.clave_idempotencia,
            entrada_usuario=texto_limpio,
        )
        self.interaccion_repo.guardar(interaccion)
        self.uow.commit()

        # 4. Construir contexto del diagrama
        prompt_sistema = self.constructor_contexto.construir_contexto(
            proyecto_id=diagrama.id_proyecto,
            diagrama_id=command.diagrama_id,
            usuario_id=command.usuario_id,
        )

        # 5. Invocar al coordinador de modelos Gemini con fallback
        interaccion.marcar_procesando()
        self.interaccion_repo.guardar(interaccion)
        self.uow.commit()

        try:
            resultado_gemini = self.coordinador_gemini.ejecutar_con_fallback(
                prompt_sistema=prompt_sistema,
                mensaje_usuario=texto_limpio,
            )

            # Validar estructura JSON devuelta
            interpretacion = ValidadorRespuestaIa.validar(resultado_gemini.texto_respuesta)

            resultados_pasos: list[dict[str, Any]] | None = None
            if interpretacion.acciones:
                # Obtener mapa de clases existentes en el diagrama
                clases_dto = self.clase_repo.listar_por_diagrama(command.diagrama_id)
                clases_existentes: dict[str, UUID] = {
                    c.nombre: c.id for c in clases_dto
                }
                for c in clases_dto:
                    clases_existentes[str(c.id)] = c.id

                # Planificar y ordenar dependencias
                acciones_ordenadas = PlanificadorAccionesIa.planificar(
                    interpretacion.acciones,
                    clases_existentes=clases_existentes,
                )

                # Ejecutar plan utilizando los casos de uso backend existentes
                resultados_pasos = self.ejecutor_plan.ejecutar_plan(
                    usuario_id=command.usuario_id,
                    diagrama_id=command.diagrama_id,
                    acciones=acciones_ordenadas,
                    clases_existentes=clases_existentes,
                )

            interaccion.completar(
                respuesta_ia=interpretacion.respuesta_usuario,
                modelo_utilizado=resultado_gemini.modelo,
                detalle_ejecucion=resultados_pasos,
            )
            self.interaccion_repo.guardar(interaccion)
            self.uow.commit()
            return interaccion

        except Exception as err:
            interaccion.marcar_error(
                respuesta_ia="Ocurrió un error al procesar tu solicitud con el asistente.",
                detalle_ejecucion={"error": str(err)},
            )
            self.interaccion_repo.guardar(interaccion)
            self.uow.commit()
            raise
