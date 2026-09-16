from __future__ import annotations

from uuid import UUID, uuid4

from app.modules.gestion_proyectos.domain.value_objects.estado_colaborador import (
    EstadoColaborador,
)
from app.modules.gestion_proyectos.domain.value_objects.rol_colaborador import (
    RolColaborador,
)


class ColaboradorProyecto:
    """Entidad de dominio para representar la membresía de un colaborador en un proyecto."""

    def __init__(
        self,
        id: UUID,
        id_proyecto: UUID,
        id_usuario: str,
        rol: RolColaborador,
        estado: EstadoColaborador,
    ) -> None:
        self.id = id
        self.id_proyecto = id_proyecto
        self.id_usuario = id_usuario
        self.rol = rol if isinstance(rol, RolColaborador) else RolColaborador(rol)
        self.estado = (
            estado if isinstance(estado, EstadoColaborador) else EstadoColaborador(estado)
        )

    @classmethod
    def crear(
        cls,
        *,
        id_proyecto: UUID,
        id_usuario: str,
        rol: RolColaborador = RolColaborador.VER,
        estado: EstadoColaborador = EstadoColaborador.ACTIVO,
    ) -> ColaboradorProyecto:
        """Fábrica de dominio para incorporar un nuevo colaborador."""
        return cls(
            id=uuid4(),
            id_proyecto=id_proyecto,
            id_usuario=id_usuario,
            rol=rol,
            estado=estado,
        )

    def cambiar_rol(self, nuevo_rol: RolColaborador | str) -> None:
        """Actualiza el rol del colaborador."""
        self.rol = nuevo_rol if isinstance(nuevo_rol, RolColaborador) else RolColaborador(nuevo_rol)

    def bloquear(self) -> None:
        """Cambia el estado a bloqueado preservando el rol base."""
        self.estado = EstadoColaborador.BLOQUEADO

    def desbloquear(self) -> None:
        """Restaura el estado a activo preservando el rol base."""
        self.estado = EstadoColaborador.ACTIVO

    def esta_activo(self) -> bool:
        return self.estado.esta_activo()

    def esta_bloqueado(self) -> bool:
        return self.estado.esta_bloqueado()
