"""Cambia nombre y matrícula por un identificador antes de enviar texto a un proveedor externo (ADR 0002)."""

import re
import unicodedata
from collections.abc import Iterable

_MATRICULA = re.compile(r"(?<!\d)\d{7}(?!\d)")
_LONGITUD_MINIMA = 3  # no se reemplazan partículas cortas como "de" o "la"
# Bordes de palabra en los que el guion bajo también separa (E2_D3_Tamez_Garcia)
_BORDE_INICIO = r"(?<![^\W_])"
_BORDE_FIN = r"(?![^\W_])"


def _sin_acentos(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


def seudonimizar(texto: str, nombres: Iterable[str], alias: str = "ALUMNO") -> str:
    """Reemplaza las palabras de los nombres (con o sin acentos) y toda matrícula de 7 dígitos."""
    resultado = _MATRICULA.sub("[MATRICULA]", texto)
    palabras = {p for nombre in nombres for p in re.split(r"[\s_]+", nombre) if len(p) >= _LONGITUD_MINIMA}
    for palabra in sorted(palabras, key=len, reverse=True):
        variantes = "|".join({re.escape(palabra), re.escape(_sin_acentos(palabra))})
        patron = re.compile(f"{_BORDE_INICIO}(?:{variantes}){_BORDE_FIN}", re.IGNORECASE)
        resultado = patron.sub(alias, resultado)
    return resultado
