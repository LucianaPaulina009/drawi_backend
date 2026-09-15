from datetime import datetime, timezone
from uuid import uuid4

from app.modules.gestion_proyectos.application.ports.readers.listado_proyectos_usuario_reader import (
    ItemProyectoUsuarioDTO,
    ListadoProyectosUsuarioReader,
)
from app.modules.gestion_proyectos.application.queries.proyecto.listar_proyectos_usuario import (
    ListarProyectosUsuarioQuery,
    ListarProyectosUsuarioQueryHandler,
)


class FakeListadoProyectosUsuarioReader(ListadoProyectosUsuarioReader):
    def __init__(self, items: list[ItemProyectoUsuarioDTO]) -> None:
        self.items = items
        self.ultimo_usuario_id: str | None = None
        self.ultimo_solo_favoritos: bool | None = None

    def listar_por_usuario(
        self, usuario_id: str, solo_favoritos: bool = False
    ) -> list[ItemProyectoUsuarioDTO]:
        self.ultimo_usuario_id = usuario_id
        self.ultimo_solo_favoritos = solo_favoritos
        if solo_favoritos:
            return [item for item in self.items if item.es_favorito]
        return self.items


def test_handler_listar_todos_los_proyectos():
    item1 = ItemProyectoUsuarioDTO(
        id=uuid4(),
        nombre="Proyecto 1",
        color="celeste",
        icono="caja",
        fecha_actualizacion=datetime.now(timezone.utc),
        es_favorito=False,
        slug="proyecto-1",
    )
    item2 = ItemProyectoUsuarioDTO(
        id=uuid4(),
        nombre="Proyecto 2",
        color="azul",
        icono="estrella",
        fecha_actualizacion=datetime.now(timezone.utc),
        es_favorito=True,
        slug="proyecto-2",
    )
    fake_reader = FakeListadoProyectosUsuarioReader(items=[item1, item2])
    handler = ListarProyectosUsuarioQueryHandler(fake_reader)

    query = ListarProyectosUsuarioQuery(usuario_id="usr-123", solo_favoritos=False)
    resultado = handler.execute(query)

    assert fake_reader.ultimo_usuario_id == "usr-123"
    assert fake_reader.ultimo_solo_favoritos is False
    assert len(resultado.items) == 2
    assert resultado.items[0] == item1
    assert resultado.items[1] == item2


def test_handler_listar_solo_favoritos():
    item1 = ItemProyectoUsuarioDTO(
        id=uuid4(),
        nombre="Proyecto 1",
        color="celeste",
        icono="caja",
        fecha_actualizacion=datetime.now(timezone.utc),
        es_favorito=False,
        slug="proyecto-1",
    )
    item2 = ItemProyectoUsuarioDTO(
        id=uuid4(),
        nombre="Proyecto 2",
        color="azul",
        icono="estrella",
        fecha_actualizacion=datetime.now(timezone.utc),
        es_favorito=True,
        slug="proyecto-2",
    )
    fake_reader = FakeListadoProyectosUsuarioReader(items=[item1, item2])
    handler = ListarProyectosUsuarioQueryHandler(fake_reader)

    query = ListarProyectosUsuarioQuery(usuario_id="usr-123", solo_favoritos=True)
    resultado = handler.execute(query)

    assert fake_reader.ultimo_solo_favoritos is True
    assert len(resultado.items) == 1
    assert resultado.items[0] == item2
