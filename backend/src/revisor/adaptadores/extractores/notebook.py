"""Extrae de un notebook las respuestas escritas, el código del alumno y el resultado de ejecutarlo.

Reconoce las marcas de las dos plantillas del curso.
Plantilla A (Etapa 1):
- `### RESPUESTA E1D3-06` y la línea `--- ESCRIBE TU RESPUESTA DEBAJO DE ESTA LINEA ---`
- `# INICIO E1D3-04 · CODIGO DEL ALUMNO` ... `# FIN E1D3-04`
- la línea `RESUMEN|...` que imprime la celda de verificación
Plantilla B (Etapa 2):
- encabezados `## Pregunta - 7`, que dan el identificador P07 a lo que sigue
- `++++ Inicia la seccion ... ++++` ... `++++ Termina la seccion ... ++++` en celdas de texto o de código
"""

import json
import re
from dataclasses import dataclass, field
from typing import Any

_RESPUESTA = re.compile(r"^#+\s*RESPUESTA\s+(E\d+D\d+-\d+)", re.MULTILINE)
_BLOQUE = re.compile(r"INICIO\s+(E\d+D\d+-\d+)[^\n]*\n(.*?)(?:#\s*FIN\s+\1|\Z)", re.DOTALL)
_SEPARADOR = re.compile(r"-{3}\s*ESCRIBE TU RESPUESTA DEBAJO DE ESTA L[IÍ]NEA\s*-{3}", re.IGNORECASE)
_MATRICULA = re.compile(r"""^\s*MATRICULA\s*=\s*["']([^"']*)["']""", re.MULTILINE)
_NOMBRE = re.compile(r"""^\s*NOMBRE\s*=\s*["']([^"']*)["']""", re.MULTILINE)
_RESUMEN = re.compile(r"^RESUMEN\|(.*)$", re.MULTILINE)
_VERIFICACION = re.compile(r"^\[(OK|FALTA|ERROR|NO)[^\]]*\]\s*(.+)$", re.MULTILINE | re.IGNORECASE)
_PREGUNTA_B = re.compile(r"^#+\s*Pregunta\s*-\s*(\d+)", re.MULTILINE | re.IGNORECASE)
_SECCION_B = re.compile(
    r"\+{4}\s*Inicia la secci[oó]n[^+]*\+{4}(.*?)(?:\+{4}\s*Termina la secci[oó]n[^+]*\+{4}|\Z)",
    re.DOTALL | re.IGNORECASE,
)
_LIMITE_SALIDA = 600


class NotebookInvalido(ValueError):
    """El archivo no es un notebook que se pueda leer."""


@dataclass(frozen=True, slots=True)
class BloqueCodigo:
    id: str
    codigo: str
    ejecutado: bool
    error: str | None
    imagenes: int
    salida: str


@dataclass(frozen=True, slots=True)
class ReporteNotebook:
    matricula: str
    nombre: str
    respuestas: dict[str, str]
    bloques: dict[str, BloqueCodigo]
    celdas_codigo: int
    celdas_sin_ejecutar: int
    errores: tuple[str, ...]
    verificacion: tuple[tuple[bool, str], ...]
    resumen: dict[str, str] = field(default_factory=dict[str, str])

    @property
    def respuestas_vacias(self) -> list[str]:
        return [i for i, t in self.respuestas.items() if not t.strip()]


def leer_notebook(contenido: bytes) -> ReporteNotebook:
    """Lee un .ipynb (o un .txt que contiene el JSON del notebook)."""
    try:
        datos = json.loads(contenido.decode("utf-8-sig"))
        celdas: list[dict[str, Any]] = datos["cells"]
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError) as e:
        raise NotebookInvalido("No es un notebook de Jupyter válido.") from e
    codigo = [c for c in celdas if c.get("cell_type") == "code"]
    texto_codigo = "\n".join(_texto(c.get("source")) for c in codigo)
    salidas = "\n".join(_salida_texto(c) for c in codigo)
    respuestas_b, bloques_b = _plantilla_b(celdas)
    return ReporteNotebook(
        matricula=_primero(_MATRICULA, texto_codigo),
        nombre=_primero(_NOMBRE, texto_codigo),
        respuestas=_respuestas(celdas) | respuestas_b,
        bloques=_bloques(codigo) | bloques_b,
        celdas_codigo=len(codigo),
        celdas_sin_ejecutar=sum(
            1 for c in codigo if c.get("execution_count") is None and _texto(c.get("source")).strip()
        ),
        errores=tuple(e for c in codigo if (e := _error(c))),
        verificacion=tuple(
            (m.group(1).upper() == "OK", m.group(2).strip()) for m in _VERIFICACION.finditer(salidas)
        ),
        resumen=_resumen(salidas),
    )


def _texto(fuente: object) -> str:
    if isinstance(fuente, list):
        return "".join(str(x) for x in fuente)  # pyright: ignore[reportUnknownVariableType]
    return str(fuente or "")


def _primero(patron: re.Pattern[str], texto: str) -> str:
    m = patron.search(texto)
    return m.group(1).strip() if m else ""


def _respuestas(celdas: list[dict[str, Any]]) -> dict[str, str]:
    respuestas: dict[str, str] = {}
    for c in celdas:
        if c.get("cell_type") != "markdown":
            continue
        fuente = _texto(c.get("source"))
        m = _RESPUESTA.search(fuente)
        if not m:
            continue
        partes = _SEPARADOR.split(fuente, maxsplit=1)
        respuestas[m.group(1)] = partes[1].strip() if len(partes) == 2 else ""
    return respuestas


def _bloques(codigo: list[dict[str, Any]]) -> dict[str, BloqueCodigo]:
    bloques: dict[str, BloqueCodigo] = {}
    for c in codigo:
        fuente = _texto(c.get("source"))
        for m in _BLOQUE.finditer(fuente):
            bloques[m.group(1)] = _bloque_de_celda(m.group(1), _sin_comentarios_de_plantilla(m.group(2)), c)
    return bloques


def _plantilla_b(celdas: list[dict[str, Any]]) -> tuple[dict[str, str], dict[str, BloqueCodigo]]:
    """Secciones `++++ Inicia ... ++++` asignadas a la última `Pregunta - N` vista."""
    respuestas: dict[str, str] = {}
    bloques: dict[str, BloqueCodigo] = {}
    actual = ""
    for c in celdas:
        fuente = _texto(c.get("source"))
        if (m := _PREGUNTA_B.search(fuente)) and c.get("cell_type") == "markdown":
            actual = f"P{int(m.group(1)):02d}"
        secciones = [s.strip() for s in _SECCION_B.findall(fuente)]
        if not secciones or not actual:
            continue
        contenido = "\n".join(secciones)
        if c.get("cell_type") == "markdown":
            respuestas[actual] = (respuestas.get(actual, "") + "\n" + contenido).strip()
        else:
            bloques[actual] = _bloque_de_celda(actual, contenido, c)
    return respuestas, bloques


def _bloque_de_celda(id_: str, codigo: str, celda: dict[str, Any]) -> BloqueCodigo:
    salidas: list[dict[str, Any]] = celda.get("outputs") or []
    return BloqueCodigo(
        id=id_,
        codigo=codigo,
        ejecutado=celda.get("execution_count") is not None,
        error=_error(celda),
        imagenes=sum(1 for s in salidas if "image/png" in (s.get("data") or {})),
        salida=_salida_texto(celda)[:_LIMITE_SALIDA],
    )


def _sin_comentarios_de_plantilla(codigo: str) -> str:
    lineas = [ln for ln in codigo.splitlines() if not ln.strip().startswith("# ====")]
    return "\n".join(lineas).strip()


def _salida_texto(celda: dict[str, Any]) -> str:
    partes: list[str] = []
    for s in celda.get("outputs") or []:
        if s.get("output_type") == "stream":
            partes.append(_texto(s.get("text")))
        elif "text/plain" in (s.get("data") or {}):
            partes.append(_texto(s["data"]["text/plain"]))
    return "".join(partes)


def _error(celda: dict[str, Any]) -> str | None:
    for s in celda.get("outputs") or []:
        if s.get("output_type") == "error":
            return f"{s.get('ename', 'Error')}: {s.get('evalue', '')}"[:300]
    return None


def _resumen(salidas: str) -> dict[str, str]:
    encontrados = list(_RESUMEN.finditer(salidas))
    if not encontrados:
        return {}
    m = encontrados[-1]  # la verificación más reciente
    campos = m.group(1).split("|")
    resumen = {"actividad": campos[0]} if campos else {}
    if len(campos) > 1:
        resumen["matricula"] = campos[1]
    for campo in campos[2:]:
        clave, _, valor = campo.partition("=")
        resumen[clave.strip()] = valor.strip()
    return resumen
