import pytest

from revisor.dominio.retroalimentacion import (
    AccionRetro,
    RetroNexus,
    TipoAccion,
    VariasRetroalimentaciones,
    planear_retro,
)


def test_sin_retro_se_agrega():
    assert planear_retro([], "Citaste 0.75.") == AccionRetro(TipoAccion.AGREGAR, "Citaste 0.75.")


def test_misma_retro_no_se_toca_aunque_cambien_espacios():
    accion = planear_retro([RetroNexus(10, "Citaste  0.75\nde tu tabla.")], "Citaste 0.75 de tu tabla.")
    assert accion.tipo is TipoAccion.NINGUNA


def test_retro_equivocada_se_edita_en_su_lugar():
    accion = planear_retro([RetroNexus(10, "Dejaste las respuestas vacías.")], "Están en celdas nuevas.")
    assert accion == AccionRetro(TipoAccion.EDITAR, "Están en celdas nuevas.", 10)


def test_retro_de_prueba_se_edita_no_se_borra():
    accion = planear_retro([RetroNexus(40832413, "xchjvbkn")], "Versión final.")
    assert accion == AccionRetro(TipoAccion.EDITAR, "Versión final.", 40832413)


def test_varias_retros_detiene():
    with pytest.raises(VariasRetroalimentaciones):
        planear_retro([RetroNexus(10, "a"), RetroNexus(25, "b")], "final")


def test_retro_vacia_no_se_permite():
    with pytest.raises(ValueError):
        planear_retro([], "   ")
