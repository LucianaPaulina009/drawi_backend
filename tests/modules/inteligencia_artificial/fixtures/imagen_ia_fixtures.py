from __future__ import annotations

import base64
from typing import Dict, List, Optional
from app.modules.inteligencia_artificial.application.ports.providers.almacenamiento_imagen_temporal import (
    AlmacenamientoImagenTemporal,
    RecursoImagenTemporal,
)
from app.modules.inteligencia_artificial.application.ports.providers.proveedor_ia import (
    ProveedorIa,
    ResultadoProveedorIa,
)

# 1x1 pixel valid PNG
PNG_VALIDO_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)

# 1x1 pixel valid JPEG
JPEG_VALIDO_BYTES = bytes([
    0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01,
    0x01, 0x01, 0x00, 0x48, 0x00, 0x48, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43,
    0x00, 0xFF, 0xC0, 0x00, 0x0B, 0x08, 0x00, 0x01, 0x00, 0x01, 0x01, 0x01,
    0x11, 0x00, 0xFF, 0xC4, 0x00, 0x14, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0xFF, 0xDA, 0x00, 0x08, 0x01, 0x01, 0x00, 0x00, 0x3F, 0x00, 0xBF, 0x00,
    0xFF, 0xD9
])

# 1x1 pixel valid WEBP
WEBP_VALIDO_BYTES = bytes([
    0x52, 0x49, 0x46, 0x46, 0x1A, 0x00, 0x00, 0x00, 0x57, 0x45, 0x42, 0x50,
    0x56, 0x50, 0x38, 0x4C, 0x0E, 0x00, 0x00, 0x00, 0x2F, 0x00, 0x00, 0x00,
    0x00, 0x07, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
])


class FakeAlmacenamientoImagen(AlmacenamientoImagenTemporal):
    """Fake en memoria para pruebas de almacenamiento efímero de imágenes."""

    def __init__(self) -> None:
        self.archivos: Dict[str, bytes] = {}
        self.destruidos: List[str] = []
        self.debe_fallar_upload: bool = False
        self.debe_fallar_destroy: bool = False

    def subir(
        self,
        *,
        contenido_imagen: bytes,
        mime_type: str,
        carpeta: str | None = None,
    ) -> RecursoImagenTemporal:
        if self.debe_fallar_upload:
            from app.modules.inteligencia_artificial.domain.exceptions import (
                ProveedorAlmacenamientoImagenException,
            )
            raise ProveedorAlmacenamientoImagenException("Error simulado en upload Cloudinary.")

        import uuid
        public_id = f"drawi/temp/importaciones-uml/{uuid.uuid4()}"
        self.archivos[public_id] = contenido_imagen
        return RecursoImagenTemporal(
            public_id=public_id,
            secure_url=f"https://res.cloudinary.com/drawi/image/upload/{public_id}.png",
            formato="png",
            bytes_tamano=len(contenido_imagen),
        )

    def eliminar(self, *, public_id: str) -> None:
        self.destruidos.append(public_id)
        if self.debe_fallar_destroy:
            # En destroy los errores no rompen la transacción pero se registran
            return
        self.archivos.pop(public_id, None)


class FakeProveedorIaImagen(ProveedorIa):
    """Fake de ProveedorIa con soporte para análisis de imagen."""

    def __init__(self, respuesta_json_imagen: str = "{}") -> None:
        self.respuesta_json_imagen = respuesta_json_imagen
        self.llamadas_imagen: List[dict] = []
        self.debe_fallar_imagen: bool = False

    def generar_respuesta(
        self,
        *,
        modelo: str,
        prompt_sistema: str,
        mensaje_usuario: str,
        temperatura: float = 0.2,
    ) -> ResultadoProveedorIa:
        return ResultadoProveedorIa(
            texto_respuesta="{}",
            modelo=modelo,
        )

    def transcribir_audio(
        self,
        *,
        modelo: str,
        contenido_audio: bytes,
        mime_type: str,
        idioma: str = "es",
    ) -> str:
        return "Transcripción simulada"

    def analizar_diagrama_imagen(
        self,
        *,
        modelo: str,
        contenido_imagen: bytes,
        mime_type: str,
        prompt_estructural: str,
    ) -> str:
        self.llamadas_imagen.append({
            "modelo": modelo,
            "contenido_imagen_len": len(contenido_imagen),
            "mime_type": mime_type,
            "prompt": prompt_estructural,
        })
        if self.debe_fallar_imagen:
            from app.modules.inteligencia_artificial.domain.exceptions import (
                ProveedorIaRecuperableException,
            )
            raise ProveedorIaRecuperableException("Fallo simulado en Gemini multimodal.")
        return self.respuesta_json_imagen
