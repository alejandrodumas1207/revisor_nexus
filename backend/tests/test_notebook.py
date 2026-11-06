import json

import pytest

from revisor.adaptadores.extractores.notebook import NotebookInvalido, leer_notebook


def _celda_md(texto: str) -> dict[str, object]:
    return {"cell_type": "markdown", "source": texto}


def _celda_code(texto: str, salidas: list[dict[str, object]] | None = None, n: int | None = 1):
    return {"cell_type": "code", "source": texto, "execution_count": n, "outputs": salidas or []}


def _notebook() -> bytes:
    celdas = [
        _celda_code('MATRICULA = "2012345"\nNOMBRE = "Ana Prueba"'),
        _celda_md(
            "### RESPUESTA E1D3-06\n\n**Pregunta.** ¿Qué ves?\n\n"
            "--- ESCRIBE TU RESPUESTA DEBAJO DE ESTA LINEA ---\n\nSube de 0.52 a 0.75."
        ),
        _celda_md("### RESPUESTA E1D3-08\n\n--- ESCRIBE TU RESPUESTA DEBAJO DE ESTA LINEA ---\n\n"),
        _celda_code(
            "# ====\n# INICIO E1D3-04 · CODIGO DEL ALUMNO\nlongitudes = [1, 2, 4, 8, 9, 11]\n# FIN E1D3-04\n",
            n=5,
        ),
        _celda_code(
            "# INICIO E1D3-05 · CODIGO DEL ALUMNO\nplt.plot(x)\n# FIN E1D3-05",
            [{"output_type": "error", "ename": "NameError", "evalue": "x no definido"}],
        ),
        _celda_code("print('sin correr')", n=None),
        _celda_code(
            "verificar()",
            [
                {
                    "output_type": "stream",
                    "text": "[OK  ] Identificación llenada\n[FALTA] Tabla generada\n"
                    "RESUMEN|E1D3|2012345|mejor_maxlen=9|codigo_ok=6/7\n",
                }
            ],
        ),
    ]
    return json.dumps({"cells": celdas, "nbformat": 4}).encode()


def test_identificacion():
    r = leer_notebook(_notebook())
    assert (r.matricula, r.nombre) == ("2012345", "Ana Prueba")


def test_respuestas_y_vacias():
    r = leer_notebook(_notebook())
    assert r.respuestas["E1D3-06"] == "Sube de 0.52 a 0.75."
    assert r.respuestas_vacias == ["E1D3-08"]


def test_bloques_de_codigo():
    r = leer_notebook(_notebook())
    assert r.bloques["E1D3-04"].codigo.endswith("longitudes = [1, 2, 4, 8, 9, 11]")
    assert r.bloques["E1D3-05"].error == "NameError: x no definido"


def test_ejecucion_y_errores():
    r = leer_notebook(_notebook())
    assert r.celdas_sin_ejecutar == 1
    assert r.errores == ("NameError: x no definido",)


def test_verificacion_y_resumen():
    r = leer_notebook(_notebook())
    assert r.verificacion == ((True, "Identificación llenada"), (False, "Tabla generada"))
    assert r.resumen == {"actividad": "E1D3", "matricula": "2012345", "mejor_maxlen": "9", "codigo_ok": "6/7"}


def test_respuesta_con_separador_borrado():
    celdas = [
        _celda_md(
            "### RESPUESTA E1D4-01\n\n**Pregunta.** ¿Cuántas reseñas hay?\n"
            "Tiene 3000 reseñas.\n\nMitad y mitad."
        ),
        _celda_md("### RESPUESTA E1D4-02\n\n**Pregunta.** ¿Y la etiqueta?\n"),
    ]
    r = leer_notebook(json.dumps({"cells": celdas}).encode())
    assert r.respuestas["E1D4-01"] == "Tiene 3000 reseñas.\n\nMitad y mitad."
    assert r.respuestas_vacias == ["E1D4-02"]


def test_respuesta_en_celda_agregada():
    celdas = [
        _celda_md("### RESPUESTA E1D3-08\n\n--- ESCRIBE TU RESPUESTA DEBAJO DE ESTA LINEA ---\n"),
        _celda_md("El estado oculto olvida los primeros tokens."),
        _celda_md("### RESPUESTA E1D3-09\n\n--- ESCRIBE TU RESPUESTA DEBAJO DE ESTA LINEA ---\n"),
        _celda_md("## 7 · Verificación"),
    ]
    r = leer_notebook(json.dumps({"cells": celdas}).encode())
    assert r.respuestas["E1D3-08"] == "El estado oculto olvida los primeros tokens."
    assert r.respuestas_vacias == ["E1D3-09"]


def test_plantilla_etapa_2():
    celdas = [
        _celda_md("## Pregunta - 3\nExplica por qué no se reacomodan los datos."),
        _celda_md(
            "++++ Inicia la seccion de agregar texto ++++\nPorque se filtra el futuro.\n"
            "++++ Termina la seccion de agregar texto ++++"
        ),
        _celda_md("## Pregunta - 5\nConstruye la LSTM."),
        _celda_code(
            "# ++++ Inicia la seccion de agregar codigo ++++\nmodelo = keras.Sequential([])\n"
            "# ++++ Termina la seccion de agregar codigo ++++",
            [{"output_type": "error", "ename": "NameError", "evalue": "keras"}],
        ),
    ]
    r = leer_notebook(json.dumps({"cells": celdas}).encode())
    assert r.respuestas == {"P03": "Porque se filtra el futuro."}
    assert "modelo = keras.Sequential([])" in r.bloques["P05"].codigo
    assert r.bloques["P05"].error == "NameError: keras"


def test_archivo_que_no_es_notebook():
    with pytest.raises(NotebookInvalido):
        leer_notebook(b"%PDF-1.7 ...")
