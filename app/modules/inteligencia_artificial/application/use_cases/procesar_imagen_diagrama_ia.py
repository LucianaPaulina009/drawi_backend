from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.core.config import settings
from app.modules.diagramas.application.queries.dtos import (
    ClaseDetalleDTO,
    DiagramaDetalleDTO,
)
from app.modules.diagramas.application.validaciones import (
    obtener_diagrama_autorizado,
)
from app.modules.diagramas.domain.repositories.atributo_repository import (
    AtributoRepository,
)
from app.modules.diagramas.domain.repositories.clase_repository import (
    ClaseRepository,
)
from app.modules.diagramas.domain.repositories.diagrama_repository import (
    DiagramaRepository,
)
from app.modules.diagramas.domain.repositories.relacion_repository import (
    RelacionRepository,
)
from app.modules.gestion_colaboradores.domain.repositories.colaborador_proyecto_repository import (
    ColaboradorProyectoRepository,
)
from app.modules.gestion_proyectos.domain.repositories.proyecto_repository import (
    ProyectoRepository,
)
from app.modules.inteligencia_artificial.application.ports.providers.almacenamiento_imagen_temporal import (
    AlmacenamientoImagenTemporal,
    RecursoImagenTemporal,
)
from app.modules.inteligencia_artificial.application.services.constructor_contexto_imagen_ia import (
    ConstructorContextoImagenIa,
)
from app.modules.inteligencia_artificial.application.services.ejecutor_plan_ia import (
    EjecutorPlanIa,
)
from app.modules.inteligencia_artificial.application.services.estrategia_modelos_gemini import (
    EstrategiaModelosGemini,
)
from app.modules.inteligencia_artificial.application.services.planificador_importacion_imagen import (
    PlanImportacionImagen,
    PlanificadorImportacionImagen,
)
from app.modules.inteligencia_artificial.application.services.servicio_layout_importacion import (
    ServicioLayoutImportacion,
)
from app.modules.inteligencia_artificial.domain.entities.interaccion_ia import (
    InteraccionIa,
)
from app.modules.inteligencia_artificial.domain.exceptions import (
    ClaveIdempotenciaConflictoException,
    FormatoImagenNoSoportadoException,
    ImagenInvalidaException,
    ImagenVaciaException,
    PlanIaInvalidoException,
    ProveedorIaRecuperableException,
    RespuestaIaInvalidaException,
    TamanoImagenExcedidoException,
)
from app.modules.inteligencia_artificial.domain.repositories.interaccion_ia_repository import (
    InteraccionIaRepository,
)
from app.shared.application.ports import UnitOfWork

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ProcesarImagenDiagramaIaCommand:
    usuario_id: str
    diagrama_id: UUID
    contenido_imagen: bytes
    mime_type: str
    nombre_archivo: str
    clave_idempotencia: UUID


class ProcesarImagenDiagramaIaUseCase:
    """
    Caso de uso para importar y reconstruir un diagrama UML desde una imagen.
    
    Flujo:
    1. Autorizar permisos de edición sobre el diagrama (403 antes de costos IA).
    2. Comprobar / reservar idempotencia.
    3. Validar tamaño, MIME y magic bytes de la imagen.
    4. Staging temporal en Cloudinary.
    5. Análisis multimodal Gemini con fallback y circuit breaker.
    6. Reconciliación exacta, layout sin colisiones y orden de dependencias.
    7. Ejecución con casos de uso existentes de Diagramas y emisión de eventos.
    8. Persistencia de 1 sola interacción en historial.
    9. Limpieza obligatoria del recurso temporal en 'finally'.
    """

    FORMATOS_PERMITIDOS = {"image/png", "image/jpeg", "image/jpg", "image/webp"}

    def __init__(
        self,
        proyecto_repository: ProyectoRepository,
        diagrama_repository: DiagramaRepository,
        interaccion_repository: InteraccionIaRepository,
        clase_repository: ClaseRepository,
        atributo_repository: AtributoRepository,
        relacion_repository: RelacionRepository,
        coordinador_gemini: EstrategiaModelosGemini,
        ejecutor_plan: EjecutorPlanIa,
        uow: UnitOfWork,
        almacenamiento_temporal: AlmacenamientoImagenTemporal | None = None,
        colaborador_repository: ColaboradorProyectoRepository | None = None,
    ) -> None:
        self.proyecto_repo = proyecto_repository
        self.diagrama_repo = diagrama_repository
        self.interaccion_repo = interaccion_repository
        self.clase_repo = clase_repository
        self.atributo_repo = atributo_repository
        self.relacion_repo = relacion_repository
        self.coordinador_gemini = coordinador_gemini
        self.ejecutor_plan = ejecutor_plan
        self.uow = uow
        self.almacenamiento_temporal = almacenamiento_temporal
        self.colaborador_repo = colaborador_repository

    def _validar_archivo_imagen(self, contenido: bytes, mime_type: str) -> str:
        if not contenido or len(contenido) == 0:
            raise ImagenVaciaException()

        max_size = getattr(settings, "IA_IMAGEN_MAX_SIZE_BYTES", 10 * 1024 * 1024)
        if len(contenido) > max_size:
            raise TamanoImagenExcedidoException()

        mime_normalizado = mime_type.lower().strip() if mime_type else ""
        if mime_normalizado == "image/jpg":
            mime_normalizado = "image/jpeg"

        # Validar magic bytes
        if contenido.startswith(b"\x89PNG\r\n\x1a\n"):
            mime_detectado = "image/png"
        elif contenido.startswith(b"\xff\xd8\xff"):
            mime_detectado = "image/jpeg"
        elif contenido.startswith(b"RIFF") and len(contenido) >= 12 and contenido[8:12] == b"WEBP":
            mime_detectado = "image/webp"
        else:
            if mime_normalizado in self.FORMATOS_PERMITIDOS:
                raise ImagenInvalidaException("El contenido del archivo no coincide con los bytes de una imagen válida.")
            raise FormatoImagenNoSoportadoException(f"Formato no soportado: {mime_type}")

        if mime_normalizado and mime_normalizado != mime_detectado:
            # Si el MIME declarado difiere del detectado por magic bytes
            if mime_normalizado not in self.FORMATOS_PERMITIDOS:
                raise FormatoImagenNoSoportadoException(f"Formato MIME no admitido: {mime_normalizado}")

        return mime_detectado

    def _obtener_diagrama_detalle_fresco(self, diagrama_id: UUID) -> DiagramaDetalleDTO:
        clases_db = self.clase_repo.listar_por_diagrama(diagrama_id)
        clases_dto: list[ClaseDetalleDTO] = []
        for c in clases_db:
            attrs = self.atributo_repo.listar_por_clase(c.id)
            c_dto = ClaseDetalleDTO(
                id=c.id,
                id_diagrama=c.id_diagrama,
                nombre=c.nombre,
                posicion_x=c.posicion_x,
                posicion_y=c.posicion_y,
                ancho=c.ancho,
                atributos=tuple(attrs) if attrs else (),
            )
            clases_dto.append(c_dto)

        return DiagramaDetalleDTO(
            id=diagrama_id,
            id_proyecto=UUID("00000000-0000-0000-0000-000000000000"),
            nombre="Diagrama",
            numero=1,
            clases=tuple(clases_dto),
            relaciones=(),
            estructuras_nm=(),
        )

    def execute(self, command: ProcesarImagenDiagramaIaCommand) -> InteraccionIa:
        inicio_total = time.monotonic()

        # 1. Autorización estricta de edición (403 antes de incurrir en costos)
        obtener_diagrama_autorizado(
            propietario_id=command.usuario_id,
            diagrama_id=command.diagrama_id,
            proyecto_repository=self.proyecto_repo,
            diagrama_repository=self.diagrama_repo,
            colaborador_repository=self.colaborador_repo,
            exigir_edicion=True,
        )

        # 2. Validar idempotencia previa
        nombre_archivo_limpio = command.nombre_archivo.strip()
        existente = self.interaccion_repo.obtener_por_idempotencia(
            command.usuario_id, command.diagrama_id, command.clave_idempotencia
        )
        if existente:
            if existente.tipo_interaccion == "imagen":
                return existente
            raise ClaveIdempotenciaConflictoException("Clave de idempotencia ya utilizada con otro tipo de interacción.")

        # 3. Validar archivo de imagen (tamaño, MIME y magic bytes)
        mime_validado = self._validar_archivo_imagen(command.contenido_imagen, command.mime_type)

        # 4. Registrar interacción en estado PENDIENTE
        interaccion = InteraccionIa.crear(
            id_usuario=command.usuario_id,
            id_diagrama=command.diagrama_id,
            clave_idempotencia=command.clave_idempotencia,
            tipo_interaccion="imagen",
            entrada_usuario=f"Importación de imagen UML: {nombre_archivo_limpio}",
        )
        self.interaccion_repo.guardar(interaccion)
        self.uow.commit()

        recurso_temporal: RecursoImagenTemporal | None = None
        try:
            # 5. Staging temporal en Cloudinary (si el adaptador está provisto)
            if self.almacenamiento_temporal:
                try:
                    recurso_temporal = self.almacenamiento_temporal.subir(
                        contenido_imagen=command.contenido_imagen,
                        mime_type=mime_validado,
                    )
                except Exception as err:
                    logger.warning("Error no fatal o fallback en subida a Cloudinary: %s", err)

            interaccion.marcar_procesando()
            self.interaccion_repo.guardar(interaccion)
            self.uow.commit()

            # 6. Analizar imagen con Gemini multimodal
            prompt_sistema = ConstructorContextoImagenIa.obtener_prompt_sistema()
            texto_json_reconocido = self.coordinador_gemini.analizar_imagen_con_fallback(
                contenido_imagen=command.contenido_imagen,
                mime_type=mime_validado,
                prompt_estructural=prompt_sistema,
            )

            # 7. Parsear respuesta JSON y validar esquema DTO
            diagrama_reconocido = ConstructorContextoImagenIa.parsear_respuesta_json(
                texto_json_reconocido
            )

            # 8. Cargar estado fresco del diagrama
            diagrama_fresco = self._obtener_diagrama_detalle_fresco(command.diagrama_id)

            # 9. Calcular layout determinista en zona libre
            posiciones_layout = ServicioLayoutImportacion.calcular_posiciones(
                clases_reconocidas=diagrama_reconocido.clases,
                clases_existentes=diagrama_fresco.clases,
            )

            # 10. Reconciliar clases, atributos y construir plan de acciones
            plan = PlanificadorImportacionImagen.construir_plan(
                diagrama_reconocido=diagrama_reconocido,
                diagrama_existente=diagrama_fresco,
                posiciones_layout=posiciones_layout,
            )

            # 11. Ejecutar plan mediante casos de uso existentes de Diagramas
            resultados_pasos: list[dict[str, Any]] = []
            if plan.acciones:
                resultados_pasos = self.ejecutor_plan.ejecutar_plan(
                    usuario_id=command.usuario_id,
                    diagrama_id=command.diagrama_id,
                    acciones=plan.acciones,
                    clases_existentes=plan.clases_existentes_mapeo,
                )

            # 12. Generar resumen final de la importación
            respuesta_final = self._construir_resumen_importacion(
                plan=plan,
                resultados_pasos=resultados_pasos,
            )

            interaccion.completar(
                respuesta_ia=respuesta_final,
                modelo_utilizado="gemini-3.6-flash",
                detalle_ejecucion={
                    "pasos": resultados_pasos,
                    "clases_reutilizadas": plan.clases_reutilizadas,
                    "atributos_omitidos": plan.atributos_omitidos,
                    "advertencias": plan.advertencias,
                },
            )
            self.interaccion_repo.guardar(interaccion)
            self.uow.commit()

            total_ms = (time.monotonic() - inicio_total) * 1000.0
            logger.info(
                "[DRAWI IA IMAGEN] duracionTotalMs=%.1f acciones=%d",
                total_ms,
                len(plan.acciones),
            )
            return interaccion

        except (RespuestaIaInvalidaException, PlanIaInvalidoException) as err:
            interaccion.completar(
                respuesta_ia=f"No se pudo completar el reconocimiento del diagrama: {err.message}",
                modelo_utilizado="gemini-3.6-flash",
                detalle_ejecucion=[{
                    "paso": 1,
                    "tipo": "reconocimiento_imagen",
                    "estado": "rechazado",
                    "motivo": err.message,
                }],
            )
            self.interaccion_repo.guardar(interaccion)
            self.uow.commit()
            return interaccion

        except ProveedorIaRecuperableException as err:
            total_ms = (time.monotonic() - inicio_total) * 1000.0
            logger.error("[DRAWI IA IMAGEN] Fallo técnico del proveedor IA: %s (totalMs=%.1f)", str(err), total_ms)
            interaccion.marcar_error(
                respuesta_ia="DRAWI no pudo analizar la imagen en este momento debido a saturación del servicio. Intenta nuevamente.",
                detalle_ejecucion={"error": str(err)},
            )
            self.interaccion_repo.guardar(interaccion)
            self.uow.commit()
            raise

        except Exception as err:
            total_ms = (time.monotonic() - inicio_total) * 1000.0
            logger.error("[DRAWI IA IMAGEN] Error inesperado al procesar imagen: %s (totalMs=%.1f)", str(err), total_ms)
            interaccion.marcar_error(
                respuesta_ia="Ocurrió un error inesperado al procesar la imagen del diagrama.",
                detalle_ejecucion={"error": str(err)},
            )
            self.interaccion_repo.guardar(interaccion)
            self.uow.commit()
            raise

        finally:
            # 13. Limpieza garantizada del recurso temporal en Cloudinary
            if recurso_temporal and self.almacenamiento_temporal:
                try:
                    self.almacenamiento_temporal.eliminar(public_id=recurso_temporal.public_id)
                except Exception as cleanup_err:
                    logger.warning(
                        "Error al eliminar recurso temporal Cloudinary %s: %s",
                        recurso_temporal.public_id,
                        cleanup_err,
                    )

    @staticmethod
    def _construir_resumen_importacion(
        plan: PlanImportacionImagen,
        resultados_pasos: list[dict[str, Any]],
    ) -> str:
        if not resultados_pasos and not plan.clases_reutilizadas:
            return "No se reconocieron elementos UML aplicables en la imagen proporcionada."

        completados = [p for p in resultados_pasos if p.get("estado") == "completado"]
        rechazados = [p for p in resultados_pasos if p.get("estado") in ("rechazado", "aclaracion_requerida")]
        fallidos = [p for p in resultados_pasos if p.get("estado") == "fallido"]

        lineas: list[str] = []

        # Resumen de lo creado
        clases_creadas = [p["nombre"] for p in completados if p.get("tipo") == "crear_clase" and p.get("nombre")]
        estructuras_nm = [p["nombre"] for p in completados if p.get("tipo") == "crear_estructura_nm" and p.get("nombre")]
        relaciones_creadas = [p for p in completados if p.get("tipo") == "crear_relacion"]

        if clases_creadas:
            lineas.append(f"Se crearon {len(clases_creadas)} clase(s): {', '.join(clases_creadas)}.")
        if estructuras_nm:
            lineas.append(f"Se crearon {len(estructuras_nm)} relación(es) N:M: {', '.join(estructuras_nm)}.")
        if relaciones_creadas:
            lineas.append(f"Se crearon {len(relaciones_creadas)} relación(es) adicionales.")

        if plan.clases_reutilizadas:
            lineas.append(
                f"Se reconciliaron {len(plan.clases_reutilizadas)} clase(s) existentes: {', '.join(plan.clases_reutilizadas)}."
            )

        if plan.atributos_omitidos:
            lineas.append(f"Se omitieron {len(plan.atributos_omitidos)} atributo(s) de clases ya existentes.")

        if rechazados:
            lineas.append(f"{len(rechazados)} operación(es) no pudieron ser aplicadas por reglas de validación.")
        if fallidos:
            lineas.append(f"{len(fallidos)} operación(es) fallaron durante la ejecución.")

        if not lineas:
            lineas.append("Importación de imagen completada exitosamente.")

        return "\n".join(lineas)
