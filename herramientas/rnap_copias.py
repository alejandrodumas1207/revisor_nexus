"""Documento para revisar una por una las copias y sospechas de RNAP E1-E2.

Por cada par: veredicto, explicación y, en cada pregunta donde hay coincidencias, la respuesta completa
de los dos alumnos. Salida: datos_locales/rnap/copias_detalle.md (contiene datos de alumnos; no se versiona).
"""

import json
import re
from pathlib import Path
from typing import Any

from revisor.adaptadores.extractores.notebook import NotebookInvalido, ReporteNotebook, leer_notebook
from revisor.dominio.integridad import VeredictoCopia

CARPETA = Path(__file__).resolve().parent.parent / "datos_locales" / "rnap"
FORMULARIOS = Path.home() / "Desktop" / "RNAP_Revision_E1_E2" / "formularios"
DESTINO = CARPETA / "copias_detalle.md"
_ID_A = re.compile(r"E\d+D\d+-\d+")
_ID_B = re.compile(r"(?:\bP|E\dD\d-)(\d{1,2})\b")


def _reportes(actividad: str) -> dict[str, ReporteNotebook]:
    """Notebooks de la actividad, por matrícula escrita dentro del notebook o en el nombre del archivo."""
    patron = {"E1D3": "E1_D3*", "E1D4": "E1_D4*", "E2D3": "ETAPA 2_DIMENSI*3*", "E2D4": "ETAPA 2_DIMENSI*4*"}
    reportes: dict[str, ReporteNotebook] = {}
    for carpeta in FORMULARIOS.glob(patron[actividad]):
        for archivo in carpeta.rglob("*"):
            try:
                r = leer_notebook(archivo.read_bytes()) if archivo.is_file() else None
            except NotebookInvalido:
                continue
            if r:
                clave = r.matricula or (m.group(0) if (m := re.search(r"\d{7}", archivo.name)) else "")
                reportes.setdefault(clave, r)
    return reportes


def _preguntas(ubicacion: str, respuestas: dict[str, str]) -> list[str]:
    """Identificadores de respuesta mencionados en la ubicación de una coincidencia."""
    ids = [i for i in _ID_A.findall(ubicacion) if i in respuestas]
    if not ids:
        ids = [f"P{int(n):02d}" for n in _ID_B.findall(ubicacion) if f"P{int(n):02d}" in respuestas]
    return list(dict.fromkeys(ids))


def _cita(texto: str) -> str:
    return "\n".join(f"> {linea}" if linea.strip() else ">" for linea in (texto or "(vacía)").splitlines())


def _par(c: dict[str, Any], nombres: dict[str, str], reportes: dict[str, ReporteNotebook]) -> list[str]:
    a, b = c["a"], c["b"]
    lineas = [
        f"### {VeredictoCopia.desde_texto(c['veredicto']).value.capitalize()}: "
        f"{nombres.get(a, '')} ({a}) y {nombres.get(b, '')} ({b})",
        f"**Explicación:** {c.get('explicacion', '')}",
    ]
    ra, rb = reportes.get(a), reportes.get(b)
    vistas: set[str] = set()
    for x in c.get("coincidencias", []):
        lineas.append(f"**{x['ubicacion']}:** {x['detalle']}")
        respuestas = (ra.respuestas if ra else {}) | (rb.respuestas if rb else {})
        for pregunta in _preguntas(x["ubicacion"], respuestas):
            if pregunta in vistas:
                continue
            vistas.add(pregunta)
            for quien, r in ((a, ra), (b, rb)):
                lineas += [
                    f"*{pregunta} de {nombres.get(quien, quien)} ({quien}):*",
                    _cita(r.respuestas.get(pregunta, "") if r else ""),
                ]
    return lineas


def main() -> None:
    doc = ["# Copias y sospechas de RNAP E1-E2, para revisar una por una", ""]
    for archivo in sorted(CARPETA.glob("*_revision_v2.json")):
        rev = json.loads(archivo.read_text(encoding="utf-8"))
        pares = [
            c
            for c in rev.get("copias", [])
            if VeredictoCopia.desde_texto(c["veredicto"]) is not VeredictoCopia.NINGUNA
        ]
        if not pares:
            continue
        nombres = {x["matricula"]: (x.get("nombre") or "").strip() for x in rev["alumnos"]}
        reportes = _reportes(rev["actividad"])
        doc.append(f"## {rev['actividad']}")
        orden = {VeredictoCopia.CONFIRMADA: 0, VeredictoCopia.PARCIAL: 1, VeredictoCopia.SOSPECHA: 2}
        for c in sorted(pares, key=lambda c: orden.get(VeredictoCopia.desde_texto(c["veredicto"]), 3)):
            doc += [*_par(c, nombres, reportes), "", "---", ""]
    DESTINO.write_text("\n\n".join(doc), encoding="utf-8")
    print(f"-> {DESTINO}")


if __name__ == "__main__":
    main()
