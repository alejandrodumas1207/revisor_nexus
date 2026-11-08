from revisor.dominio.calificacion import calificaciones_validas
from revisor.dominio.informe import CriterioEvaluado, InformeAlumno, componer_retroalimentacion
from revisor.dominio.integridad import VeredictoCopia, detalle_calificacion

RUBRICA_3 = calificaciones_validas(3, [100, 70, 40, 0])
CRITERIOS = (
    CriterioEvaluado("C1", "Preparación", 15, "parcial", "conteo_eq imprime filas."),
    CriterioEvaluado("C2", "Modelo", 25, "parcial", "Un solo panel."),
    CriterioEvaluado("C3", "Comprensión", 20, "parcial", "P2 bien; P6 sin relleno ni [UNK]."),
    CriterioEvaluado("C4", "Interpretación", 20, "no_cumple", "F1 y cifras incorrectas."),
    CriterioEvaluado("C5", "Conclusión", 20, "cumple", "Cita 0.8212."),
)


def _informe(
    copia: VeredictoCopia = VeredictoCopia.NINGUNA,
    justificacion_copia: str = "",
    avisos: tuple[str, ...] = (),
) -> InformeAlumno:
    lista = sum(c.obtenidos for c in CRITERIOS) / 10  # 62 → 6.2
    detalle = detalle_calificacion(lista, RUBRICA_3, copia=copia)
    fortalezas, pendientes = "Tu conclusión usa tus números.", "Corrige la P6."
    return InformeAlumno(CRITERIOS, detalle, fortalezas, pendientes, copia, justificacion_copia, avisos)


def test_desglose_y_total_cuadran():
    texto = componer_retroalimentacion(_informe())
    assert "• C1 Preparación: 10.5 de 15 (cumple parcialmente)." in texto
    assert "• C4 Interpretación: 0 de 20 (no cumple)." in texto
    assert "Total de la lista: 62 de 100 (6.2 de 10)" in texto


def test_ajuste_a_nexus_y_calificacion_final():
    texto = componer_retroalimentacion(_informe())
    assert texto.startswith("Calificación en NEXUS: 7")
    assert "• Ajuste a la calificación registrable en NEXUS → 7" in texto


def test_copia_parcial_explica_el_descuento():
    texto = componer_retroalimentacion(
        _informe(
            VeredictoCopia.PARCIAL,
            justificacion_copia="La P10 coincide palabra por palabra con un compañero.",
        )
    )
    assert "• Copia parcial: × 0.75 → 4.7" in texto  # 6.2 × 0.75 = 4.65
    assert texto.startswith("Calificación en NEXUS: 5")
    assert "Copia parcial: La P10 coincide" in texto


def test_sospecha_se_menciona_sin_descuento():
    texto = componer_retroalimentacion(
        _informe(VeredictoCopia.SOSPECHA, justificacion_copia="Mismo valor erróneo.")
    )
    assert "Sospecha de copia (sin descuento): Mismo valor erróneo." in texto
    assert texto.startswith("Calificación en NEXUS: 7")


def test_avisos_al_final():
    texto = componer_retroalimentacion(_informe(avisos=("Incluye tu matrícula en el nombre del archivo.",)))
    assert texto.endswith("Para la próxima entrega: Incluye tu matrícula en el nombre del archivo.")
