from app.modules.diagramas.domain.entities.atributo import Atributo
from app.modules.diagramas.infrastructure.persistence.models.atributo_model import AtributoModel

class AtributoMapper:
    @staticmethod
    def a_dominio(m: AtributoModel) -> Atributo:
        return Atributo(id=m.id,id_clase=m.id_clase,tipo_dato=m.tipo_dato,nombre=m.nombre,longitud=m.longitud,precision=m.precision,escala=m.escala,es_llave_primaria=m.es_llave_primaria,permite_nulo=m.permite_nulo,es_unico=m.es_unico,valor_por_defecto=m.valor_por_defecto,orden_de_posicion=m.orden_de_posicion)
    @staticmethod
    def a_modelo(e: Atributo) -> AtributoModel:
        return AtributoModel(id=e.id,id_clase=e.id_clase,tipo_dato=e.tipo_dato,nombre=e.nombre,longitud=e.longitud,precision=e.precision,escala=e.escala,es_llave_primaria=e.es_llave_primaria,permite_nulo=e.permite_nulo,es_unico=e.es_unico,valor_por_defecto=e.valor_por_defecto,orden_de_posicion=e.orden_de_posicion)
