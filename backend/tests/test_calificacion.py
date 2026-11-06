import pytest

from revisor.dominio.calificacion import calificaciones_validas, combinacion_rubrica

NIVELES = [100, 70, 40, 0]


def test_sin_rubrica_acepta_cualquier_entero():
    assert calificaciones_validas(None, NIVELES) == list(range(10, -1, -1))


def test_tres_criterios_con_niveles_habituales():
    assert calificaciones_validas(3, NIVELES) == [10, 9, 8, 7, 6, 5, 4, 0]


def test_combinacion_exacta():
    combo = combinacion_rubrica(9, 3, NIVELES)
    assert combo is not None
    assert combo.promedio == pytest.approx(90)
    assert combo.niveles == (0, 0, 1)  # dos en Completa y uno en Suficiente


def test_combinacion_sube_al_promedio_mas_cercano_por_arriba():
    # 3 no es válida con tres criterios: el promedio más bajo que la alcanza es 100+0+0 = 33.3
    combo = combinacion_rubrica(3, 3, NIVELES)
    assert combo is not None
    assert combo.promedio == pytest.approx(100 / 3)


def test_combinacion_sin_criterios_falla():
    with pytest.raises(ValueError):
        combinacion_rubrica(8, 0, NIVELES)
