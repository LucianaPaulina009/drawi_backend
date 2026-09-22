from __future__ import annotations

import logging

import httpx
from app.core.config import settings
from app.modules.inteligencia_artificial.application.ports.providers.proveedor_ia import (
    ProveedorIa,
    ResultadoProveedorIa,
)
from app.modules.inteligencia_artificial.domain.exceptions import (
    ProveedorIaNoRecuperableException,
    ProveedorIaRecuperableException,
)
from google import genai
from google.genai import errors, types

logger = logging.getLogger(__name__)


class ProveedorGoogleGemini(ProveedorIa):
    """Adaptador de infraestructura para Google Gemini mediante el SDK google-genai."""

    def __init__(
        self,
        api_key: str | None = None,
        timeout_segundos: float | None = None,
    ) -> None:
        self._api_key = api_key if api_key is not None else settings.GEMINI_API_KEY
        self._timeout_segundos = (
            timeout_segundos
            if timeout_segundos is not None
            else settings.IA_GEMINI_TIMEOUT_SECONDS
        )
        self._client: genai.Client | None = None

    def _obtener_cliente(self) -> genai.Client:
        key = (
            self._api_key
            if (self._api_key is not None and self._api_key.strip() != "")
            else settings.GEMINI_API_KEY
        )
        if not key or not key.strip():
            raise ProveedorIaNoRecuperableException(
                "GEMINI_API_KEY no está configurada en el servidor."
            )
        if self._client is None or self._api_key != key:
            self._api_key = key.strip()
            timeout_ms = int(self._timeout_segundos * 1000) if self._timeout_segundos else 10000
            self._client = genai.Client(
                api_key=self._api_key,
                http_options=types.HttpOptions(timeout=timeout_ms),
            )
        return self._client

    def generar_respuesta(
        self,
        *,
        modelo: str,
        prompt_sistema: str,
        mensaje_usuario: str,
        temperatura: float = 0.2,
    ) -> ResultadoProveedorIa:
        cliente = self._obtener_cliente()
        timeout_ms = int(self._timeout_segundos * 1000) if self._timeout_segundos else 10000
        try:
            config = types.GenerateContentConfig(
                system_instruction=prompt_sistema,
                temperature=temperatura,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                http_options=types.HttpOptions(timeout=timeout_ms),
            )
            respuesta = cliente.models.generate_content(
                model=modelo,
                contents=mensaje_usuario,
                config=config,
            )
            texto = respuesta.text or ""
            return ResultadoProveedorIa(
                texto_respuesta=texto,
                modelo=modelo,
            )
        except errors.APIError as e:
            codigo = getattr(e, "code", None)
            mensaje = getattr(e, "message", str(e))
            logger.error(
                "Error en llamada a Gemini API (modelo=%s, status=%s): %s",
                modelo,
                codigo,
                mensaje,
            )
            if (
                codigo in (429, 500, 502, 503, 504, 404)
                or "rate limit" in mensaje.lower()
                or "quota" in mensaje.lower()
                or "unavailable" in mensaje.lower()
                or "high demand" in mensaje.lower()
                or "resource exhausted" in mensaje.lower()
                or "overloaded" in mensaje.lower()
                or "timeout" in mensaje.lower()
            ):
                raise ProveedorIaRecuperableException(
                    f"Error temporal del proveedor Gemini ({codigo}): {mensaje}"
                ) from e
            if codigo in (401, 403):
                raise ProveedorIaNoRecuperableException(
                    f"Error de autorización en Gemini: {mensaje}"
                ) from e
            raise ProveedorIaNoRecuperableException(
                f"Error no recuperable de Gemini ({codigo}): {mensaje}"
            ) from e
        except (TimeoutError, errors.ClientError, httpx.TimeoutException, httpx.RequestError) as e:
            logger.error(
                "Timeout o error de conexión con Gemini (modelo=%s): %s",
                modelo,
                str(e),
            )
            raise ProveedorIaRecuperableException(
                f"Timeout o error de conexión con Gemini ({type(e).__name__}): {str(e)}"
            ) from e
        except Exception as e:
            logger.error(
                "Error inesperado al generar respuesta con Gemini (modelo=%s): %s",
                modelo,
                str(e),
            )
            raise ProveedorIaRecuperableException(
                f"Error inesperado con el modelo {modelo}: {str(e)}"
            ) from e

    def transcribir_audio(
        self,
        *,
        modelo: str,
        contenido_audio: bytes,
        mime_type: str,
        idioma: str = "es",
    ) -> str:
        cliente = self._obtener_cliente()
        mime_base = mime_type.split(";")[0].strip().lower()
        part_audio = types.Part.from_bytes(data=contenido_audio, mime_type=mime_base)
        prompt_transcripcion = (
            "Transcribe el audio de forma exacta y literal a texto en español. "
            "No agregues comentarios, explicaciones, formato markdown, comillas ni texto adicional. "
            "Devuelve únicamente las palabras transcritas."
        )
        timeout_voz = getattr(settings, "IA_TRANSCRIPCION_TIMEOUT_SECONDS", 15.0)
        timeout_ms = int(timeout_voz * 1000)
        try:
            config = types.GenerateContentConfig(
                temperature=0.0,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                http_options=types.HttpOptions(timeout=timeout_ms),
            )
            respuesta = cliente.models.generate_content(
                model=modelo,
                contents=[part_audio, prompt_transcripcion],
                config=config,
            )
            return (respuesta.text or "").strip()
        except errors.APIError as e:
            codigo = getattr(e, "code", None)
            mensaje = getattr(e, "message", str(e))
            logger.error(
                "Error en transcripción Gemini API (modelo=%s, status=%s): %s",
                modelo,
                codigo,
                mensaje,
            )
            if (
                codigo in (429, 500, 502, 503, 504, 404)
                or "rate limit" in mensaje.lower()
                or "quota" in mensaje.lower()
                or "unavailable" in mensaje.lower()
                or "high demand" in mensaje.lower()
                or "resource exhausted" in mensaje.lower()
                or "overloaded" in mensaje.lower()
                or "timeout" in mensaje.lower()
            ):
                raise ProveedorIaRecuperableException(
                    f"Error temporal del proveedor Gemini ({codigo}): {mensaje}"
                ) from e
            if codigo in (401, 403):
                raise ProveedorIaNoRecuperableException(
                    f"Error de autorización en Gemini: {mensaje}"
                ) from e
            raise ProveedorIaNoRecuperableException(
                f"Error no recuperable de Gemini ({codigo}): {mensaje}"
            ) from e
        except (TimeoutError, errors.ClientError, httpx.TimeoutException, httpx.RequestError) as e:
            logger.error(
                "Timeout o error de conexión con Gemini al transcribir (modelo=%s): %s",
                modelo,
                str(e),
            )
            raise ProveedorIaRecuperableException(
                f"Timeout o error de conexión con Gemini ({type(e).__name__}): {str(e)}"
            ) from e
        except Exception as e:
            logger.error(
                "Error inesperado al transcribir con Gemini (modelo=%s): %s",
                modelo,
                str(e),
            )
            raise ProveedorIaRecuperableException(
                f"Error inesperado con el modelo {modelo}: {str(e)}"
            ) from e

    def analizar_diagrama_imagen(
        self,
        *,
        modelo: str,
        contenido_imagen: bytes,
        mime_type: str,
        prompt_estructural: str,
    ) -> str:
        cliente = self._obtener_cliente()
        mime_base = mime_type.split(";")[0].strip().lower()
        part_imagen = types.Part.from_bytes(data=contenido_imagen, mime_type=mime_base)
        timeout_ms = int(self._timeout_segundos * 1000) if self._timeout_segundos else 10000
        try:
            config = types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json",
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                http_options=types.HttpOptions(timeout=timeout_ms),
            )
            respuesta = cliente.models.generate_content(
                model=modelo,
                contents=[part_imagen, prompt_estructural],
                config=config,
            )
            return (respuesta.text or "").strip()
        except errors.APIError as e:
            codigo = getattr(e, "code", None)
            mensaje = getattr(e, "message", str(e))
            logger.error(
                "Error en análisis multimodal Gemini API (modelo=%s, status=%s): %s",
                modelo,
                codigo,
                mensaje,
            )
            if (
                codigo in (429, 500, 502, 503, 504, 404)
                or "rate limit" in mensaje.lower()
                or "quota" in mensaje.lower()
                or "unavailable" in mensaje.lower()
                or "high demand" in mensaje.lower()
                or "resource exhausted" in mensaje.lower()
                or "overloaded" in mensaje.lower()
                or "timeout" in mensaje.lower()
            ):
                raise ProveedorIaRecuperableException(
                    f"Error temporal del proveedor Gemini ({codigo}): {mensaje}"
                ) from e
            if codigo in (401, 403):
                raise ProveedorIaNoRecuperableException(
                    f"Error de autorización en Gemini: {mensaje}"
                ) from e
            raise ProveedorIaNoRecuperableException(
                f"Error no recuperable de Gemini ({codigo}): {mensaje}"
            ) from e
        except (TimeoutError, errors.ClientError, httpx.TimeoutException, httpx.RequestError) as e:
            logger.error(
                "Timeout o error de conexión con Gemini al analizar imagen (modelo=%s): %s",
                modelo,
                str(e),
            )
            raise ProveedorIaRecuperableException(
                f"Timeout o error de conexión con Gemini ({type(e).__name__}): {str(e)}"
            ) from e
        except Exception as e:
            logger.error(
                "Error inesperado al analizar imagen con Gemini (modelo=%s): %s",
                modelo,
                str(e),
            )
            raise ProveedorIaRecuperableException(
                f"Error inesperado con el modelo {modelo}: {str(e)}"
            ) from e
