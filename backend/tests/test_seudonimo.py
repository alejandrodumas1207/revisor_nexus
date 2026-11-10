from revisor.dominio.seudonimo import datos_personales_restantes, seudonimizar


def test_reemplaza_matricula_y_nombre_con_o_sin_acentos():
    texto = 'MATRICULA = "2251387"\nNOMBRE = "Hernández Valero Jesús"\nHecho por Hernandez.'
    limpio = seudonimizar(texto, ["Hernández Valero Jesús"])
    assert "2251387" not in limpio
    assert "Hernández" not in limpio and "Hernandez" not in limpio and "Jesús" not in limpio
    assert "[MATRICULA]" in limpio and "ALUMNO" in limpio


def test_no_toca_particulas_cortas_ni_otros_numeros():
    limpio = seudonimizar("La red de Ana tiene 386,564 parámetros y 0.8212", ["Ana de la Cruz"])
    assert "La red de" in limpio
    assert "386,564" in limpio and "0.8212" in limpio
    assert "Cruz" not in seudonimizar("Cruz", ["Ana de la Cruz"])


def test_nombre_en_archivo_con_guiones_bajos():
    assert "Tamez" not in seudonimizar("E2_D3_Tamez_García.ipynb", ["Tamez_García"])


def test_detecta_datos_personales_restantes():
    nombres = ["Prueba Luna Ana"]
    assert datos_personales_restantes(seudonimizar("Ana Prueba 2012345", nombres), nombres) == []
    assert datos_personales_restantes("Hecho por LUNA, 2012345", nombres) == ["2012345", "Luna"]
