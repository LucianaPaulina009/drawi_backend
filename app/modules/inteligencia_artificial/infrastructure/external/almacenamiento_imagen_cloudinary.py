from __future__ import annotations

import io
import logging
from typing import Any

from app.core.config import settings
from app.modules.inteligencia_artificial.application.ports.providers.almacenamiento_imagen_temporal import (
    AlmacenamientoImagenTemporal,
    ProveedorAlmacenamientoException,
    ProveedorAlmacenamientoRecuperableException,
    RecursoImagenTemporal,
)
from app.modules.inteligencia_artificial.domain.exceptions import (
    ProveedorAlmacenamientoImagenException,
    ProveedorAlmacenamientoImagenRecuperableException,
)

logger = logging.getLogger(__name__)


class AlmacenamientoImagenCloudinary(AlmacenamientoImagenTemporal):
    """Adaptador de almacenamiento efímero usando Cloudinary."""

    def __init__(
        self,
        cloud_name: str | None = None,
        api_key: str | None = None,
        api_secret: str | None = None,
        cloudinary_url: str | None = None,
    ) -> None:
        try:
            import cloudinary
            import cloudinary.uploader

            self._cloudinary = cloudinary
            self._uploader = cloudinary.uploader

            cfg_url = cloudinary_url or settings.CLOUDINARY_URL
            cfg_cloud_name = cloud_name or settings.CLOUDINARY_CLOUD_NAME
            cfg_api_key = api_key or settings.CLOUDINARY_API_KEY
            cfg_api_secret = api_secret or settings.CLOUDINARY_API_SECRET

            if cfg_url:
                self._cloudinary.config(cloudinary_url=cfg_url)
            elif cfg_cloud_name and cfg_api_key and cfg_api_secret:
                self._cloudinary.config(
                    cloud_name=cfg_cloud_name,
                    api_key=cfg_api_key,
                    api_secret=cfg_api_secret,
                    secure=True,
                )
            else:
                logger.warning(
                    "Cloudinary no está completamente configurado con credenciales en entorno."
                )
        except ImportError as err:
            logger.error("SDK de Cloudinary no encontrado: %s", str(err))
            raise ProveedorAlmacenamientoImagenException(
                "El paquete cloudinary no está instalado en el runtime."
            ) from err

    def subir(
        self,
        *,
        contenido_imagen: bytes,
        mime_type: str,
        carpeta: str | None = None,
    ) -> RecursoImagenTemporal:
        folder_prefix = carpeta or settings.IA_IMAGEN_FOLDER_PREFIX
        try:
            stream = io.BytesIO(contenido_imagen)
            resultado: dict[str, Any] = self._uploader.upload(
                stream,
                folder=folder_prefix,
                resource_type="image",
                use_filename=False,
                unique_filename=True,
            )

            public_id = str(resultado.get("public_id", ""))
            secure_url = str(resultado.get("secure_url", ""))
            formato = str(resultado.get("format", "png"))
            tamano = int(resultado.get("bytes", len(contenido_imagen)))

            if not public_id or not secure_url:
                raise ProveedorAlmacenamientoImagenException(
                    "Cloudinary no retornó public_id o secure_url válidos."
                )

            return RecursoImagenTemporal(
                public_id=public_id,
                secure_url=secure_url,
                formato=formato,
                bytes_tamano=tamano,
            )
        except (TimeoutError, ConnectionError) as err:
            logger.warning("Error de conexión al subir imagen a Cloudinary: %s", str(err))
            raise ProveedorAlmacenamientoImagenRecuperableException(
                "Tiempo de espera agotado al comunicarse con el servicio de almacenamiento temporal."
            ) from err
        except Exception as err:
            if isinstance(err, (ProveedorAlmacenamientoImagenException, ProveedorAlmacenamientoImagenRecuperableException)):
                raise
            logger.error("Error al subir imagen a Cloudinary: %s", str(err))
            raise ProveedorAlmacenamientoImagenException(
                f"Fallo al subir imagen temporal: {str(err)}"
            ) from err

    def eliminar(self, *, public_id: str) -> None:
        if not public_id:
            return
        try:
            self._uploader.destroy(public_id, resource_type="image", invalidate=True)
            logger.info("Recurso temporal Cloudinary destruido con éxito: %s", public_id)
        except Exception as err:
            # Cleanup seguro en finally: no debe revertir operaciones del dominio ya confirmadas
            logger.warning(
                "No se pudo destruir el recurso temporal de Cloudinary (%s): %s",
                public_id,
                str(err),
            )
