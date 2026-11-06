"""Qué hacer con la retroalimentación de un alumno en NEXUS para que quede la que el docente validó.

NEXUS permite varias retroalimentaciones por alumno y elemento. La app mantiene una sola, la validada:
- si no hay ninguna, se agrega;
- si hay una distinta, se edita en su lugar (el alumno no ve duplicados);
- si ya es igual, no se hace nada;
- si hay varias, se conserva la que ya coincide (o se edita la más reciente) y las demás se eliminan
  solo si el docente pide consolidar.
Eliminar sin reemplazo es siempre una acción explícita del docente.
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
    ELIMINAR = "eliminar"


@dataclass(frozen=True, slots=True)
class AccionRetro:
    tipo: TipoAccion
    texto: str = ""
    retro_id: int = 0  # 0 al agregar


@dataclass(frozen=True, slots=True)
class PlanRetro:
    acciones: tuple[AccionRetro, ...]
    advertencias: tuple[str, ...] = ()

    @property
    def sin_cambios(self) -> bool:
        return not self.acciones


def mismo_texto(a: str, b: str) -> bool:
    return _ESPACIOS.sub(" ", a).strip() == _ESPACIOS.sub(" ", b).strip()


def planear_retro(existentes: Sequence[RetroNexus], deseada: str, *, consolidar: bool = False) -> PlanRetro:
    """Acciones para que en NEXUS quede `deseada` como retroalimentación del alumno."""
    if not deseada.strip():
        raise ValueError("La retroalimentación validada está vacía; para borrar usa eliminar_retro.")
    if not existentes:
        return PlanRetro((AccionRetro(TipoAccion.AGREGAR, deseada),))
    recientes = sorted(existentes, key=lambda r: r.id, reverse=True)
    # Se conserva la que ya dice lo validado; si ninguna, la más reciente
    principal = next((r for r in recientes if mismo_texto(r.texto, deseada)), recientes[0])
    otras = [r for r in recientes if r.id != principal.id]
    acciones: list[AccionRetro] = []
    if not mismo_texto(principal.texto, deseada):
        acciones.append(AccionRetro(TipoAccion.EDITAR, deseada, principal.id))
    advertencias: list[str] = []
    if otras and consolidar:
        acciones += [AccionRetro(TipoAccion.ELIMINAR, retro_id=r.id) for r in otras]
    elif otras:
        advertencias.append(
            f"El alumno tiene {len(otras)} retroalimentación(es) anterior(es) además de la editada."
        )
    return PlanRetro(tuple(acciones), tuple(advertencias))


def eliminar_retro(existentes: Sequence[RetroNexus], retro_id: int) -> PlanRetro:
    """Borrado explícito de una retroalimentación (por ejemplo, una de prueba o equivocada)."""
    if retro_id not in {r.id for r in existentes}:
        raise ValueError(f"La retroalimentación {retro_id} no pertenece a este alumno y elemento.")
    return PlanRetro((AccionRetro(TipoAccion.ELIMINAR, retro_id=retro_id),))
