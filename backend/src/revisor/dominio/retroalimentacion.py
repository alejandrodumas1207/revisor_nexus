"""Qué hacer con la retroalimentación de un alumno en NEXUS para que quede la versión final validada.

Cada alumno tiene una sola retroalimentación por elemento:
- si no hay, se agrega;
- si hay una distinta (incluida una de prueba), se edita en su lugar;
- si ya dice lo mismo, no se toca.
La app nunca borra por su cuenta. Si NEXUS trae más de una, se detiene, muestra todas al docente
y este elige cuál borrar; después se sigue con la regla de una sola.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

_ESPACIOS = re.compile(r"\s+")


@dataclass(frozen=True, slots=True)
class RetroNexus:
    id: int
    texto: str


class TipoAccion(StrEnum):
    AGREGAR = "agregar"
    EDITAR = "editar"
    NINGUNA = "ninguna"


@dataclass(frozen=True, slots=True)
class AccionRetro:
    tipo: TipoAccion
    texto: str = ""
    retro_id: int = 0  # 0 al agregar


class VariasRetroalimentaciones(ValueError):
    """El alumno tiene más de una retroalimentación en NEXUS; el docente elige cuál borrar."""

    def __init__(self, existentes: Sequence[RetroNexus]) -> None:
        self.existentes = tuple(sorted(existentes, key=lambda r: r.id))
        super().__init__(f"Hay {len(existentes)} retroalimentaciones; elige cuál borrar.")


def validar_borrado(existentes: Sequence[RetroNexus], retro_id: int) -> None:
    """Solo se borra una retroalimentación que el docente eligió de la lista del propio alumno."""
    if retro_id not in {r.id for r in existentes}:
        raise ValueError(f"La retroalimentación {retro_id} no pertenece a este alumno y elemento.")


def mismo_texto(a: str, b: str) -> bool:
    return _ESPACIOS.sub(" ", a).strip() == _ESPACIOS.sub(" ", b).strip()


def planear_retro(existentes: Sequence[RetroNexus], final: str) -> AccionRetro:
    """Acción para que en NEXUS quede `final` como la única retroalimentación del alumno."""
    if not final.strip():
        raise ValueError("La retroalimentación final está vacía.")
    if len(existentes) > 1:
        raise VariasRetroalimentaciones(existentes)
    if not existentes:
        return AccionRetro(TipoAccion.AGREGAR, final)
    actual = existentes[0]
    if mismo_texto(actual.texto, final):
        return AccionRetro(TipoAccion.NINGUNA, final, actual.id)
    return AccionRetro(TipoAccion.EDITAR, final, actual.id)
