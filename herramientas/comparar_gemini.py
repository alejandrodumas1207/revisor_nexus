"""Compara la revisión de Gemini con la referencia validada por el docente (fase 0).

Mide por actividad la coincidencia por criterio (exacta y a un nivel) y por calificación final (exacta y ±1),
calculando ambas calificaciones con el dominio y con la misma integridad (formato, tardanza, copia) de la
referencia, para que solo cuente la diferencia de juicio. Salida: datos_locales/gemini/comparacion.xlsx.
"""

import json
from collections import Counter
from pathlib import Path
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

from revisor.dominio.calificacion import calificaciones_validas
from revisor.dominio.instrumentos import CriterioPropio, NivelPropio, RubricaPropia
from revisor.dominio.integridad import Tardanza, VeredictoCopia, calificacion_final

RAIZ = Path(__file__).resolve().parent.parent / "datos_locales"
DESTINO = RAIZ / "gemini" / "comparacion.xlsx"
NIVELES = (NivelPropio("Cumple", 100), NivelPropio("Parcial", 70), NivelPropio("No cumple", 0))
INDICE = {"cumple": 0, "parcial": 1, "no_cumple": 2}
CORTO = {"cumple": "✓", "parcial": "½", "no_cumple": "✗"}
DISTINTO = PatternFill("solid", fgColor="FCE4D6")
NEGRITA = Font(bold=True)


def _final(rev: dict[str, Any], a: dict[str, Any], niveles: dict[str, str]) -> int:
    rubrica = RubricaPropia(
        rev["actividad"],
        tuple(
            CriterioPropio(c["id"], c["criterio"], NIVELES, float(c["puntos"])) for c in rev["lista_cotejo"]
        ),
    )
    lista = rubrica.calificar({c.id: INDICE[niveles[c.id]] for c in rubrica.criterios})
    validas = (
        calificaciones_validas(3, [100, 70, 40, 0]) if rev["actividad"].endswith("D4") else range(10, -1, -1)
    )
    return calificacion_final(
        lista,
        list(validas),
        formato_incorrecto=bool(a.get("formato_incorrecto")),
        tardanza=Tardanza(a.get("tardanza") or "a tiempo"),
        copia=VeredictoCopia.desde_texto(a.get("copia")),
    )


def _comparar(rev: dict[str, Any], gemini: dict[str, Any]) -> tuple[dict[str, Any], list[list[Any]]]:
    ids = [c["id"] for c in rev["lista_cotejo"]]
    crit, finales, filas = Counter[str](), Counter[str](), []
    for a in rev["alumnos"]:
        g = gemini.get(a["matricula"], {})
        if not a.get("niveles") or "niveles" not in g:
            continue
        for i in ids:
            pasos = abs(INDICE[a["niveles"][i]] - INDICE[g["niveles"][i]])
            crit["total"] += 1
            crit["exacta"] += pasos == 0
            crit["un_nivel"] += pasos <= 1
        f_ref, f_gem = _final(rev, a, a["niveles"]), _final(rev, a, g["niveles"])
        finales["total"] += 1
        finales["exacta"] += f_ref == f_gem
        finales["mas_menos_1"] += abs(f_ref - f_gem) <= 1
        finales["suma_dif"] += abs(f_ref - f_gem)
        pares = [f"{CORTO[a['niveles'][i]]} / {CORTO[g['niveles'][i]]}" for i in ids]
        comentarios = "\n".join(f"{i}: {g['comentarios'].get(i, '')}" for i in ids)
        filas.append([a["matricula"], a.get("nombre"), f_ref, f_gem, f_gem - f_ref, *pares, comentarios])
    return {
        "criterios": crit,
        "finales": finales,
        "errores": sum("error" in v for v in gemini.values()),
    }, filas


def _porcentaje(parte: int, total: int) -> str:
    return f"{parte / total:.0%}" if total else "—"


def main() -> None:
    wb = Workbook()
    resumen = wb.active
    if resumen is None:
        raise SystemExit("No se pudo crear el libro.")
    resumen.title = "Resumen"
    resumen.append(
        [
            "Actividad",
            "Alumnos",
            "Criterio exacto",
            "Criterio a 1 nivel",
            "Final exacta",
            "Final ±1",
            "Diferencia media",
            "Errores de Gemini",
        ]
    )
    for archivo in sorted((RAIZ / "gemini").glob("E*.json")):
        rev = json.loads((RAIZ / "rnap" / f"{archivo.stem}_revision_v2.json").read_text(encoding="utf-8"))
        medidas, filas = _comparar(rev, json.loads(archivo.read_text(encoding="utf-8")))
        c, f = medidas["criterios"], medidas["finales"]
        resumen.append(
            [
                archivo.stem,
                f["total"],
                _porcentaje(c["exacta"], c["total"]),
                _porcentaje(c["un_nivel"], c["total"]),
                _porcentaje(f["exacta"], f["total"]),
                _porcentaje(f["mas_menos_1"], f["total"]),
                round(f["suma_dif"] / f["total"], 2) if f["total"] else "—",
                medidas["errores"],
            ]
        )
        ws = wb.create_sheet(archivo.stem)
        ws.append(
            [
                "Matrícula",
                "Alumno",
                "Final referencia",
                "Final Gemini",
                "Dif.",
                *[f"{c['id']} ref / gemini" for c in rev["lista_cotejo"]],
                "Comentarios de Gemini",
            ]
        )
        for fila in filas:
            ws.append(fila)
            for celda in ws[ws.max_row][5:-1]:
                if (
                    isinstance(celda.value, str)
                    and celda.value.split(" / ")[0] != celda.value.split(" / ")[-1]
                ):
                    celda.fill = DISTINTO
        for celda in ws[1]:
            celda.font = NEGRITA
        for fila in ws.iter_rows(min_row=2):
            fila[-1].alignment = Alignment(wrap_text=True, vertical="top")
        (
            ws.column_dimensions["B"].width,
            ws.column_dimensions[ws.cell(1, ws.max_column).column_letter].width,
        ) = 30, 100
    for celda in resumen[1]:
        celda.font = NEGRITA
    wb.save(DESTINO)
    for fila in resumen.iter_rows(values_only=True):
        print(fila)
    print(f"-> {DESTINO}")


if __name__ == "__main__":
    main()
