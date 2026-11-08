from revisor.dominio.calificacion import calificaciones_validas
from revisor.dominio.informe import CriterioEvaluado, InformeAlumno, componer_retroalimentacion
from revisor.dominio.integridad import VeredictoCopia, detalle_calificacion

RUBRICA_3 = calificaciones_validas(3, [100, 70, 40, 0])
CRITERIOS = (
    CriterioEvaluado("C1", "Preparación", 15, "parcial", "Conteo correcto; conteo_eq imprime filas."),
    CriterioEvaluado("C2", "Modelo", 25, "parcial", "Entrena bien; un solo panel."),
    CriterioEvaluado("C3", "Comprensión", 20, "parcial", "P2 bien; P6 sin relleno ni [UNK]."),
    CriterioEvaluado("C4", "Interpretación", 20, "no_cumple", "F1 y cifras incorrectas."),
    CriterioEvaluado("C5", "Conclusión", 20, "cumple", "Cita 0.8212."),
)


def _informe(
    copia: VeredictoCopia = VeredictoCopia.NINGUNA,
    copia_con: tuple[str, ...] = (),
    justificacion: str = "",
    generales: str = "",
    avisos: tuple[str, ...] = (),
) -> InformeAlumno:
    lista = sum(c.obtenidos for c in CRITERIOS) / 10  # 62 → 6.2
    detalle = detalle_calificacion(lista, RUBRICA_3, copia=copia)
    return InformeAlumno(CRITERIOS, detalle, generales, copia, copia_con, justificacion, avisos)


def test_desglose_y_total_cuadran():
    texto = componer_retroalimentacion(_informe())
    assert "• C1 Preparación: 10.5 de 15 (cumple parcialmente). Conteo correcto" in texto
    assert "• C4 Interpretación: 0 de 20 (no cumple)." in texto
    assert "Total de la lista: 62 de 100 (6.2 de 10)" in texto


def test_sin_apartados_de_bien_y_mal_ni_generales_vacios():
    texto = componer_retroalimentacion(_informe())
    assert "Lo que hiciste bien" not in texto
    assert "Comentarios generales" not in texto
    assert texto.startswith("Calificación en NEXUS: 7")
    assert texto.endswith("• Ajuste a la calificación registrable en NEXUS → 7")


def test_copia_parcial_nombra_al_companero_y_explica():
    texto = componer_retroalimentacion(
        _informe(
            VeredictoCopia.PARCIAL,
            ("Treviño Ruiz Luis (2251411)",),
            "Tu E1D3-08 repite su secuencia de ideas y la frase 'se pierde información valiosa'.",
        )
    )
    assert "• Copia parcial: × 0.75 → 4.7" in texto  # 6.2 × 0.75 = 4.65
    assert texto.startswith("Calificación en NEXUS: 5")
    assert "• Copia parcial (calificación × 0.75) con Treviño Ruiz Luis (2251411): Tu E1D3-08" in texto


def test_sospecha_sin_penalizacion():
    texto = componer_retroalimentacion(
        _informe(VeredictoCopia.SOSPECHA, ("Ana (1)",), "Mismo valor erróneo.")
    )
    assert "Sospecha de copia (sin penalización) con Ana (1): Mismo valor erróneo." in texto
    assert "descuento" not in texto
    assert texto.startswith("Calificación en NEXUS: 7")


def test_comentarios_generales_y_avisos_opcionales():
    texto = componer_retroalimentacion(
        _informe(
            generales="Buen avance respecto a la etapa 1.", avisos=("Incluye tu matrícula en el nombre.",)
        )
    )
    assert texto.endswith(
        "Comentarios generales:\n• Buen avance respecto a la etapa 1.\n"
        "• Para la próxima entrega: Incluye tu matrícula en el nombre."
    )
