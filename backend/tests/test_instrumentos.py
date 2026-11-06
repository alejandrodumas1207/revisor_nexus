import pytest

from revisor.dominio.calificacion import PoliticaAjuste, ajustar_a_valida, calificaciones_validas
from revisor.dominio.instrumentos import (
    CriterioPropio,
    ItemCotejo,
    ListaCotejo,
    NivelPropio,
    RubricaPropia,
)

NIVELES = (NivelPropio("Logrado", 100), NivelPropio("En proceso", 60), NivelPropio("No presenta", 0))


def _lista() -> ListaCotejo:
    return ListaCotejo(
        "Libreta Dimensión 2",
        (
            ItemCotejo("vocab", "Vocabulario completo", 2),
            ItemCotejo("ejer", "Ejercicios resueltos", 2),
            ItemCotejo("fecha", "Fecha y título", 1),
        ),
    )


def test_lista_cotejo_completa():
    assert _lista().calificar({"vocab", "ejer", "fecha"}) == pytest.approx(10)


def test_lista_cotejo_ponderada():
    assert _lista().calificar({"vocab", "fecha"}) == pytest.approx(6)


def test_lista_cotejo_rechaza_item_inexistente():
    with pytest.raises(ValueError):
        _lista().calificar({"firma"})


def test_lista_cotejo_rechaza_ids_repetidos():
    with pytest.raises(ValueError):
        ListaCotejo("x", (ItemCotejo("a", "uno"), ItemCotejo("a", "dos")))


def test_rubrica_propia_ponderada():
    rubrica = RubricaPropia(
        "Notebook RNN",
        (
            CriterioPropio("codigo", "Código funciona", NIVELES, peso=2),
            CriterioPropio("analisis", "Análisis de resultados", NIVELES, peso=1),
        ),
    )
    # (2·100 + 1·60) / 3 = 86.7 → 8.67
    assert rubrica.calificar({"codigo": 0, "analisis": 1}) == pytest.approx(260 / 30)


def test_rubrica_propia_exige_todos_los_criterios():
    rubrica = RubricaPropia("r", (CriterioPropio("a", "A", NIVELES),))
    with pytest.raises(ValueError):
        rubrica.calificar({})


@pytest.mark.parametrize(
    ("valor", "politica", "esperada"),
    [
        (3.0, PoliticaAjuste.ARRIBA, 4),
        (3.0, PoliticaAjuste.ABAJO, 0),
        (3.0, PoliticaAjuste.CERCANA, 4),
        (8.67, PoliticaAjuste.ARRIBA, 9),
        (8.67, PoliticaAjuste.CERCANA, 9),
        (8.4, PoliticaAjuste.CERCANA, 8),
        (10.0, PoliticaAjuste.ARRIBA, 10),
    ],
)
def test_ajuste_con_rubrica_nexus_de_tres_criterios(valor, politica, esperada):
    validas = calificaciones_validas(3, [100, 70, 40, 0])  # [10, 9, 8, 7, 6, 5, 4, 0]
    assert ajustar_a_valida(valor, validas, politica) == esperada


def test_sin_rubrica_nexus_cualquier_entero():
    assert ajustar_a_valida(6.5, calificaciones_validas(None, []), PoliticaAjuste.CERCANA) == 7
