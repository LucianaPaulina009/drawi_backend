from __future__ import annotations

import io
import zipfile
from pathlib import PurePath

from app.modules.generacion_backend.domain.exceptions import (
    ErrorEmpaquetadoZipException,
)


class EmpaquetadorZip:
    """Empaqueta un conjunto de archivos en memoria dentro de un archivo ZIP seguro."""

    def empaquetar(self, archivos: dict[str, str]) -> bytes:
        """Crea y devuelve los bytes del archivo ZIP."""
        try:
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zip_file:
                for ruta_relativa, contenido in archivos.items():
                    pure_path = PurePath(ruta_relativa)
                    # Prevención de Path Traversal
                    if pure_path.is_absolute() or ".." in pure_path.parts:
                        raise ValueError(f"Ruta inválida detectada en el empaquetado: {ruta_relativa}")

                    # Normalizar separadores a / para ZIP estándar
                    ruta_zip = pure_path.as_posix()
                    contenido_limpio = contenido.lstrip("\ufeff")
                    zip_file.writestr(ruta_zip, contenido_limpio.encode("utf-8"))

            buffer.seek(0)
            return buffer.getvalue()
        except Exception as e:
            raise ErrorEmpaquetadoZipException(
                f"Fallo al construir el archivo ZIP: {str(e)}"
            ) from e
