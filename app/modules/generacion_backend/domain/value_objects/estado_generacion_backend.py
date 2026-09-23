from enum import Enum


class EstadoGeneracionBackend(str, Enum):
    VALIDANDO = "validando"
    GENERANDO = "generando"
    EMPAQUETANDO = "empaquetando"
    COMPLETADO = "completado"
    ERROR = "error"

    @classmethod
    def validar(cls, valor: "EstadoGeneracionBackend | str") -> "EstadoGeneracionBackend":
        if isinstance(valor, cls):
            return valor
        for miembro in cls:
            if miembro.value == valor:
                return miembro
        valores = ", ".join(m.value for m in cls)
        raise ValueError(f"Estado de generación inválido '{valor}'. Válidos: {valores}")
