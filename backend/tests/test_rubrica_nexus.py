import pytest

from revisor.dominio.modelos import CriterioRubricaNexus, OpcionRubricaNexus, RubricaNexus
from revisor.dominio.rubrica_nexus import CalificacionNoRegistrable, niveles_para_calificacion

PORCENTAJES = (100, 70, 40, 0)


def _criterio(cid: int) -> CriterioRubricaNexus:
    opciones = tuple(
        OpcionRubricaNexus(
            nivel_dominio_id=7000 + i, criterio_nivel_dominio_id=cid * 10 + i, posicion=i + 1, porcentaje=p
        )
        for i, p in enumerate(PORCENTAJES)
    )
    return CriterioRubricaNexus(cid, f"Criterio {cid}", opciones)


RUBRICA = RubricaNexus(1909378, (_criterio(1), _criterio(2), _criterio(3)))


def test_diez_marca_el_nivel_mas_alto_en_todos():
    niveles = niveles_para_calificacion(RUBRICA, 10)
    assert [n.nivel_dominio_id for n in niveles] == [7000, 7000, 7000]
    assert [n.criterio_id for n in niveles] == [1, 2, 3]


def test_nueve_combina_dos_completos_y_uno_suficiente():
    niveles = niveles_para_calificacion(RUBRICA, 9)
    assert sorted(n.nivel_dominio_id for n in niveles) == [7000, 7000, 7001]
    assert all(n.rubrica_id == 1909378 for n in niveles)


def test_calificacion_no_registrable_se_rechaza():
    with pytest.raises(CalificacionNoRegistrable):
        niveles_para_calificacion(RUBRICA, 3)
