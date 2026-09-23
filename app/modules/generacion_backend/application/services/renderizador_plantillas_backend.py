from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

from app.modules.generacion_backend.application.dtos.modelo_spring_dto import (
    EntidadSpring,
    ProyectoSpring,
)
from app.modules.generacion_backend.domain.exceptions import (
    ErrorRenderizadoPlantillaException,
)


class RenderizadorPlantillasBackend:
    """Renderiza archivos de código fuente y configuración a partir del modelo ProyectoSpring."""

    def __init__(self, templates_dir: Path | None = None) -> None:
        if templates_dir is None:
            templates_dir = (
                Path(__file__).resolve().parent.parent.parent
                / "infrastructure"
                / "templates"
                / "spring_boot_maven"
            )
        self.templates_dir = templates_dir
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def renderizar(self, proyecto: ProyectoSpring) -> dict[str, str]:
        """Devuelve un mapa de ruta_relativa -> contenido_renderizado."""
        try:
            archivos: dict[str, str] = {}
            ctx = self._crear_contexto_general(proyecto)

            # Archivos raíz y recursos
            archivos["pom.xml"] = self._render_template("pom.xml.j2", ctx)
            archivos["Dockerfile"] = self._render_template("Dockerfile.j2", ctx)
            archivos["docker-compose.yml"] = self._render_template("docker-compose.yml.j2", ctx)
            archivos["README.md"] = self._render_template("README.md.j2", ctx)
            archivos["src/main/resources/application.yml"] = self._render_template(
                "application.yml.j2", ctx
            )

            pkg_path = f"src/main/java/{proyecto.package_path}"

            # Clases compartidas
            archivos[f"{pkg_path}/Application.java"] = self._render_template("Application.java.j2", ctx)
            archivos[f"{pkg_path}/config/OpenApiConfig.java"] = self._render_template("OpenApiConfig.java.j2", ctx)
            archivos[f"{pkg_path}/config/CorsConfig.java"] = self._render_template("CorsConfig.java.j2", ctx)
            archivos[f"{pkg_path}/dto/ApiResponse.java"] = self._render_template("ApiResponse.java.j2", ctx)
            archivos[f"{pkg_path}/exception/ResourceNotFoundException.java"] = self._render_template("ResourceNotFoundException.java.j2", ctx)
            archivos[f"{pkg_path}/exception/GlobalExceptionHandler.java"] = self._render_template("GlobalExceptionHandler.java.j2", ctx)

            # Clases por entidad
            for entidad in proyecto.entidades:
                entidad_ctx = {**ctx, "entidad": entidad}
                archivos[f"{pkg_path}/entity/{entidad.nombre_clase}.java"] = self._render_template(
                    "Entity.java.j2", entidad_ctx
                )
                archivos[f"{pkg_path}/dto/{entidad.nombre_clase}RequestDto.java"] = self._render_template(
                    "EntityRequestDto.java.j2", entidad_ctx
                )
                archivos[f"{pkg_path}/dto/{entidad.nombre_clase}ResponseDto.java"] = self._render_template(
                    "EntityResponseDto.java.j2", entidad_ctx
                )
                archivos[f"{pkg_path}/repository/{entidad.nombre_clase}Repository.java"] = self._render_template(
                    "EntityRepository.java.j2", entidad_ctx
                )
                archivos[f"{pkg_path}/service/{entidad.nombre_clase}Service.java"] = self._render_template(
                    "EntityService.java.j2", entidad_ctx
                )
                archivos[f"{pkg_path}/controller/{entidad.nombre_clase}Controller.java"] = self._render_template(
                    "EntityController.java.j2", entidad_ctx
                )

            return archivos
        except Exception as e:
            raise ErrorRenderizadoPlantillaException(
                f"Fallo al renderizar las plantillas del backend: {str(e)}"
            ) from e

    def _render_template(self, template_name: str, context: dict[str, Any]) -> str:
        template = self.jinja_env.get_template(template_name)
        contenido = template.render(context)
        return contenido.lstrip("\ufeff")

    def _crear_contexto_general(self, proyecto: ProyectoSpring) -> dict[str, Any]:
        return {
            "nombre_proyecto": proyecto.nombre_proyecto,
            "slug": proyecto.slug,
            "package_name": proyecto.package_name,
            "package_path": proyecto.package_path,
            "version_plantilla": proyecto.version_plantilla,
            "java_version": proyecto.java_version,
            "spring_boot_version": proyecto.spring_boot_version,
            "entidades": proyecto.entidades,
        }
