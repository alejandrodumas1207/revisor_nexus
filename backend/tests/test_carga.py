from collections.abc import Mapping
from typing import Any

import pytest

from revisor.adaptadores.nexus_api.escritura import ErrorNexus, EscrituraNexusApi
from revisor.dominio.modelos import CalificacionNexus, Elemento, NivelRubricaNexus, TipoElemento
from revisor.dominio.retroalimentacion import RetroNexus, TipoAccion, VariasRetroalimentaciones
from revisor.servicios.carga import borrar_retro_elegida, subir_revision

DIMENSION = Elemento("1.2", 4560461, TipoElemento.EVIDENCIA, "Dimensión 2", 2.5, False, None, None, None)
EVIDENCIA = Elemento("1.4", 4560463, TipoElemento.EVIDENCIA, "Evidencia", 5, True, 3, None, None)
NIVELES = (NivelRubricaNexus(1909378, 9193517, 7542588, 33971437),)
CALIFICAR = "Portafolio/ActualizarCalificacionesElementoEvaluable"
RETRO = "Retroalimentacion/ActualizarRetroalimentacion"


class ClienteFalso:
    """Registra lo que se enviaría a NEXUS y contesta como lo hace NEXUS."""

    def __init__(self, error: bool = False) -> None:
        self.enviados: list[tuple[str, Mapping[str, Any]]] = []
        self.error = error

    def post_json(self, ruta: str, cuerpo: Mapping[str, Any]) -> dict[str, Any]:
        self.enviados.append((ruta, cuerpo))
        if self.error:
            return {"Code": 2011, "Message": "La sesión no existe."}
        if ruta.endswith("EliminarRetroalimentacion"):
            return {"RetroalimentacionEliminada": True}
        return {"Calificaiones": [{"CuentaId": e["CuentaId"]} for e in cuerpo["Estudiantes"]]}

    def post_form(self, ruta: str, campos: Mapping[str, str]) -> dict[str, Any]:
        self.enviados.append((ruta, campos))
        return {"Retroalimentacion": {"RetroalimentacionId": int(campos["RetroalimentacionId"]) or 500}}

    @property
    def rutas(self) -> list[str]:
        return [r for r, _ in self.enviados]


def _subir(cliente: ClienteFalso, existentes: list[RetroNexus], final: str, valor: int = 100):
    return subir_revision(
        EscrituraNexusApi(cliente), 747689, DIMENSION, CalificacionNexus(748333, valor), existentes, final
    )


def test_calificacion_sin_rubrica_va_en_escala_100():
    cliente = ClienteFalso()
    EscrituraNexusApi(cliente).guardar_calificaciones(747689, DIMENSION, [CalificacionNexus(748333, 90)])
    ruta, cuerpo = cliente.enviados[0]
    assert ruta == CALIFICAR
    assert cuerpo["UsaRubrica"] is False
    assert cuerpo["Estudiantes"][0]["Calificacion"]["Valor"] == "90"


def test_calificacion_con_rubrica_envia_niveles():
    cliente = ClienteFalso()
    EscrituraNexusApi(cliente).guardar_calificaciones(
        747689, EVIDENCIA, [CalificacionNexus(748333, 100, NIVELES)]
    )
    assert cliente.enviados[0][1]["Estudiantes"][0]["Rubrica"][0]["CriterioNivelDominioId"] == 33971437


def test_rubrica_sin_niveles_no_se_envia():
    cliente = ClienteFalso()
    with pytest.raises(ValueError):
        EscrituraNexusApi(cliente).guardar_calificaciones(747689, EVIDENCIA, [CalificacionNexus(748333, 100)])
    assert cliente.enviados == []


def test_sesion_vencida_es_error():
    with pytest.raises(ErrorNexus, match="La sesión no existe"):
        _subir(ClienteFalso(error=True), [], "Completa.")


def test_agrega_retro_cuando_no_hay():
    cliente = ClienteFalso()
    assert _subir(cliente, [], "Completa.").retro_id == 500
    assert cliente.rutas == [CALIFICAR, RETRO]


def test_corrige_retro_equivocada_editandola():
    cliente = ClienteFalso()
    resultado = _subir(
        cliente, [RetroNexus(40458364, "Dejaste las respuestas vacías.")], "Están en celdas nuevas."
    )
    assert resultado.accion.tipo is TipoAccion.EDITAR
    campos = cliente.enviados[1][1]
    assert (campos["RetroalimentacionId"], campos["Estudiantes"]) == ("40458364", "748333")


def test_retro_igual_solo_sube_calificacion():
    cliente = ClienteFalso()
    _subir(cliente, [RetroNexus(10, "Completa.")], "Completa.")
    assert cliente.rutas == [CALIFICAR]


def test_varias_retros_no_sube_nada_y_las_muestra():
    cliente = ClienteFalso()
    existentes = [RetroNexus(25, "xchjvbkn"), RetroNexus(10, "Buena.")]
    with pytest.raises(VariasRetroalimentaciones) as e:
        _subir(cliente, existentes, "final")
    assert e.value.existentes == (RetroNexus(10, "Buena."), RetroNexus(25, "xchjvbkn"))
    assert cliente.enviados == []


def test_docente_borra_la_que_eligio_y_luego_se_sube():
    cliente = ClienteFalso()
    existentes = [RetroNexus(10, "Buena."), RetroNexus(25, "xchjvbkn")]
    borrar_retro_elegida(EscrituraNexusApi(cliente), 747689, DIMENSION, existentes, 25)
    assert cliente.enviados[-1] == (
        "Retroalimentacion/EliminarRetroalimentacion",
        {"CursoId": 747689, "TipoElementoId": 1, "ElementoId": 4560461, "RetroalimentacionId": 25},
    )
    _subir(cliente, [RetroNexus(10, "Buena.")], "Buena.")
    assert cliente.rutas[-1] == CALIFICAR


def test_no_borra_retro_de_otro_alumno():
    cliente = ClienteFalso()
    with pytest.raises(ValueError):
        borrar_retro_elegida(EscrituraNexusApi(cliente), 747689, DIMENSION, [RetroNexus(10, "a")], 99)
    assert cliente.enviados == []
