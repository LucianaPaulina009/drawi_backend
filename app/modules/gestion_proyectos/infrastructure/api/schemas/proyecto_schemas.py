from __future__ import annotations

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, model_validator

from app.modules.gestion_proyectos.domain.entities.proyecto import (
    ColorProyecto,
    IconoProyecto,
)
from app.modules.gestion_proyectos.domain.exceptions import (
    ActualizacionProyectoVaciaException,
    NombreProyectoInvalidoException,
)


class ActualizarProyectoRequest(BaseModel):
    """Petición para actualizar parcialmente nombre, color o ícono de un proyecto."""

    nombre: str | None = Field(
        default=None, description="Nuevo nombre del proyecto (máximo 40 caracteres)."
    )
    color: ColorProyecto | None = Field(
        default=None, description="Color seleccionado para el proyecto."
    )
    icono: IconoProyecto | None = Field(
        default=None, description="Ícono representativo del proyecto."
    )

    @model_validator(mode="after")
    def validar_campos(self) -> ActualizarProyectoRequest:
        if self.nombre is None and self.color is None and self.icono is None:
            raise ActualizacionProyectoVaciaException()

        if self.nombre is not None:
            nombre_limpio = self.nombre.strip()
            if not nombre_limpio or len(nombre_limpio) > 40:
                raise NombreProyectoInvalidoException()
        return self


class ProyectoRead(BaseModel):
    """Representación pública del detalle de un proyecto creado o consultado."""

    id: UUID
    nombre: str
    color: str
    icono: str
    fecha_actualizacion: datetime
    es_favorito: bool
    slug: str
    propietario_id: str
    es_dueno: bool = True



class ListaProyectosRead(BaseModel):
    """Listado de proyectos pertenecientes al usuario autenticado."""

    items: list[ProyectoRead]


class ProyectoCreadoRead(BaseModel):
    """Respuesta tras crear un proyecto; expone únicamente su slug."""

    slug: str
