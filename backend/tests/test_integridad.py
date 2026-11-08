from revisor.dominio.calificacion import calificaciones_validas
from revisor.dominio.integridad import ReglasIntegridad, Tardanza, VeredictoCopia, calificacion_final

SIN_RUBRICA = calificaciones_validas(None, [])
RUBRICA_3 = calificaciones_validas(3, [100, 70, 40, 0])


def test_sin_ajustes():
    assert calificacion_final(8.7, SIN_RUBRICA) == 9


def test_copia_confirmada_divide_a_la_mitad():
    assert calificacion_final(9.0, SIN_RUBRICA, copia=VeredictoCopia.CONFIRMADA) == 5  # 4.5 sube a 5


def test_copia_parcial_tres_cuartos():
    assert calificacion_final(8.0, SIN_RUBRICA, copia=VeredictoCopia.PARCIAL) == 6


def test_sospecha_no_sanciona():
    assert calificacion_final(9.0, SIN_RUBRICA, copia=VeredictoCopia.SOSPECHA) == 9


def test_veredictos_anteriores_se_traducen():
    assert VeredictoCopia.desde_texto("probable") is VeredictoCopia.SOSPECHA
    assert VeredictoCopia.desde_texto("coincidencia por plantilla") is VeredictoCopia.NINGUNA
    assert VeredictoCopia.desde_texto("copia parcial") is VeredictoCopia.PARCIAL
    assert VeredictoCopia.desde_texto(None) is VeredictoCopia.NINGUNA


def test_copia_con_rubrica_nexus_sube_a_valida():
    # 7 × 0.5 = 3.5; con tres criterios lo siguiente registrable es 4
    assert calificacion_final(7.0, RUBRICA_3, copia=VeredictoCopia.CONFIRMADA) == 4


def test_formato_incorrecto_resta_un_punto():
    assert calificacion_final(10.0, SIN_RUBRICA, formato_incorrecto=True) == 9


def test_formato_con_rubrica_nexus_puede_absorberse_al_subir_a_valida():
    # 4 − 1 = 3 no se puede registrar con tres criterios; sube a 4 (política hacia arriba)
    assert calificacion_final(4.0, RUBRICA_3, formato_incorrecto=True) == 4


def test_tardanza_confirmada_resta_un_punto():
    assert calificacion_final(8.0, SIN_RUBRICA, tardanza=Tardanza.CONFIRMADA) == 7


def test_tardanza_dudosa_no_penaliza():
    assert calificacion_final(8.0, SIN_RUBRICA, tardanza=Tardanza.DUDOSA) == 8


def test_penalizaciones_configurables_y_acumuladas():
    reglas = ReglasIntegridad(puntos_tardia=2.0)
    final = calificacion_final(
        10.0, SIN_RUBRICA, formato_incorrecto=True, tardanza=Tardanza.CONFIRMADA, reglas=reglas
    )
    assert final == 7
