"""Ajustes a la calificación del instrumento por formato, entrega tardía y copia (ADR 0005).

Orden: instrumento → formato → tardanza → copia → ajuste a calificación válida de NEXUS.
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


class Tardanza(StrEnum):
    A_TIEMPO = "a tiempo"
    CONFIRMADA = "tardía confirmada"  # marca Extemporanea de NEXUS o fecha posterior al límite vigente
    DUDOSA = "dudosa"  # no se penaliza; se señala al docente


@dataclass(frozen=True, slots=True)
class ReglasIntegridad:
    factor_copia: float = 0.5  # copia confirmada: la calificación se divide a la mitad
    puntos_formato: float = 1.0  # tipo de archivo incorrecto: descuento simbólico que se nota en NEXUS
    puntos_tardia: float = 1.0  # solo con tardanza confirmada


def calificacion_final(
    valor: float,
    validas: Sequence[int],
    *,
    formato_incorrecto: bool = False,
    tardanza: Tardanza = Tardanza.A_TIEMPO,
    copia: VeredictoCopia = VeredictoCopia.NINGUNA,
    reglas: ReglasIntegridad | None = None,
    politica: PoliticaAjuste = POLITICA_POR_DEFECTO,
) -> int:
    """Aplica formato, tardanza y copia a la calificación del instrumento y la lleva a una válida de NEXUS."""
    reglas = reglas or ReglasIntegridad()
    if formato_incorrecto:
        valor = max(0.0, valor - reglas.puntos_formato)
    if tardanza is Tardanza.CONFIRMADA:
        valor = max(0.0, valor - reglas.puntos_tardia)
    if copia is VeredictoCopia.CONFIRMADA:
        valor *= reglas.factor_copia
    return ajustar_a_valida(valor, validas, politica)
