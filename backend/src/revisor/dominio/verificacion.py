"""Verificaciones que hace el código antes de la IA: son exactas, gratis y no se equivocan.

- Cifras citadas que no aparecen en las salidas del propio notebook (aceptando redondeo y porcentajes).
- Entregas sin trabajo (respuestas vacías y nada ejecutado), que no necesitan revisión con IA.
"""

import re
from collections.abc import Iterable, Mapping

_CIFRA = re.compile(r"(?<![\w.])(\d{1,3}(?:,\d{3})+|\d+\.\d+)(\s*%)?|(?<![\w.])(\d+)(\s*%)")
_VALOR = re.compile(r"-?\d+(?:,\d{3})*(?:\.\d+)?(?:e-?\d+)?")


def cifras_citadas(texto: str) -> list[str]:
    """Decimales, miles con coma y porcentajes. Los enteros sueltos se ignoran (suelen ser preguntas)."""
    citadas: list[str] = []
    for m in _CIFRA.finditer(texto):
        numero, pct = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
        citadas.append(numero + ("%" if pct else ""))
    return list(dict.fromkeys(citadas))


def valores_en(texto: str) -> list[float]:
    valores: list[float] = []
    for m in _VALOR.finditer(texto):
        try:
            valores.append(float(m.group(0).replace(",", "")))
        except ValueError:
            continue
    return valores


def _decimales(cifra: str) -> int:
    parte = cifra.rstrip("%").split(".")
    return len(parte[1]) if len(parte) == 2 else 0


def aparece(cifra: str, valores: Iterable[float]) -> bool:
    """True si la cifra coincide con un valor redondeado a los decimales citados, directo o en porcentaje."""
    numero = float(cifra.rstrip("%").replace(",", ""))
    tolerancia = 0.5 * 10 ** (-_decimales(cifra)) + 1e-9
    return any(abs(v - numero) <= tolerancia or abs(v * 100 - numero) <= tolerancia for v in valores)


def cifras_no_encontradas(respuestas: Mapping[str, str], salidas: str) -> dict[str, list[str]]:
    """Por respuesta, las cifras citadas que no salen de las salidas del notebook."""
    valores = valores_en(salidas)
    faltantes = {i: [c for c in cifras_citadas(t) if not aparece(c, valores)] for i, t in respuestas.items()}
    return {i: c for i, c in faltantes.items() if c}


def sin_trabajo(respuestas: Mapping[str, str], celdas_con_salida: int) -> bool:
    """Ninguna celda con salidas y ninguna respuesta escrita: no hay nada que revisar con IA.

    No se usa el número de ejecución: Colab a veces guarda notebooks ejecutados sin él.
    """
    return celdas_con_salida == 0 and all(not t.strip() for t in respuestas.values())
