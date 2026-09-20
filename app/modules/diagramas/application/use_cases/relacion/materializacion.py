from __future__ import annotations

from collections.abc import Iterable

from app.modules.diagramas.domain.entities.atributo import Atributo
from app.modules.diagramas.domain.entities.referencia_fk import ReferenciaFK
from app.modules.diagramas.domain.entities.relacion import Relacion
from app.modules.diagramas.domain.exceptions import MaterializacionRelacionRequeridaException
from app.modules.diagramas.domain.value_objects.tipo_relacion import TipoRelacion


TIPOS_RELACIONALES = {
    TipoRelacion.ASOCIACION.value,
    TipoRelacion.ASOCIACION_DIRIGIDA.value,
    TipoRelacion.AGREGACION.value,
    TipoRelacion.COMPOSICION.value,
}


def _maximo(cardinalidad: str) -> int | None:
    valor = cardinalidad.strip()
    limite = valor.split("..", 1)[-1] if ".." in valor else valor
    return None if limite == "*" else int(limite)


def requiere_materializacion(relacion: Relacion) -> bool:
    if relacion.tipo_relacion in {
        TipoRelacion.HERENCIA.value,
        TipoRelacion.REALIZACION.value,
        TipoRelacion.DEPENDENCIA.value,
    }:
        return True
    if relacion.tipo_relacion not in TIPOS_RELACIONALES:
        return False
    origen_muchos = _maximo(relacion.cardinalidad_origen) is None or _maximo(relacion.cardinalidad_origen) > 1
    destino_muchos = _maximo(relacion.cardinalidad_destino) is None or _maximo(relacion.cardinalidad_destino) > 1
    return not (origen_muchos and destino_muchos)


def referencia_materializa_relacion(
    relacion: Relacion, referencia: ReferenciaFK, atributo_fk: Atributo, atributo_referenciado: Atributo
) -> bool:
    if atributo_fk.id_clase not in {relacion.id_clase_origen, relacion.id_clase_destino}:
        return False
    if atributo_referenciado.id_clase not in {relacion.id_clase_origen, relacion.id_clase_destino}:
        return False
    if relacion.tipo_relacion in {
        TipoRelacion.HERENCIA.value,
        TipoRelacion.REALIZACION.value,
        TipoRelacion.DEPENDENCIA.value,
    }:
        return (
            atributo_fk.id_clase == relacion.id_clase_origen
            and atributo_referenciado.id_clase == relacion.id_clase_destino
        )
    if relacion.id_clase_origen == relacion.id_clase_destino:
        return True
    origen_muchos = _maximo(relacion.cardinalidad_origen) is None or _maximo(relacion.cardinalidad_origen) > 1
    destino_muchos = _maximo(relacion.cardinalidad_destino) is None or _maximo(relacion.cardinalidad_destino) > 1
    if origen_muchos != destino_muchos:
        clase_muchos = relacion.id_clase_origen if origen_muchos else relacion.id_clase_destino
        clase_uno = relacion.id_clase_destino if origen_muchos else relacion.id_clase_origen
        return atributo_fk.id_clase == clase_muchos and atributo_referenciado.id_clase == clase_uno
    return atributo_fk.id_clase != atributo_referenciado.id_clase


def asegurar_materializacion_valida(
    relacion: Relacion,
    referencias: Iterable[ReferenciaFK],
    obtener_atributo,
) -> None:
    if not requiere_materializacion(relacion):
        return
    for referencia in referencias:
        atributo_fk = obtener_atributo(referencia.id_atributo_fk)
        atributo_referenciado = obtener_atributo(referencia.id_atributo_referenciado)
        if atributo_fk and atributo_referenciado and referencia_materializa_relacion(
            relacion, referencia, atributo_fk, atributo_referenciado
        ):
            return
    raise MaterializacionRelacionRequeridaException()
