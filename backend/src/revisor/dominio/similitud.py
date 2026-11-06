"""Similitud entre entregas para detectar posibles copias. Solo señala: nunca califica."""

import itertools
import re
from collections.abc import Mapping
from dataclasses import dataclass

_PALABRA = re.compile(r"\w+", re.UNICODE)
_COMENTARIO = re.compile(r"#.*$", re.MULTILINE)


@dataclass(frozen=True, slots=True)
class ParSimilar:
    a: str
    b: str
    similitud: float  # 0 a 1 (Jaccard de n-gramas)


def normalizar_texto(texto: str) -> list[str]:
    return _PALABRA.findall(texto.lower())


def normalizar_codigo(codigo: str) -> list[str]:
    """Quita comentarios y espacios para que cambiar solo el formato no oculte una copia."""
    return _PALABRA.findall(_COMENTARIO.sub("", codigo).lower())


def ngramas(tokens: list[str], n: int) -> set[tuple[str, ...]]:
    if len(tokens) < n:
        return {tuple(tokens)} if tokens else set()
    return {tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1)}


def jaccard(a: set[tuple[str, ...]], b: set[tuple[str, ...]]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def pares_similares(tokens: Mapping[str, list[str]], umbral: float, n: int = 5) -> list[ParSimilar]:
    """Pares cuya similitud supera el umbral, del más parecido al menos parecido."""
    conjuntos = {k: ngramas(v, n) for k, v in tokens.items()}
    pares = [
        ParSimilar(a, b, s)
        for a, b in itertools.combinations(sorted(conjuntos), 2)
        if (s := jaccard(conjuntos[a], conjuntos[b])) >= umbral
    ]
    return sorted(pares, key=lambda p: p.similitud, reverse=True)
