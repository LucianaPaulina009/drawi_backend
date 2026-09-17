from enum import Enum


class EstadoColaborador(str, Enum):
    """Estado de membresía de un colaborador."""

    ACTIVO = "activo"
    BLOQUEADO = "bloqueado"

    def esta_activo(self) -> bool:
        return self is EstadoColaborador.ACTIVO

    def esta_bloqueado(self) -> bool:
        return self is EstadoColaborador.BLOQUEADO
