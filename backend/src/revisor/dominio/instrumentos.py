"""Instrumentos de evaluación propios del docente. Cada uno produce una calificación de 0 a 10.

La rúbrica de NEXUS no interviene aquí (ADR 0004): solo limita qué calificaciones se pueden registrar.
"""

from collections.abc import Mapping, Set
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ItemCotejo:
    id: str
    descripcion: str
    puntos: float = 1.0


@dataclass(frozen=True, slots=True)
class ListaCotejo:
    nombre: str
    items: tuple[ItemCotejo, ...]
    version: int = 1

    def __post_init__(self) -> None:
        _validar_ids([i.id for i in self.items])
        if sum(i.puntos for i in self.items) <= 0:
            raise ValueError("La lista de cotejo necesita al menos un ítem con puntos.")

    def calificar(self, cumplidos: Set[str]) -> float:
        """Proporción de puntos cumplidos, en escala de 0 a 10."""
        desconocidos = cumplidos - {i.id for i in self.items}
        if desconocidos:
            raise ValueError(f"Ítems que no existen en la lista: {sorted(desconocidos)}")
        total = sum(i.puntos for i in self.items)
        logrado = sum(i.puntos for i in self.items if i.id in cumplidos)
        return logrado / total * 10


@dataclass(frozen=True, slots=True)
class NivelPropio:
    nombre: str
    porcentaje: float  # 0-100
    descriptor: str = ""


@dataclass(frozen=True, slots=True)
class CriterioPropio:
    id: str
    descripcion: str
    niveles: tuple[NivelPropio, ...]
    peso: float = 1.0


@dataclass(frozen=True, slots=True)
class RubricaPropia:
    nombre: str
    criterios: tuple[CriterioPropio, ...]
    version: int = 1

    def __post_init__(self) -> None:
        _validar_ids([c.id for c in self.criterios])
        if not self.criterios or any(not c.niveles for c in self.criterios):
            raise ValueError("Cada criterio de la rúbrica necesita al menos un nivel.")
        if sum(c.peso for c in self.criterios) <= 0:
            raise ValueError("La suma de pesos de la rúbrica debe ser positiva.")

    def calificar(self, elegidos: Mapping[str, int]) -> float:
        """Promedio ponderado de los niveles elegidos (índice por criterio), en escala de 0 a 10."""
        faltantes = {c.id for c in self.criterios} - set(elegidos)
        if faltantes:
            raise ValueError(f"Falta elegir nivel en: {sorted(faltantes)}")
        total = sum(c.peso for c in self.criterios)
        logrado = sum(c.peso * c.niveles[elegidos[c.id]].porcentaje for c in self.criterios)
        return logrado / total / 10


type Instrumento = ListaCotejo | RubricaPropia


def _validar_ids(ids: list[str]) -> None:
    if len(ids) != len(set(ids)):
        raise ValueError("Los identificadores del instrumento se repiten.")
