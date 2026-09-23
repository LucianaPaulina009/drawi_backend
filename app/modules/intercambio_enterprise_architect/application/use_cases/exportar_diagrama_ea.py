from __future__ import annotations

from uuid import UUID

from app.modules.diagramas.application.queries.diagrama.obtener_diagrama import (
    ObtenerDiagramaCompletoQueryHandler,
    ObtenerDiagramaQuery,
)
from app.modules.diagramas.application.queries.dtos import DiagramaDetalleDTO
from app.modules.diagramas.application.validaciones import (
    obtener_diagrama_autorizado,
)
from app.modules.diagramas.domain.repositories.diagrama_repository import (
    DiagramaRepository,
)
from app.modules.gestion_colaboradores.domain.repositories.colaborador_proyecto_repository import (
    ColaboradorProyectoRepository,
)
from app.modules.gestion_proyectos.domain.repositories.proyecto_repository import (
    ProyectoRepository,
)
from app.modules.intercambio_enterprise_architect.application.services.serializador_xmi_enterprise_architect import (
    SerializadorXmiEnterpriseArchitect,
)
from app.shared.domain.exceptions import ValidationException


class ExportarDiagramaEaUseCase:
    """Caso de uso para exportar el diagrama activo a formato XML XMI 2.1
    compatible con Enterprise Architect.
    """

    def __init__(
        self,
        proyecto_repository: ProyectoRepository,
        diagrama_repository: DiagramaRepository,
        query_diagrama: ObtenerDiagramaCompletoQueryHandler,
        colaborador_repository: ColaboradorProyectoRepository | None = None,
    ) -> None:
        self.proyecto_repo = proyecto_repository
        self.diagrama_repo = diagrama_repository
        self.query_diagrama = query_diagrama
        self.colaborador_repo = colaborador_repository

    def execute(
        self,
        *,
        usuario_id: str,
        proyecto_id: UUID,
        diagrama_id: UUID,
    ) -> tuple[str, str]:
        # 1. Autorización de acceso (lectura o edición)
        diagrama = obtener_diagrama_autorizado(
            propietario_id=usuario_id,
            diagrama_id=diagrama_id,
            proyecto_repository=self.proyecto_repo,
            diagrama_repository=self.diagrama_repo,
            colaborador_repository=self.colaborador_repo,
            exigir_edicion=False,
        )

        if diagrama.id_proyecto != proyecto_id:
            raise ValidationException(
                "El diagrama no pertenece al proyecto especificado.",
                code="DIAGRAMA_NO_ENCONTRADO",
            )

        # 2. Obtener snapshot inmutable completo del diagrama
        diagrama_dto: DiagramaDetalleDTO = self.query_diagrama.execute(
            ObtenerDiagramaQuery(
                proyecto_id=proyecto_id,
                diagrama_id=diagrama_id,
                usuario_id=usuario_id,
            )
        )

        # 3. Regla: solo se puede exportar si hay elementos en el diagrama
        if not diagrama_dto.clases or len(diagrama_dto.clases) == 0:
            raise ValidationException(
                "El diagrama actual está en blanco. Se requiere al menos una clase para poder exportar a Enterprise Architect.",
                code="DIAGRAMA_VACIO",
            )

        # 4. Serializar a XML XMI 2.1 con geometría EA
        contenido_xml = SerializadorXmiEnterpriseArchitect.serializar(diagrama_dto)

        import re
        import unicodedata

        nombre_raw = (diagrama_dto.nombre or "diagrama").strip()
        nombre_ascii = unicodedata.normalize("NFKD", nombre_raw).encode("ascii", "ignore").decode("ascii")
        nombre_limpio = re.sub(r"[^\w\-_]", "_", nombre_ascii.lower()).strip("_") or "diagrama"
        nombre_archivo = f"{nombre_limpio}_ea.xml"

        return contenido_xml, nombre_archivo
