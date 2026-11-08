"""Ajustes a la calificación del instrumento por formato, entrega tardía y copia (ADR 0005).

Orden: instrumento → formato → tardanza → copia → ajuste a calificación válida de NEXUS.
Cada paso queda registrado para explicarlo en la retroalimentación.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from revisor.dominio.calificacion import POLITICA_POR_DEFECTO, PoliticaAjuste, ajustar_a_valida


class VeredictoCopia(StrEnum):
    CONFIRMADA = "copia confirmada"  # copió todo o casi todo: × 0.5
    PARCIAL = "copia parcial"  # casi seguro que copió una parte, aunque parafraseada: × 0.75
    SOSPECHA = "sospecha"  # similitudes que pueden ser coincidencia: sin sanción, decide el docente
    NINGUNA = "ninguna"

    @classmethod
    def desde_texto(cls, texto: str | None) -> "VeredictoCopia":
        """Acepta también veredictos anteriores ("probable", "coincidencia por plantilla")."""
        anteriores = {"probable": cls.SOSPECHA, "coincidencia por plantilla": cls.NINGUNA, "": cls.NINGUNA}
        valor = (texto or "").strip().lower()
        return anteriores[valor] if valor in anteriores else cls(valor)


class Tardanza(StrEnum):
    A_TIEMPO = "a tiempo"
    CONFIRMADA = "tardía confirmada"  # marca Extemporanea de NEXUS o fecha posterior al límite vigente
    DUDOSA = "dudosa"  # no se penaliza; se señala al docente


@dataclass(frozen=True, slots=True)
class ReglasIntegridad:
    factor_copia: float = 0.5  # copia confirmada: la calificación se divide a la mitad
    factor_copia_parcial: float = 0.75  # copia parcial: se queda con tres cuartos
    puntos_formato: float = 1.0  # tipo de archivo incorrecto: penalización simbólica que se nota en NEXUS
    puntos_tardia: float = 1.0  # solo con tardanza confirmada


@dataclass(frozen=True, slots=True)
class PasoCalificacion:
    descripcion: str
    valor: float  # calificación (0-10) después del paso


@dataclass(frozen=True, slots=True)
class DetalleCalificacion:
    lista: float
    pasos: tuple[PasoCalificacion, ...]
    final: int


def detalle_calificacion(
    valor: float,
    validas: Sequence[int],
    *,
    formato_incorrecto: bool = False,
    tardanza: Tardanza = Tardanza.A_TIEMPO,
    copia: VeredictoCopia = VeredictoCopia.NINGUNA,
    reglas: ReglasIntegridad | None = None,
    politica: PoliticaAjuste = POLITICA_POR_DEFECTO,
) -> DetalleCalificacion:
    """Aplica formato, tardanza y copia y ajusta a una calificación válida de NEXUS, paso a paso."""
    reglas = reglas or ReglasIntegridad()
    pasos: list[PasoCalificacion] = []
    actual = valor
    if formato_incorrecto:
        actual = max(0.0, actual - reglas.puntos_formato)
        pasos.append(PasoCalificacion(f"Formato de archivo incorrecto: −{reglas.puntos_formato:g}", actual))
    if tardanza is Tardanza.CONFIRMADA:
        actual = max(0.0, actual - reglas.puntos_tardia)
        pasos.append(PasoCalificacion(f"Entrega tardía: −{reglas.puntos_tardia:g}", actual))
    factor = _factor_copia(copia, reglas)
    if factor < 1:
        actual *= factor
        pasos.append(PasoCalificacion(f"{copia.capitalize()}: × {factor:g}", actual))
    final = ajustar_a_valida(actual, validas, politica)
    if abs(final - actual) > 1e-9:
        pasos.append(PasoCalificacion("Ajuste a la calificación registrable en NEXUS", final))
    return DetalleCalificacion(valor, tuple(pasos), final)


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
    """Calificación que se registra en NEXUS (ver `detalle_calificacion`)."""
    return detalle_calificacion(
        valor,
        validas,
        formato_incorrecto=formato_incorrecto,
        tardanza=tardanza,
        copia=copia,
        reglas=reglas,
        politica=politica,
    ).final


def _factor_copia(copia: VeredictoCopia, reglas: ReglasIntegridad) -> float:
    if copia is VeredictoCopia.CONFIRMADA:
        return reglas.factor_copia
    if copia is VeredictoCopia.PARCIAL:
        return reglas.factor_copia_parcial
    return 1.0
