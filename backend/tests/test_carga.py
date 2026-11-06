from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from revisor.adaptadores.nexus_api.escritura import ErrorNexus, EscrituraNexusApi
from revisor.dominio.modelos import CalificacionNexus, Elemento, NivelRubricaNexus, TipoElemento
from revisor.dominio.retroalimentacion import RetroNexus, TipoAccion
from revisor.servicios.carga import subir_revision

DIMENSION = Elemento("1.2", 4560461, TipoElemento.EVIDENCIA, "Dimensión 2", 2.5, False, None, None, None)
EVIDENCIA = Elemento("1.4", 4560463, TipoElemento.EVIDENCIA, "Evidencia", 5, True, 3, None, None)
NIVELES = (NivelRubricaNexus(1909378, 9193517, 7542588, 33971437),)


class ClienteFalso:
    """Registra lo que se enviaría a NEXUS y contesta como lo hace NEXUS."""

    def __init__(self, error: bool = False) -> None:
        self.enviados: list[tuple[str, Mapping[str, Any]]] = []
        self.error = error
        self.siguiente_id = 500

    def post_json(self, ruta: str, cuerpo: Mapping[str, Any]) -> dict[str, Any]:
        self.enviados.append((ruta, cuerpo))
        if self.error:
            return {"Code": 2011, "Message": "La sesión no existe."}
        if ruta.endswith("ActualizarCalificacionesElementoEvaluable"):
            return {"Calificaiones": [{"CuentaId": e["CuentaId"]} for e in cuerpo["Estudiantes"]]}
        return {"RetroalimentacionEliminada": True}

    def post_form(self, ruta: str, campos: Mapping[str, str]) -> dict[str, Any]:
        self.enviados.append((ruta, campos))
        nuevo = int(campos["RetroalimentacionId"]) or self.siguiente_id
        return {"Retroalimentacion": {"RetroalimentacionId": nuevo}}


def test_calificacion_sin_rubrica_va_en_escala_100():
    cliente = ClienteFalso()
    EscrituraNexusApi(cliente).guardar_calificaciones(747689, DIMENSION, [CalificacionNexus(748333, 90)])
    ruta, cuerpo = cliente.enviados[0]
    assert ruta == "Portafolio/ActualizarCalificacionesElementoEvaluable"
    assert cuerpo["UsaRubrica"] is False
    assert cuerpo["Estudiantes"][0]["Calificacion"]["Valor"] == "90"


def test_calificacion_con_rubrica_envia_niveles():
    cliente = ClienteFalso()
    EscrituraNexusApi(cliente).guardar_calificaciones(
        747689, EVIDENCIA, [CalificacionNexus(748333, 100, NIVELES)]
    )
    estudiante = cliente.enviados[0][1]["Estudiantes"][0]
    assert estudiante["Rubrica"][0]["CriterioNivelDominioId"] == 33971437


def test_rubrica_sin_niveles_no_se_envia():
    cliente = ClienteFalso()
    with pytest.raises(ValueError):
        EscrituraNexusApi(cliente).guardar_calificaciones(747689, EVIDENCIA, [CalificacionNexus(748333, 100)])
    assert cliente.enviados == []


def test_sesion_vencida_es_error():
    with pytest.raises(ErrorNexus, match="La sesión no existe"):
        EscrituraNexusApi(ClienteFalso(error=True)).eliminar_retro(747689, DIMENSION, 1)


def test_corrige_retro_equivocada_editandola():
    cliente = ClienteFalso()
    existentes = [RetroNexus(40458364, "Dejaste las cinco respuestas vacías.")]
    resultado = subir_revision(
        EscrituraNexusApi(cliente),
        747689,
        DIMENSION,
        CalificacionNexus(748333, 80),
        existentes,
        "Tus respuestas están en celdas nuevas debajo de cada pregunta.",
    )
    assert resultado.plan.acciones[0].tipo is TipoAccion.EDITAR
    assert resultado.retro_id == 40458364
    campos = cliente.enviados[1][1]
    assert campos["RetroalimentacionId"] == "40458364"
    assert campos["Estudiantes"] == "748333"


def test_agrega_retro_cuando_no_hay():
    cliente = ClienteFalso()
    resultado = subir_revision(
        EscrituraNexusApi(cliente), 747689, DIMENSION, CalificacionNexus(748333, 100), [], "Completa."
    )
    assert resultado.retro_id == 500


def test_consolidar_elimina_retro_de_prueba():
    cliente = ClienteFalso()
    existentes: Sequence[RetroNexus] = [RetroNexus(40458364, "Buena."), RetroNexus(40832413, "xchjvbkn")]
    subir_revision(
        EscrituraNexusApi(cliente),
        747689,
        DIMENSION,
        CalificacionNexus(748333, 100),
        existentes,
        "Buena.",
        consolidar=True,
    )
    rutas = [r for r, _ in cliente.enviados]
    # "Buena." ya existe: se conserva y solo se elimina la de prueba
    assert rutas == [
        "Portafolio/ActualizarCalificacionesElementoEvaluable",
        "Retroalimentacion/EliminarRetroalimentacion",
    ]
    assert cliente.enviados[1][1]["RetroalimentacionId"] == 40832413
