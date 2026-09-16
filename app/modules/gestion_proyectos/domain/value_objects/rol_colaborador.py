from enum import Enum


class RolColaborador(str, Enum):
    """Rol de un colaborador en un proyecto."""

    VER = "ver"
    EDITOR = "editor"
    COMENTARISTA = "comentarista"

    def puede_editar(self) -> bool:
        return self is RolColaborador.EDITOR

    def puede_comentar(self) -> bool:
        return self in (RolColaborador.EDITOR, RolColaborador.COMENTARISTA)
