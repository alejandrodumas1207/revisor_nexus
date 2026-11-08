from revisor.dominio.verificacion import aparece, cifras_citadas, cifras_no_encontradas, sin_trabajo

SALIDAS = "maxlen  exactitud\n1  0.5800\n9  0.7427\n12  0.7533\nTotal params: 386,564\nTiempo: 4.3 s"


def test_extrae_decimales_miles_y_porcentajes_pero_no_enteros_sueltos():
    assert cifras_citadas("En E1D3-06 cito 0.7533, 75.3 % y 386,564 parámetros; la pregunta 9 dice 3") == [
        "0.7533",
        "75.3%",
        "386,564",
    ]


def test_acepta_redondeo_y_porcentaje():
    valores = [0.5800, 0.7427, 0.7533, 386564.0]
    assert aparece("0.75", valores)  # 0.7533 redondeado
    assert aparece("75.3%", valores)  # 0.7533 como porcentaje
    assert aparece("74%", valores)  # 0.7427
    assert aparece("386,564", valores)
    assert not aparece("0.38", valores)
    assert not aparece("0.7493", valores)  # cifra de otro alumno


def test_cifras_que_no_salen_del_cuaderno():
    respuestas = {
        "E1D3-06": "pasa de 0.38 en maxlen 1 a 0.52",
        "E1D3-10": "recomiendo 12, con 0.7533 y 4.3 s",
    }
    assert cifras_no_encontradas(respuestas, SALIDAS) == {"E1D3-06": ["0.38", "0.52"]}


def test_entrega_sin_trabajo():
    assert sin_trabajo({"A": "", "B": "  "}, celdas_con_salida=0)
    assert sin_trabajo({}, celdas_con_salida=0)


def test_con_salidas_no_es_sin_trabajo_aunque_falte_numero_de_ejecucion():
    # Plantilla no reconocida (sin respuestas extraídas) pero con celdas ejecutadas: sí hay trabajo
    assert not sin_trabajo({}, celdas_con_salida=12)
    assert not sin_trabajo({"A": "Mi respuesta"}, celdas_con_salida=0)
