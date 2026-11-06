"""Qué calificaciones puede registrar NEXUS y cómo marcar la rúbrica para lograrlas.

Portado de nexus_tools/nexus_lib/maestro.py (calificaciones_validas, combinacion_rubrica).
"""

import itertools
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

_TOLERANCIA = 1e-9


class PoliticaAjuste(StrEnum):
    """Qué hacer cuando la calificación del instrumento no se puede registrar en NEXUS."""

    ARRIBA = "arriba"
    ABAJO = "abajo"
    CERCANA = "cercana"  # en empate sube


POLITICA_POR_DEFECTO = PoliticaAjuste.ARRIBA  # decisión del docente: no perjudicar al alumno


def ajustar_a_valida(
    valor: float, validas: Sequence[int], politica: PoliticaAjuste = POLITICA_POR_DEFECTO
) -> int:
    """Lleva una calificación de 0 a 10 a una que NEXUS pueda registrar."""
    if not validas:
        raise ValueError("No hay calificaciones válidas.")
    if politica is PoliticaAjuste.ARRIBA:
        mayores = [v for v in validas if v + _TOLERANCIA >= valor]
        return min(mayores) if mayores else max(validas)
    if politica is PoliticaAjuste.ABAJO:
        menores = [v for v in validas if v - _TOLERANCIA <= valor]
        return max(menores) if menores else min(validas)
    return min(validas, key=lambda v: (abs(v - valor), -v))


@dataclass(frozen=True, slots=True)
class CombinacionRubrica:
    niveles: tuple[int, ...]  # índice del nivel marcado en cada criterio, ordenado
    promedio: float  # porcentaje que registra NEXUS (0-100)


def calificaciones_validas(criterios: int | None, niveles: Sequence[float]) -> list[int]:
    """Calificaciones enteras de 0 a 10 que NEXUS registra exactamente, de mayor a menor.

    Sin rúbrica (criterios None o 0) cualquier entero de 0 a 10 es válido.
    """
    if not criterios or not niveles:
        return list(range(10, -1, -1))
    validas: set[int] = set()
    for combo in itertools.combinations_with_replacement(niveles, criterios):
        decimas = sum(combo) / criterios / 10
        if abs(decimas - round(decimas)) < _TOLERANCIA:
            validas.add(round(decimas))
    return sorted(validas, reverse=True)


def combinacion_rubrica(cal10: int, criterios: int, niveles: Sequence[float]) -> CombinacionRubrica | None:
    """Niveles a marcar para registrar la calificación pedida.

    Si no es exacta, sube a la siguiente posible. Devuelve None si ninguna la alcanza.
    """
    if criterios <= 0 or not niveles:
        raise ValueError("Se necesita al menos un criterio y un nivel.")
    objetivo = cal10 * 10
    mejor: CombinacionRubrica | None = None
    for combo in itertools.product(range(len(niveles)), repeat=criterios):
        promedio = sum(niveles[i] for i in combo) / criterios
        if promedio + _TOLERANCIA >= objetivo and (mejor is None or promedio < mejor.promedio):
            mejor = CombinacionRubrica(tuple(sorted(combo)), promedio)
    return mejor
