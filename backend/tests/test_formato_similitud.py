import pytest

from revisor.dominio.formato import nombre_antes_de_forms, revisar_formato
from revisor.dominio.similitud import normalizar_codigo, normalizar_texto, pares_similares


def test_quita_sufijo_de_forms():
    assert nombre_antes_de_forms("E1_D3_2012345_Perez - Ana Perez.ipynb") == "E1_D3_2012345_Perez.ipynb"


def test_formato_correcto():
    r = revisar_formato("E1_D3_2012345_Perez - Ana Perez.ipynb", "E1_D3")
    assert r.correcto
    assert r.matricula_en_nombre == "2012345"


def test_notebook_guardado_como_txt():
    r = revisar_formato("E1_D3_2012345_Perez.ipynb - Ana Perez.txt", "E1_D3")
    assert r.extension == ".ipynb.txt"
    assert not r.correcto


@pytest.mark.parametrize(
    ("nombre", "fragmento"),
    [
        ("Tarea 1 - Ana Perez.pdf", "Entregó .pdf"),
        ("Tarea 1 - Ana Perez.pdf", "no inicia con E1_D3"),
        ("E1_D3_Perez - Ana Perez.ipynb", "no incluye la matrícula"),
    ],
)
def test_observaciones_de_formato(nombre, fragmento):
    assert any(fragmento in o for o in revisar_formato(nombre, "E1_D3").observaciones)


def test_codigo_igual_con_otros_comentarios_y_espacios():
    a = normalizar_codigo("x = [1, 2, 4]  # mi lista\nplt.plot(x)")
    b = normalizar_codigo("# copiado\nx=[1,2,4]\nplt.plot( x )")
    assert pares_similares({"a": a, "b": b}, umbral=0.99, n=3)[0].similitud == 1.0


def test_textos_distintos_no_se_marcan():
    a = normalizar_texto("La exactitud sube de 0.52 a 0.75 cuando aumenta maxlen hasta nueve tokens")
    b = normalizar_texto("Recomendaría doce tokens y cinco épocas porque tarda poco y no sobreajusta")
    assert pares_similares({"a": a, "b": b}, umbral=0.2) == []
