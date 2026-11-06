import pytest

from revisor.dominio.retroalimentacion import (
    AccionRetro,
    RetroNexus,
    TipoAccion,
    eliminar_retro,
    planear_retro,
)


def test_sin_retro_se_agrega():
    plan = planear_retro([], "Citaste 0.75 de tu tabla.")
    assert plan.acciones == (AccionRetro(TipoAccion.AGREGAR, "Citaste 0.75 de tu tabla."),)


def test_misma_retro_no_hace_nada_aunque_cambien_espacios():
    plan = planear_retro([RetroNexus(10, "Citaste  0.75\nde tu tabla.")], "Citaste 0.75 de tu tabla.")
    assert plan.sin_cambios


def test_retro_distinta_se_edita_en_su_lugar():
    plan = planear_retro(
        [RetroNexus(10, "Dejaste las respuestas vacías.")], "Tus respuestas están en celdas nuevas."
    )
    assert plan.acciones == (AccionRetro(TipoAccion.EDITAR, "Tus respuestas están en celdas nuevas.", 10),)


def test_varias_retros_edita_la_mas_reciente_y_avisa():
    plan = planear_retro([RetroNexus(10, "vieja"), RetroNexus(25, "xchjvbkn")], "La buena.")
    assert plan.acciones == (AccionRetro(TipoAccion.EDITAR, "La buena.", 25),)
    assert plan.advertencias


def test_varias_retros_consolidando_elimina_las_demas():
    plan = planear_retro([RetroNexus(10, "vieja"), RetroNexus(25, "otra")], "La buena.", consolidar=True)
    assert AccionRetro(TipoAccion.ELIMINAR, retro_id=10) in plan.acciones
    assert not plan.advertencias


def test_conserva_la_que_ya_coincide_aunque_no_sea_la_mas_reciente():
    plan = planear_retro(
        [RetroNexus(10, "La buena."), RetroNexus(25, "xchjvbkn")], "La buena.", consolidar=True
    )
    assert plan.acciones == (AccionRetro(TipoAccion.ELIMINAR, retro_id=25),)


def test_retro_vacia_no_se_permite():
    with pytest.raises(ValueError):
        planear_retro([RetroNexus(10, "x")], "   ")


def test_eliminar_solo_retros_del_alumno():
    assert eliminar_retro([RetroNexus(25, "xchjvbkn")], 25).acciones[0].tipo is TipoAccion.ELIMINAR
    with pytest.raises(ValueError):
        eliminar_retro([RetroNexus(25, "xchjvbkn")], 99)
