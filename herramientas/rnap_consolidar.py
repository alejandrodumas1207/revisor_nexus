"""Junta las revisiones v2 de RNAP E1-E2 en un Excel para que el docente las valide.

La calificación final la calcula el dominio (instrumento → formato → tardanza → copia → válida en NEXUS),
igual que la calcularía la app al subirla. La retroalimentación desglosada también la arma el dominio.
Lee datos_locales/rnap/*_revision_v2.json.
"""

import json
from pathlib import Path
from typing import Any

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.worksheet import Worksheet

from revisor.dominio.calificacion import calificaciones_validas
from revisor.dominio.informe import CriterioEvaluado, InformeAlumno, componer_retroalimentacion
from revisor.dominio.instrumentos import CriterioPropio, NivelPropio, RubricaPropia
from revisor.dominio.integridad import (
    DecisionDocente,
    DetalleCalificacion,
    Integridad,
    Tardanza,
    VeredictoCopia,
    detalle_calificacion,
    integridad_vigente,
)

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
COL_FORMATO, COL_TARDANZA, COL_COPIA = "Formato (aplicar)", "Tardanza (aplicar)", "Copia (aplicar)"
OPCIONES = {
    COL_FORMATO: ["sí", "no"],
    COL_TARDANZA: [t.value for t in Tardanza],
    COL_COPIA: [v.value for v in VeredictoCopia],
}
OCULTAS = ["_rec_formato", "_rec_tardanza", "_rec_copia"]  # recomendación original, para detectar cambios
type Decisiones = dict[tuple[str, str], DecisionDocente]
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


def _recomendada(a: dict[str, Any]) -> Integridad:
    return Integridad(
        bool(a.get("formato_incorrecto")),
        Tardanza(a.get("tardanza") or "a tiempo"),
        VeredictoCopia.desde_texto(a.get("copia")),
    )


def _detalle(actividad: str, integridad: Integridad, lista: float) -> DetalleCalificacion:
    validas = RUBRICA_EVIDENCIA if actividad.endswith("D4") else SIN_RUBRICA
    return detalle_calificacion(
        lista,
        validas,
        formato_incorrecto=integridad.formato_incorrecto,
        tardanza=integridad.tardanza,
        copia=integridad.copia,
    )


def _companeros(rev: dict[str, Any], matricula: str) -> tuple[str, ...]:
    """Nombre y matrícula de los compañeros con los que el alumno aparece en un par de copia o sospecha."""
    nombres = {a["matricula"]: a.get("nombre") or "" for a in rev["alumnos"]}
    otros: list[str] = []
    for c in rev.get("copias", []):
        if VeredictoCopia.desde_texto(c["veredicto"]) is VeredictoCopia.NINGUNA or matricula not in (
            c["a"],
            c["b"],
        ):
            continue
        otro = c["b"] if c["a"] == matricula else c["a"]
        otros.append(f"{nombres.get(otro, '').strip()} ({otro})".strip())
    return tuple(dict.fromkeys(otros))


def _retroalimentacion(
    rev: dict[str, Any], a: dict[str, Any], detalle: DetalleCalificacion, copia: VeredictoCopia
) -> str:
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
    justificacion = str(a.get("justificacion_copia") or "") if copia is not VeredictoCopia.NINGUNA else ""
    informe = InformeAlumno(
        criterios,
        detalle,
        str(a.get("comentarios_generales") or ""),
        copia,
        _companeros(rev, a["matricula"]) if copia is not VeredictoCopia.NINGUNA else (),
        justificacion,
        tuple(filter(None, [a.get("aviso_nombre")])),
    )
    return componer_retroalimentacion(informe)


def _fila(
    rev: dict[str, Any], a: dict[str, Any], rubrica: RubricaPropia, decisiones: Decisiones
) -> tuple[list[Any], float | None, bool]:
    ids = [c["id"] for c in rev["lista_cotejo"]]
    lista = _calificacion_lista(rubrica, a)
    recomendada = _recomendada(a)
    decision = decisiones.get((rev["actividad"], str(a.get("matricula"))), DecisionDocente())
    vigente = integridad_vigente(recomendada, decision)
    detalle = _detalle(rev["actividad"], vigente, lista)
    excel = a.get("calificacion_excel")
    dif = detalle.final - excel if isinstance(excel, int | float) else None
    entrego = bool(a.get("archivo"))
    revisar = recomendada.copia is not VeredictoCopia.NINGUNA or (
        entrego and recomendada.tardanza is Tardanza.DUDOSA
    )
    fila = [
        a.get("matricula"),
        a.get("nombre"),
        round(lista, 2),
        "sí" if vigente.formato_incorrecto else "no",
        vigente.tardanza.value if entrego else "a tiempo",
        vigente.copia.value,
        detalle.final,
        excel,
        dif,
        *[NIVEL.get(a.get("niveles", {}).get(i, ""), "") for i in ids],
        _retroalimentacion(rev, a, detalle, vigente.copia),
        _texto_recomendacion(recomendada, entrego),
        "\n".join([*(a.get("alertas") or []), *filter(None, [a.get("tardanza_evidencia")])]),
        "sí" if recomendada.formato_incorrecto else "no",
        recomendada.tardanza.value if entrego else "a tiempo",
        recomendada.copia.value,
    ]
    return fila, dif, revisar


def _texto_recomendacion(r: Integridad, entrego: bool) -> str:
    if not entrego:
        return "Sin archivo."
    formato = "penalizar formato" if r.formato_incorrecto else "formato correcto"
    return f"{formato}; tardanza: {r.tardanza.value}; copia: {r.copia.value}"


def _leer_decisiones(ruta: Path) -> Decisiones:
    """Lo que el docente cambió en las columnas "(aplicar)" respecto a la recomendación original."""
    if not ruta.exists():
        return {}
    decisiones: Decisiones = {}
    for ws in load_workbook(ruta, read_only=True).worksheets:
        filas = list(ws.values)
        enc = list(filas[0]) if filas else []
        if not set([COL_FORMATO, COL_TARDANZA, COL_COPIA, *OCULTAS]) <= set(enc):
            continue
        for f in filas[1:]:
            if f[enc.index("Matrícula")] is not None:
                decisiones[(ws.title, str(f[enc.index("Matrícula")]))] = _decision_de_fila(f, enc)
    return decisiones


def _decision_de_fila(f: tuple[Any, ...], enc: list[Any]) -> DecisionDocente:
    def cambiado(col: str, oculta: str) -> Any:
        valor = f[enc.index(col)]
        return valor if valor != f[enc.index(oculta)] else None

    formato = cambiado(COL_FORMATO, "_rec_formato")
    tardanza = cambiado(COL_TARDANZA, "_rec_tardanza")
    copia = cambiado(COL_COPIA, "_rec_copia")
    return DecisionDocente(
        formato_incorrecto=None if formato is None else formato == "sí",
        tardanza=None if tardanza is None else Tardanza(tardanza),
        copia=None if copia is None else VeredictoCopia.desde_texto(copia),
    )


def _listas_desplegables(ws: Worksheet, columnas: list[str]) -> None:
    for nombre, opciones in OPCIONES.items():
        letra = get_column_letter(columnas.index(nombre) + 1)
        validacion = DataValidation(type="list", formula1=f'"{",".join(opciones)}"', allow_blank=False)
        validacion.add(f"{letra}2:{letra}{ws.max_row}")
        ws.add_data_validation(validacion)


def _hoja_actividad(wb: Workbook, rev: dict[str, Any], decisiones: Decisiones) -> dict[str, int]:
    ws = wb.create_sheet(rev["actividad"])
    ids = [c["id"] for c in rev["lista_cotejo"]]
    columnas = [
        "Matrícula",
        "Alumno",
        "Lista (0-10)",
        COL_FORMATO,
        COL_TARDANZA,
        COL_COPIA,
        "Final",
        "NEXUS",
        "Dif.",
    ]
    _encabezado(
        ws,
        [*columnas, *ids, "Retroalimentación propuesta", "Recomendación de la revisión", "Alertas", *OCULTAS],
        [11, 28, 9, 10, 16, 16, 7, 7, 6] + [5] * len(ids) + [90, 30, 50, 4, 4, 4],
    )
    conteo = {"comparables": 0, "coinciden": 0}
    rubrica = _rubrica(rev)
    for a in rev["alumnos"]:
        fila, dif, revisar = _fila(rev, a, rubrica, decisiones)
        ws.append(fila)
        relleno = REVISAR if revisar else DIFERENCIA if dif is not None and abs(dif) >= 2 else None
        if relleno:
            for celda in ws[ws.max_row]:
                celda.fill = relleno
        if dif is not None:
            conteo["comparables"] += 1
            conteo["coinciden"] += abs(dif) <= 1
    _ajustar(ws)
    _listas_desplegables(ws, [*columnas, *ids])
    for i in range(len(OCULTAS)):
        ws.column_dimensions[get_column_letter(ws.max_column - i)].hidden = True
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


def _resumen(wb: Workbook, revisiones: list[dict[str, Any]], decisiones: Decisiones) -> None:
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
        conteo = _hoja_actividad(wb, rev, decisiones)
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
    decisiones = _leer_decisiones(DESTINO)
    wb = Workbook()
    wb.remove(wb.worksheets[0])
    _resumen(wb, revisiones, decisiones)
    _hoja_listas(wb, revisiones)
    _hoja_copias(wb, revisiones)
    try:
        wb.save(DESTINO)
    except PermissionError:
        raise SystemExit(f"Cierra {DESTINO.name} en Excel y vuelve a ejecutar.") from None
    cambios = sum(1 for d in decisiones.values() if d != DecisionDocente())
    print(f"{len(revisiones)} actividades, {cambios} decisiones del docente aplicadas -> {DESTINO}")


if __name__ == "__main__":
    main()
