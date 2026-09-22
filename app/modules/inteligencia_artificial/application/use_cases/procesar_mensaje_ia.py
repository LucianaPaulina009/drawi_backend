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
    ClaveIdempotenciaConflictoException,
    PlanIaInvalidoException,
    ProveedorIaRecuperableException,
)
from app.modules.inteligencia_artificial.domain.repositories.interaccion_ia_repository import (
    InteraccionIaRepository,
)
from app.shared.application.ports import UnitOfWork

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ProcesarMensajeIaCommand:
    usuario_id: str
    diagrama_id: UUID
    texto: str
    clave_idempotencia: UUID
    tipo_interaccion: str = "texto"


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
        inicio_total = time.monotonic()

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
            tipo_interaccion=command.tipo_interaccion or "texto",
            entrada_usuario=texto_limpio,
        )
        self.interaccion_repo.guardar(interaccion)
        self.uow.commit()

        # 4. Construir contexto determinista del diagrama (siempre fresco desde BD)
        inicio_contexto = time.monotonic()
        prompt_sistema, nivel_contexto = self.constructor_contexto.construir_contexto_con_metadatos(
            proyecto_id=diagrama.id_proyecto,
            diagrama_id=command.diagrama_id,
            usuario_id=command.usuario_id,
            mensaje_usuario=texto_limpio,
        )
        context_ms = (time.monotonic() - inicio_contexto) * 1000.0

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

            respuesta_final = self._construir_respuesta_ia(
                respuesta_gemini=interpretacion.respuesta_usuario,
                resultados_pasos=resultados_pasos,
            )

            interaccion.completar(
                respuesta_ia=respuesta_final,
                modelo_utilizado=resultado_gemini.modelo,
                detalle_ejecucion=resultados_pasos,
            )
            self.interaccion_repo.guardar(interaccion)
            self.uow.commit()

            total_ms = (time.monotonic() - inicio_total) * 1000.0
            logger.info(
                "[DRAWI IA] contextLevel=%d contextMs=%.1f model=%s attempts=%d fallback=%s breakerOpen=%s geminiMs=%.1f totalMs=%.1f",
                nivel_contexto,
                context_ms,
                resultado_gemini.modelo,
                resultado_gemini.intentos,
                resultado_gemini.fallback_utilizado,
                resultado_gemini.breaker_abierto,
                resultado_gemini.duracion_ms,
                total_ms,
            )

            return interaccion

        except PlanIaInvalidoException as err:
            interaccion.completar(
                respuesta_ia=f"No se pudo realizar la operación: {err.message}",
                modelo_utilizado=resultado_gemini.modelo if "resultado_gemini" in locals() else None,
                detalle_ejecucion=[{
                    "paso": 1,
                    "tipo": "planificacion",
                    "estado": "rechazado",
                    "motivo": err.message,
                }],
            )
            self.interaccion_repo.guardar(interaccion)
            self.uow.commit()
            return interaccion

        except ProveedorIaRecuperableException as err:
            total_ms = (time.monotonic() - inicio_total) * 1000.0
            logger.error(
                "[DRAWI IA ERROR] Fallo técnico del proveedor IA: %s (contextLevel=%d, totalMs=%.1f)",
                str(err),
                nivel_contexto,
                total_ms,
            )
            interaccion.marcar_error(
                respuesta_ia="DRAWI no pudo procesar la solicitud en este momento. Intenta nuevamente.",
                detalle_ejecucion={"error": str(err)},
            )
            self.interaccion_repo.guardar(interaccion)
            self.uow.commit()
            raise

        except Exception as err:
            total_ms = (time.monotonic() - inicio_total) * 1000.0
            logger.error(
                "[DRAWI IA ERROR] Error no recuperable al procesar interacción: %s (totalMs=%.1f)",
                str(err),
                total_ms,
            )
            interaccion.marcar_error(
                respuesta_ia="Ocurrió un error al procesar tu solicitud con el asistente.",
                detalle_ejecucion={"error": str(err)},
            )
            self.interaccion_repo.guardar(interaccion)
            self.uow.commit()
            raise

    @staticmethod
    def _construir_respuesta_ia(
        respuesta_gemini: str,
        resultados_pasos: list[dict[str, Any]] | None,
    ) -> str:
        """Determina la respuesta final visible al usuario basándose en los resultados reales de la ejecución."""
        if not resultados_pasos:
            return respuesta_gemini

        completados = [p for p in resultados_pasos if p.get("estado") == "completado"]
        rechazados = [p for p in resultados_pasos if p.get("estado") in ("rechazado", "aclaracion_requerida")]
        fallidos = [p for p in resultados_pasos if p.get("estado") == "fallido"]
        omitidos = [p for p in resultados_pasos if p.get("estado") == "omitido"]

        # Si todos los pasos se completaron exitosamente
        if len(completados) == len(resultados_pasos):
            return respuesta_gemini if respuesta_gemini and respuesta_gemini.strip() else "Operaciones realizadas exitosamente."

        # Si ningún paso se completó
        if not completados:
            if rechazados:
                primer_rechazo = rechazados[0]
                motivo = primer_rechazo.get("motivo") or primer_rechazo.get("error") or "La operación no es permitida por las reglas del modelo."
                if primer_rechazo.get("estado") == "aclaracion_requerida":
                    return motivo
                return f"No se pudo realizar la operación: {motivo}"
            if fallidos:
                primer_fallo = fallidos[0]
                error = primer_fallo.get("error") or "Error inesperado al ejecutar la operación."
                return f"No se pudo realizar la operación debido a un error: {error}"
            return "No se pudo realizar la operación solicitada."

        # Mixto: algunos se completaron y otros fallaron/fueron rechazados
        partes = []
        nombres_completados = []
        for p in completados:
            tipo = p.get("tipo", "acción")
            nombre = p.get("nombre")
            if nombre:
                nombres_completados.append(f"{tipo} '{nombre}'")
            else:
                nombres_completados.append(f"{tipo}")
        partes.append(f"Se completó exitosamente: {', '.join(nombres_completados)}.")

        for p in rechazados:
            motivo = p.get("motivo") or "rechazado por el dominio"
            partes.append(f"No se pudo ejecutar {p.get('tipo')}: {motivo}")

        for p in fallidos:
            error = p.get("error") or "error inesperado"
            partes.append(f"Falló {p.get('tipo')}: {error}")

        if omitidos:
            partes.append(f"Se omitieron {len(omitidos)} acción(es) posterior(es).")

        return "\n".join(partes)
