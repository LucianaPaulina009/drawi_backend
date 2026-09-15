from __future__ import annotations

from enum import Enum
from uuid import UUID, uuid4
from slugify import slugify

from app.modules.gestion_proyectos.domain.exceptions import NombreProyectoInvalidoException


class ColorProyecto(str, Enum):
    celeste = "celeste"
    rojo = "rojo"
    verde = "verde"
    azul = "azul"
    naranja = "naranja"
    amarillo = "amarillo"
    morado = "morado"


class IconoProyecto(str, Enum):
    finanza = "finanza"
    almacen = "almacen"
    estrella = "estrella"
    dinero = "dinero"
    caja = "caja"


class Proyecto:
    """Entidad de dominio para representar un proyecto de dibujo/modelado."""

    def __init__(
        self,
        id: UUID,
        propietario_id: str,
        nombre: str,
        color: ColorProyecto,
        icono: IconoProyecto,
        slug: str,
    ) -> None:
        self.id = id
        self.propietario_id = propietario_id
        self.nombre = self.normalizar_nombre(nombre)
        self.color = color if isinstance(color, ColorProyecto) else ColorProyecto(color)
        self.icono = icono if isinstance(icono, IconoProyecto) else IconoProyecto(icono)
        self.slug = slug

    @classmethod
    def crear(
        cls,
        *,
        propietario_id: str,
        numero: int,
        slug: str | None = None,
    ) -> Proyecto:
        """Constructor nombrado para crear un nuevo proyecto por defecto."""
        nombre = f"Nuevo Proyecto {numero}"
        color = ColorProyecto.celeste
        icono = IconoProyecto.caja
        slug_generado = slug or cls.generar_slug(nombre)
        return cls(
            id=uuid4(),
            propietario_id=propietario_id,
            nombre=nombre,
            color=color,
            icono=icono,
            slug=slug_generado,
        )

    def actualizar(
        self,
        *,
        nombre: str | None = None,
        color: ColorProyecto | str | None = None,
        icono: IconoProyecto | str | None = None,
        nuevo_slug: str | None = None,
    ) -> None:
        """Actualiza los campos permitidos del proyecto."""
        if nombre is not None:
            nombre_normalizado = self.normalizar_nombre(nombre)
            if nombre_normalizado != self.nombre:
                self.nombre = nombre_normalizado
                self.slug = nuevo_slug or self.generar_slug(nombre_normalizado)
            elif nuevo_slug is not None:
                self.slug = nuevo_slug

        if color is not None:
            self.color = color if isinstance(color, ColorProyecto) else ColorProyecto(color)

        if icono is not None:
            self.icono = icono if isinstance(icono, IconoProyecto) else IconoProyecto(icono)

    @staticmethod
    def normalizar_nombre(nombre: str) -> str:
        if not isinstance(nombre, str):
            raise NombreProyectoInvalidoException("El nombre del proyecto debe ser texto.")
        nombre_limpio = nombre.strip()
        if not nombre_limpio or len(nombre_limpio) > 40:
            raise NombreProyectoInvalidoException(
                "El nombre del proyecto no puede estar vacío ni superar los 40 caracteres."
            )
        return nombre_limpio

    @staticmethod
    def generar_slug(nombre: str) -> str:
        slug = slugify(nombre)
        if not slug:
            return "proyecto"
        return slug
