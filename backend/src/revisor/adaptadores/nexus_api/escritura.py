"""Escritura en NEXUS por API: calificaciones (con o sin rúbrica) y retroalimentaciones.

Formatos capturados el 2026-11-06; ver docs/nexus_api.md.
"""

from collections.abc import Mapping, Sequence
from typing import Any, Protocol

from revisor.dominio.modelos import CalificacionNexus, Elemento, TipoElemento

_TIPO_ELEMENTO = {TipoElemento.EVIDENCIA: 1, TipoElemento.PIA: 2}


class ErrorNexus(RuntimeError):
    """NEXUS respondió con un error en el cuerpo (siempre contesta HTTP 200)."""


class ClienteNexus(Protocol):
    """Envía peticiones con los encabezados de la sesión del docente."""

    def post_json(self, ruta: str, cuerpo: Mapping[str, Any]) -> dict[str, Any]: ...

    def post_form(self, ruta: str, campos: Mapping[str, str]) -> dict[str, Any]: ...


class EscrituraNexusApi:
    def __init__(self, cliente: ClienteNexus) -> None:
        self._cliente = cliente

    def guardar_calificaciones(
        self, curso_id: int, elemento: Elemento, calificaciones: Sequence[CalificacionNexus]
    ) -> None:
        cuerpo = {
            **_ids_elemento(curso_id, elemento),
            "UsaRubrica": elemento.usa_rubrica,
            "Estudiantes": [_estudiante(c, elemento.usa_rubrica) for c in calificaciones],
        }
        respuesta = _validar(
            self._cliente.post_json("Portafolio/ActualizarCalificacionesElementoEvaluable", cuerpo)
        )
        guardadas = {c["CuentaId"] for c in respuesta.get("Calificaiones", [])}  # sic en NEXUS
        faltantes = {c.cuenta_id for c in calificaciones} - guardadas
        if faltantes:
            raise ErrorNexus(f"NEXUS no confirmó la calificación de las cuentas {sorted(faltantes)}.")

    def guardar_retro(
        self, curso_id: int, elemento: Elemento, cuenta_id: int, texto: str, retro_id: int = 0
    ) -> int:
        campos = {
            "RetroalimentacionId": str(retro_id),
            "Descripcion": texto,
            "DerechoReplica": "false",
            "Estado": "true",
            **{k: str(v) for k, v in _ids_elemento(curso_id, elemento).items()},
            "Estudiantes": str(cuenta_id),
            "EquipoId": "0",
        }
        respuesta = _validar(self._cliente.post_form("Retroalimentacion/ActualizarRetroalimentacion", campos))
        try:
            return int(respuesta["Retroalimentacion"]["RetroalimentacionId"])
        except (KeyError, TypeError, ValueError) as e:
            raise ErrorNexus("NEXUS no confirmó la retroalimentación.") from e

    def eliminar_retro(self, curso_id: int, elemento: Elemento, retro_id: int) -> None:
        cuerpo = {**_ids_elemento(curso_id, elemento), "RetroalimentacionId": retro_id}
        respuesta = _validar(self._cliente.post_json("Retroalimentacion/EliminarRetroalimentacion", cuerpo))
        if respuesta.get("RetroalimentacionEliminada") is not True:
            raise ErrorNexus(f"NEXUS no confirmó la eliminación de la retroalimentación {retro_id}.")


def _ids_elemento(curso_id: int, elemento: Elemento) -> dict[str, int]:
    return {"CursoId": curso_id, "TipoElementoId": _TIPO_ELEMENTO[elemento.tipo], "ElementoId": elemento.id}


def _estudiante(c: CalificacionNexus, usa_rubrica: bool) -> dict[str, Any]:
    if usa_rubrica:
        if not c.rubrica:
            raise ValueError(f"El elemento usa rúbrica y la cuenta {c.cuenta_id} no trae niveles.")
        return {
            "CuentaId": c.cuenta_id,
            "Valor": c.valor,
            "Rubrica": [
                {
                    "RubricaId": n.rubrica_id,
                    "CriterioId": n.criterio_id,
                    "NivelDominioId": n.nivel_dominio_id,
                    "CriterioNivelDominioId": n.criterio_nivel_dominio_id,
                }
                for n in c.rubrica
            ],
        }
    # La web reenvía el objeto completo del alumno; estos son los campos que cambian (verificar en vivo)
    valor = str(c.valor)
    return {
        "CuentaId": c.cuenta_id,
        "Valor": valor,
        "Calificacion": {"Rubrica": [], "Calificado": False, "Valor": valor},
    }


def _validar(respuesta: dict[str, Any]) -> dict[str, Any]:
    if "Code" in respuesta and "Message" in respuesta:
        raise ErrorNexus(f"NEXUS respondió {respuesta['Code']}: {respuesta['Message']}")
    return respuesta
