from uuid import UUID
import pytest

from app.modules.gestion_proyectos.domain.entities.proyecto import (
    ColorProyecto,
    IconoProyecto,
    Proyecto,
)
from app.modules.gestion_proyectos.domain.exceptions import NombreProyectoInvalidoException


def test_crear_proyecto_valores_por_defecto():
    proyecto = Proyecto.crear(propietario_id="usr-123", numero=0)

    assert isinstance(proyecto.id, UUID)
    assert proyecto.propietario_id == "usr-123"
    assert proyecto.nombre == "Nuevo Proyecto 0"
    assert proyecto.color == ColorProyecto.celeste
    assert proyecto.icono == IconoProyecto.caja
    assert proyecto.slug == "nuevo-proyecto-0"


def test_crear_proyecto_con_numero_consecutivo():
    proyecto = Proyecto.crear(propietario_id="usr-123", numero=5)

    assert proyecto.nombre == "Nuevo Proyecto 5"
    assert proyecto.slug == "nuevo-proyecto-5"


def test_crear_proyecto_con_slug_personalizado():
    proyecto = Proyecto.crear(propietario_id="usr-123", numero=0, slug="nuevo-proyecto-0-1")

    assert proyecto.nombre == "Nuevo Proyecto 0"
    assert proyecto.slug == "nuevo-proyecto-0-1"


def test_normalizar_nombre_exitoso():
    nombre = "  Mi Proyecto Especial  "
    normalizado = Proyecto.normalizar_nombre(nombre)
    assert normalizado == "Mi Proyecto Especial"


def test_normalizar_nombre_limite_40_caracteres():
    nombre_40 = "A" * 40
    assert Proyecto.normalizar_nombre(nombre_40) == nombre_40

    nombre_41 = "A" * 41
    with pytest.raises(NombreProyectoInvalidoException):
        Proyecto.normalizar_nombre(nombre_41)


def test_normalizar_nombre_vacio_invalido():
    with pytest.raises(NombreProyectoInvalidoException):
        Proyecto.normalizar_nombre("")

    with pytest.raises(NombreProyectoInvalidoException):
        Proyecto.normalizar_nombre("   ")


def test_actualizar_campos_proyecto():
    proyecto = Proyecto.crear(propietario_id="usr-123", numero=0)
    proyecto.actualizar(
        nombre="Arquitectura Cloud",
        color=ColorProyecto.azul,
        icono=IconoProyecto.estrella,
    )

    assert proyecto.nombre == "Arquitectura Cloud"
    assert proyecto.color == ColorProyecto.azul
    assert proyecto.icono == IconoProyecto.estrella
    assert proyecto.slug == "arquitectura-cloud"
