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


@dataclass(frozen=True, slots=True)
class ValorCompartido:
    valor: str
    alumnos: tuple[str, ...]

    @property
    def es_evidencia(self) -> bool:
        """Solo un valor compartido por pocos alumnos es indicio; si lo eligieron muchos, es opción común."""
        return len(self.alumnos) <= MAXIMO_RARO


MAXIMO_RARO = 2  # con 3 o más alumnos eligiendo lo mismo, la actividad lo está guiando


def valores_compartidos(decisiones: Mapping[str, str]) -> list[ValorCompartido]:
    """Agrupa una decisión libre (valor elegido por cada alumno) y dice qué tan común es cada valor.

    Los resultados obtenidos con semilla fija no se pasan aquí: con las mismas decisiones salen idénticos.
    """
    grupos: dict[str, list[str]] = {}
    for alumno, valor in decisiones.items():
        if valor.strip():
            grupos.setdefault(valor.strip(), []).append(alumno)
    return sorted(
        (ValorCompartido(v, tuple(sorted(a))) for v, a in grupos.items() if len(a) > 1),
        key=lambda g: len(g.alumnos),
    )
