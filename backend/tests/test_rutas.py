from pathlib import PurePath

from revisor.dominio.rutas import carpeta_elemento, nombre_archivo_entrega


def test_dimension():
    assert carpeta_elemento("1.2", "Dimensión 2: vocabulario") == PurePath("Etapa 1/Dimensión 2")


def test_dimension_sin_acento():
    assert carpeta_elemento("2.3", "dimension 3") == PurePath("Etapa 2/Dimensión 3")


def test_evidencia():
    assert carpeta_elemento("1.4", "Evidencia de aprendizaje 1") == PurePath(
        "Etapa 1/Evidencia de Aprendizaje"
    )


def test_otro_elemento():
    assert carpeta_elemento("3.1", "Proyecto") == PurePath("Etapa 3/Elemento 1")


def test_pia():
    assert carpeta_elemento("PIA") == PurePath("PIA")


def test_nombre_archivo_con_varios():
    assert nombre_archivo_entrega("2012345", "Pérez Luna Ana", ".PDF", 2) == "2012345_PÉREZ LUNA ANA_2.pdf"
