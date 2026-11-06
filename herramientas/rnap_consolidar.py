"""Junta las revisiones de RNAP E1-E2 en un Excel para que el docente las valide.

Lee datos_locales/rnap/*_revision.json y escribe datos_locales/rnap/RNAP_E1_E2_listas_cotejo.xlsx.
"""

import json
from pathlib import Path
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

CARPETA = Path(__file__).resolve().parent.parent / "datos_locales" / "rnap"
DESTINO = CARPETA / "RNAP_E1_E2_listas_cotejo.xlsx"
NEGRITA = Font(bold=True, color="FFFFFF")
ENCABEZADO = PatternFill("solid", fgColor="1F3A5F")
DIFERENCIA = PatternFill("solid", fgColor="FCE4D6")
NIVEL = {"cumple": "✓", "parcial": "½", "no_cumple": "✗"}


def _encabezado(ws: Worksheet, columnas: list[str], anchos: list[int]) -> None:
    ws.append(columnas)
    for i, ancho in enumerate(anchos, start=1):
        celda = ws.cell(row=1, column=i)
        celda.font, celda.fill = NEGRITA, ENCABEZADO
        ws.column_dimensions[get_column_letter(i)].width = ancho
    ws.freeze_panes = "A2"


def _ajustar(ws: Worksheet) -> None:
    for fila in ws.iter_rows(min_row=2):
        for celda in fila:
            celda.alignment = Alignment(wrap_text=True, vertical="top")


def _diferencia(a: Any, b: Any) -> int | None:
    return a - b if isinstance(a, int | float) and isinstance(b, int | float) else None


def _hoja_actividad(wb: Workbook, rev: dict[str, Any]) -> tuple[int, int]:
    ws = wb.create_sheet(rev["actividad"])
    ids = [c["id"] for c in rev["lista_cotejo"]]
    columnas = ["Matrícula", "Alumno", "Propuesta", "Excel/NEXUS", "Dif.", "Puntos", *ids]
    columnas += ["Retroalimentación propuesta", "Por qué difiere", "Alertas"]
    _encabezado(ws, columnas, [11, 28, 10, 11, 6, 8, *[5] * len(ids), 70, 45, 45])
    comparables = coinciden = 0
    for a in rev["alumnos"]:
        dif = _diferencia(a.get("calificacion"), a.get("calificacion_excel"))
        niveles = [NIVEL.get(a.get("niveles", {}).get(i, ""), "") for i in ids]
        ws.append(
            [
                a.get("matricula"),
                a.get("nombre"),
                a.get("calificacion"),
                a.get("calificacion_excel"),
                dif,
                a.get("puntos"),
                *niveles,
                a.get("retroalimentacion"),
                a.get("diferencia_explicada"),
                "\n".join(a.get("alertas") or []),
            ]
        )
        if dif is not None:
            comparables += 1
            coinciden += abs(dif) <= 1
            if abs(dif) >= 2:
                for celda in ws[ws.max_row]:
                    celda.fill = DIFERENCIA
    _ajustar(ws)
    return comparables, coinciden


def _hoja_listas(wb: Workbook, revisiones: list[dict[str, Any]]) -> None:
    ws = wb.create_sheet("Listas de cotejo")
    _encabezado(
        ws,
        ["Actividad", "Id", "Criterio", "Puntos", "Cumple", "Parcial", "No cumple"],
        [10, 5, 40, 8, 45, 45, 35],
    )
    for rev in revisiones:
        for c in rev["lista_cotejo"]:
            ws.append(
                [
                    rev["actividad"],
                    c["id"],
                    c["criterio"],
                    c["puntos"],
                    c["cumple"],
                    c.get("parcial"),
                    c["no_cumple"],
                ]
            )
    _ajustar(ws)


def _hoja_copias(wb: Workbook, revisiones: list[dict[str, Any]]) -> None:
    ws = wb.create_sheet("Copias")
    _encabezado(ws, ["Actividad", "Alumno A", "Alumno B", "Veredicto", "Evidencia"], [10, 11, 11, 24, 100])
    for rev in revisiones:
        orden = {"copia confirmada": 0, "probable": 1}
        for c in sorted(rev.get("copias", []), key=lambda c: orden.get(c["veredicto"], 2)):
            ws.append([rev["actividad"], c["a"], c["b"], c["veredicto"], c["evidencia"]])
    _ajustar(ws)


def main() -> None:
    revisiones = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(CARPETA.glob("*_revision.json"))]
    wb = Workbook()
    wb.remove(wb.worksheets[0])
    resumen = wb.create_sheet("Resumen")
    _encabezado(
        resumen,
        [
            "Actividad",
            "Alumnos",
            "Comparables",
            "Coinciden ±1",
            "Copias confirmadas",
            "Notas para el profesor",
        ],
        [10, 9, 12, 12, 12, 110],
    )
    for rev in revisiones:
        comparables, coinciden = _hoja_actividad(wb, rev)
        confirmadas = sum(1 for c in rev.get("copias", []) if c["veredicto"] == "copia confirmada")
        resumen.append(
            [
                rev["actividad"],
                len(rev["alumnos"]),
                comparables,
                coinciden,
                confirmadas,
                rev.get("notas_para_profesor"),
            ]
        )
    _ajustar(resumen)
    _hoja_listas(wb, revisiones)
    _hoja_copias(wb, revisiones)
    wb.save(DESTINO)
    print(f"{len(revisiones)} actividades -> {DESTINO}")


if __name__ == "__main__":
    main()
