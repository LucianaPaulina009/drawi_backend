from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class ErrorGeneracion:
    codigo: str
    mensaje: str
    elemento_tipo: str  # "diagrama" | "clase" | "atributo" | "relacion" | "referencia_fk" | "estructura_nm"
    elemento: str | None = None
    elemento_id: str | None = None
    detalle: str | None = None

    def a_dict(self) -> dict[str, Any]:
        resultado = {
            "codigo": self.codigo,
            "mensaje": self.mensaje,
            "elemento_tipo": self.elemento_tipo,
        }
        if self.elemento is not None:
            resultado["elemento"] = self.elemento
        if self.elemento_id is not None:
            resultado["elemento_id"] = self.elemento_id
        if self.detalle is not None:
            resultado["detalle"] = self.detalle
        return resultado


@dataclass(slots=True)
class DiagnosticoGeneracion:
    valido: bool
    errores_bloqueantes: list[ErrorGeneracion] = field(default_factory=list)
    advertencias: list[ErrorGeneracion] = field(default_factory=list)

    @classmethod
    def exitoso(cls, advertencias: list[ErrorGeneracion] | None = None) -> DiagnosticoGeneracion:
        return cls(valido=True, errores_bloqueantes=[], advertencias=advertencias or [])

    @classmethod
    def con_errores(
        cls,
        errores: list[ErrorGeneracion],
        advertencias: list[ErrorGeneracion] | None = None,
    ) -> DiagnosticoGeneracion:
        return cls(
            valido=len(errores) == 0,
            errores_bloqueantes=errores,
            advertencias=advertencias or [],
        )

    def agregar_error(self, error: ErrorGeneracion) -> None:
        self.errores_bloqueantes.append(error)
        self.valido = False

    def agregar_advertencia(self, advertencia: ErrorGeneracion) -> None:
        self.advertencias.append(advertencia)
