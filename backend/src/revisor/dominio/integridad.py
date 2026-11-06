"""Ajustes a la calificación del instrumento por copia y por entrega tardía (ADR 0005).

Orden: instrumento → penalización tardía → sanción por copia → ajuste a calificación válida de NEXUS.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from revisor.dominio.calificacion import POLITICA_POR_DEFECTO, PoliticaAjuste, ajustar_a_valida


class VeredictoCopia(StrEnum):
    CONFIRMADA = "copia confirmada"
    PROBABLE = "probable"  # se señala al docente, no se sanciona
    PLANTILLA = "coincidencia por plantilla"
    NINGUNA = "ninguna"


@dataclass(frozen=True, slots=True)
class ReglasIntegridad:
    factor_copia: float = 0.5  # copia confirmada: la calificación se divide a la mitad
    puntos_tardia: float = 0.0  # se restan de 0-10; en 0 mientras no se defina la penalización


def calificacion_final(
    valor: float,
    validas: Sequence[int],
    *,
    tardia: bool = False,
    copia: VeredictoCopia = VeredictoCopia.NINGUNA,
    reglas: ReglasIntegridad | None = None,
    politica: PoliticaAjuste = POLITICA_POR_DEFECTO,
) -> int:
    """Aplica tardanza y copia a la calificación del instrumento y la lleva a una válida de NEXUS."""
    reglas = reglas or ReglasIntegridad()
    if tardia:
        valor = max(0.0, valor - reglas.puntos_tardia)
    if copia is VeredictoCopia.CONFIRMADA:
        valor *= reglas.factor_copia
    return ajustar_a_valida(valor, validas, politica)
