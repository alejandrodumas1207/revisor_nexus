"""Junta las revisiones v2 de RNAP E1-E2 en un Excel para que el docente las valide.

La calificación final la calcula el dominio (instrumento → formato → tardanza → copia → válida en NEXUS),
igual que la calcularía la app al subirla. La retroalimentación desglosada también la arma el dominio.
Lee datos_locales/rnap/*_revision_v2.json.
"""

import json
from pathlib import Path
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from revisor.dominio.calificacion import calificaciones_validas
from revisor.dominio.informe import CriterioEvaluado, InformeAlumno, componer_retroalimentacion
from revisor.dominio.instrumentos import CriterioPropio, NivelPropio, RubricaPropia
from revisor.dominio.integridad import DetalleCalificacion, Tardanza, VeredictoCopia, detalle_calificacion

CARPETA = Path(__file__).resolve().parent.parent / "datos_locales" / "rnap"
DESTINO = CARPETA / "RNAP_E1_E2_revision_v2.xlsx"
NEGRITA = Font(bold=True, color="FFFFFF")
ENCABEZADO = PatternFill("solid", fgColor="1F3A5F")
DIFERENCIA = PatternFill("solid", fgColor="FCE4D6")
REVISAR = PatternFill("solid", fgColor="FFF2CC")
NIVEL = {"cumple": "✓", "parcial": "½", "no_cumple": "✗"}
NIVELES_LISTA = (
    NivelPropio("Cumple", 100),
    NivelPropio("Cumple parcialmente", 70),
    NivelPropio("No cumple", 0),
)
INDICE_NIVEL = {"cumple": 0, "parcial": 1, "no_cumple": 2}
# Las Evidencias (D4) usan en NEXUS rúbrica de 3 criterios con niveles 100/70/40/0; las D3 no tienen rúbrica
RUBRICA_EVIDENCIA = calificaciones_validas(3, [100, 70, 40, 0])
SIN_RUBRICA = calificaciones_validas(None, [])
_ORDEN_COPIA = {
    VeredictoCopia.CONFIRMADA: 0,
    VeredictoCopia.PARCIAL: 1,
    VeredictoCopia.SOSPECHA: 2,
    VeredictoCopia.NINGUNA: 3,
}


def _encabezado(ws: Worksheet, columnas: list[str], anchos: list[int]) -> None:
    ws.append(columnas)
    for i, ancho in enumerate(anchos, start=1):
        celda = ws.cell(row=1, column=i)
        celda.font, celda.fill = NEGRITA, ENCABEZADO
        ws.column_dimensions[get_column_letter(i)].width = ancho
    ws.freeze_panes = "C2"


def _ajustar(ws: Worksheet) -> None:
    for fila in ws.iter_rows(min_row=2):
        for celda in fila:
            celda.alignment = Alignment(wrap_text=True, vertical="top")


def _rubrica(rev: dict[str, Any]) -> RubricaPropia:
    """La lista de cotejo como rúbrica del dominio: cumple 100 %, parcial 70 %, no cumple 0 %."""
    criterios = tuple(
        CriterioPropio(c["id"], c["criterio"], NIVELES_LISTA, peso=float(c["puntos"]))
        for c in rev["lista_cotejo"]
    )
    return RubricaPropia(rev["actividad"], criterios)


def _calificacion_lista(rubrica: RubricaPropia, a: dict[str, Any]) -> float:
    """0-10 calculada con el dominio a partir de los niveles; sin archivo cuenta como 0."""
    niveles = a.get("niveles") or {}
    if not niveles:
        return 0.0
    return rubrica.calificar({c.id: INDICE_NIVEL[niveles.get(c.id, "no_cumple")] for c in rubrica.criterios})


def _detalle(actividad: str, a: dict[str, Any], lista: float) -> DetalleCalificacion:
    validas = RUBRICA_EVIDENCIA if actividad.endswith("D4") else SIN_RUBRICA
    return detalle_calificacion(
        lista,
        validas,
        formato_incorrecto=bool(a.get("formato_incorrecto")),
        tardanza=Tardanza(a.get("tardanza") or "a tiempo"),
        copia=VeredictoCopia.desde_texto(a.get("copia")),
    )


def _retroalimentacion(rev: dict[str, Any], a: dict[str, Any], detalle: DetalleCalificacion) -> str:
    """Retro desglosada armada por el dominio; si la revisión aún no trae comentarios, la retro anterior."""
    comentarios = a.get("comentarios")
    if not comentarios or not a.get("niveles"):
        return str(a.get("retroalimentacion") or "")
    criterios = tuple(
        CriterioEvaluado(
            c["id"], c["criterio"], float(c["puntos"]), a["niveles"][c["id"]], comentarios.get(c["id"], "")
        )
        for c in rev["lista_cotejo"]
    )
    informe = InformeAlumno(
        criterios,
        detalle,
        str(a.get("fortalezas") or ""),
        str(a.get("pendientes") or ""),
        VeredictoCopia.desde_texto(a.get("copia")),
        str(a.get("justificacion_copia") or ""),
        tuple(filter(None, [a.get("aviso_nombre")])),
    )
    return componer_retroalimentacion(informe)


def _fila(
    rev: dict[str, Any], a: dict[str, Any], rubrica: RubricaPropia
) -> tuple[list[Any], float | None, bool]:
    ids = [c["id"] for c in rev["lista_cotejo"]]
    lista = _calificacion_lista(rubrica, a)
    detalle = _detalle(rev["actividad"], a, lista)
    excel = a.get("calificacion_excel")
    dif = detalle.final - excel if isinstance(excel, int | float) else None
    entrego = bool(a.get("archivo"))
    copia = VeredictoCopia.desde_texto(a.get("copia"))
    revisar = copia is not VeredictoCopia.NINGUNA or (entrego and a.get("tardanza") == "dudosa")
    fila = [
        a.get("matricula"),
        a.get("nombre"),
        round(lista, 2),
        "−1" if a.get("formato_incorrecto") else "",
        a.get("tardanza") if entrego else "sin archivo",
        copia.value,
        detalle.final,
        excel,
        dif,
        *[NIVEL.get(a.get("niveles", {}).get(i, ""), "") for i in ids],
        _retroalimentacion(rev, a, detalle),
        "\n".join([*(a.get("alertas") or []), *filter(None, [a.get("tardanza_evidencia")])]),
    ]
    return fila, dif, revisar


def _hoja_actividad(wb: Workbook, rev: dict[str, Any]) -> dict[str, int]:
    ws = wb.create_sheet(rev["actividad"])
    ids = [c["id"] for c in rev["lista_cotejo"]]
    columnas = [
        "Matrícula",
        "Alumno",
        "Lista (0-10)",
        "Formato",
        "Tardanza",
        "Copia",
        "Final",
        "NEXUS",
        "Dif.",
    ]
    _encabezado(
        ws,
        [*columnas, *ids, "Retroalimentación propuesta", "Alertas"],
        [11, 28, 9, 8, 14, 14, 7, 7, 6] + [5] * len(ids) + [80, 50],
    )
    conteo = {"comparables": 0, "coinciden": 0}
    rubrica = _rubrica(rev)
    for a in rev["alumnos"]:
        fila, dif, revisar = _fila(rev, a, rubrica)
        ws.append(fila)
        relleno = REVISAR if revisar else DIFERENCIA if dif is not None and abs(dif) >= 2 else None
        if relleno:
            for celda in ws[ws.max_row]:
                celda.fill = relleno
        if dif is not None:
            conteo["comparables"] += 1
            conteo["coinciden"] += abs(dif) <= 1
    _ajustar(ws)
    return conteo


def _hoja_listas(wb: Workbook, revisiones: list[dict[str, Any]]) -> None:
    ws = wb.create_sheet("Listas de cotejo")
    _encabezado(
        ws,
        ["Actividad", "Id", "Criterio", "Puntos", "Cumple (100 %)", "Parcial (70 %)", "No cumple (0 %)"],
        [10, 5, 40, 8, 50, 50, 40],
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
    _encabezado(
        ws,
        [
            "Actividad",
            "Alumno A",
            "Alumno B",
            "Veredicto",
            "Explicación",
            "Coincidencias",
            "Decisión del docente",
        ],
        [10, 11, 11, 16, 60, 80, 20],
    )
    for rev in revisiones:
        for c in sorted(
            rev.get("copias", []), key=lambda c: _ORDEN_COPIA[VeredictoCopia.desde_texto(c["veredicto"])]
        ):
            detalle = "\n".join(f"• {x['ubicacion']}: {x['detalle']}" for x in c.get("coincidencias", []))
            veredicto = VeredictoCopia.desde_texto(c["veredicto"]).value
            ws.append([rev["actividad"], c["a"], c["b"], veredicto, c.get("explicacion", ""), detalle, ""])
    _ajustar(ws)


def _contar_copias(rev: dict[str, Any], *veredictos: VeredictoCopia) -> int:
    return sum(1 for c in rev.get("copias", []) if VeredictoCopia.desde_texto(c["veredicto"]) in veredictos)


def _resumen(wb: Workbook, revisiones: list[dict[str, Any]]) -> None:
    ws = wb.create_sheet("Resumen", 0)
    _encabezado(
        ws,
        [
            "Actividad",
            "Alumnos",
            "Coinciden ±1 con NEXUS",
            "Copias (confirmada o parcial)",
            "Sospechas",
            "Tardías confirmadas",
            "Tardías dudosas",
            "Notas",
        ],
        [10, 9, 14, 12, 12, 12, 12, 100],
    )
    for rev in revisiones:
        conteo = _hoja_actividad(wb, rev)
        alumnos = rev["alumnos"]
        ws.append(
            [
                rev["actividad"],
                len(alumnos),
                f"{conteo['coinciden']} de {conteo['comparables']}",
                _contar_copias(rev, VeredictoCopia.CONFIRMADA, VeredictoCopia.PARCIAL),
                _contar_copias(rev, VeredictoCopia.SOSPECHA),
                sum(1 for a in alumnos if a.get("tardanza") == "tardía confirmada"),
                sum(1 for a in alumnos if a.get("tardanza") == "dudosa" and a.get("archivo")),
                rev.get("notas_para_profesor"),
            ]
        )
    _ajustar(ws)


def main() -> None:
    revisiones = [
        json.loads(p.read_text(encoding="utf-8")) for p in sorted(CARPETA.glob("*_revision_v2.json"))
    ]
    wb = Workbook()
    wb.remove(wb.worksheets[0])
    _resumen(wb, revisiones)
    _hoja_listas(wb, revisiones)
    _hoja_copias(wb, revisiones)
    wb.save(DESTINO)
    print(f"{len(revisiones)} actividades -> {DESTINO}")


if __name__ == "__main__":
    main()
