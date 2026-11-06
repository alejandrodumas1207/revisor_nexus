"""Prueba de fase 0 con RNAP Etapas 1 y 2: resume cada entrega para diseñar listas de cotejo.

Lee los formularios descargados de Drive, revisa formato, extrae respuestas y código de cada notebook,
cruza con las calificaciones del Excel de revisión y marca pares sospechosos de copia.
La salida queda en datos_locales/rnap/ (contiene datos de alumnos; no se versiona).
"""

import zipfile
from dataclasses import dataclass
from pathlib import Path

import openpyxl

from revisor.adaptadores.extractores.notebook import NotebookInvalido, ReporteNotebook, leer_notebook
from revisor.dominio.formato import revisar_formato
from revisor.dominio.similitud import normalizar_codigo, normalizar_texto, pares_similares

RAIZ = Path.home() / "Desktop" / "RNAP_Revision_E1_E2"
FORMULARIOS = RAIZ / "formularios"
EXCEL = RAIZ / "Revision_RNAP_E1_E2.xlsx"
SALIDA = Path(__file__).resolve().parent.parent / "datos_locales" / "rnap"
UMBRAL_TEXTO = 0.25
UMBRAL_CODIGO = 0.85


@dataclass(frozen=True)
class Actividad:
    clave: str  # E1D3
    prefijo: str  # E1_D3
    carpeta: str  # patrón de la carpeta del formulario
    en_excel: str  # inicio del texto en la columna Actividad


ACTIVIDADES = (
    Actividad("E1D3", "E1_D3", "E1_D3*", "E1 · D3"),
    Actividad("E1D4", "E1_D4", "E1_D4*", "E1 · D4"),
    Actividad("E2D3", "E2_D3", "ETAPA 2_DIMENSI*3*", "E2 · D3"),
    Actividad("E2D4", "E2_D4", "ETAPA 2_DIMENSI*4*", "E2 · D4"),
)


@dataclass
class Entrega:
    archivo: Path
    formato: list[str]
    reporte: ReporteNotebook | None
    matricula: str


def _leer(archivo: Path) -> tuple[ReporteNotebook | None, list[str]]:
    if archivo.suffix.lower() == ".zip":
        with zipfile.ZipFile(archivo) as z:
            notebooks = [n for n in z.namelist() if n.endswith(".ipynb")]
            if not notebooks:
                return None, [f"Zip sin notebook: {z.namelist()[:5]}"]
            return leer_notebook(z.read(notebooks[0])), ["Entregó el notebook dentro de un zip."]
    try:
        return leer_notebook(archivo.read_bytes()), []
    except NotebookInvalido:
        return None, ["El archivo no es un notebook legible."]


def _entregas(act: Actividad) -> list[Entrega]:
    carpetas = list(FORMULARIOS.glob(act.carpeta))
    entregas: list[Entrega] = []
    for archivo in sorted(f for c in carpetas for f in c.rglob("*") if f.is_file()):
        formato = revisar_formato(archivo.name, act.prefijo)
        reporte, extra = _leer(archivo)
        obs = [*formato.penalizables, *extra, *(f"(solo aviso) {a}" for a in formato.avisos)]
        mat = (reporte.matricula if reporte else "") or formato.matricula_en_nombre
        if reporte and formato.matricula_en_nombre and reporte.matricula != formato.matricula_en_nombre:
            obs.append(
                f"Matrícula del nombre ({formato.matricula_en_nombre}) ≠ notebook ({reporte.matricula})."
            )
        entregas.append(Entrega(archivo, obs, reporte, mat))
    return entregas


def _excel() -> dict[tuple[str, str], tuple[object, str, str]]:
    filas = list(openpyxl.load_workbook(EXCEL, read_only=True, data_only=True)["Calificaciones"].values)
    h = next(i for i, f in enumerate(filas) if f and "Actividad" in f)
    enc = list(filas[h])
    col = {n: enc.index(n) for n in ("Matrícula", "Actividad", "Calificación")}
    retro = enc.index("Retroalimentación para el alumno")
    obs = enc.index("Observaciones para el profesor")
    datos: dict[tuple[str, str], tuple[object, str, str]] = {}
    for f in filas[h + 1 :]:
        if f[col["Actividad"]]:
            clave = (str(f[col["Matrícula"]]), str(f[col["Actividad"]])[:7])
            datos[clave] = (f[col["Calificación"]], str(f[retro] or ""), str(f[obs] or ""))
    return datos


def _sospechas(entregas: list[Entrega]) -> list[str]:
    con = [e for e in entregas if e.reporte]
    texto = {e.matricula: normalizar_texto(" ".join(e.reporte.respuestas.values())) for e in con if e.reporte}
    codigo = {
        e.matricula: normalizar_codigo("\n".join(b.codigo for b in e.reporte.bloques.values()))
        for e in con
        if e.reporte
    }
    lineas = [f"- Respuestas {p.a} y {p.b}: {p.similitud:.0%}" for p in pares_similares(texto, UMBRAL_TEXTO)]
    lineas += [f"- Código {p.a} y {p.b}: {p.similitud:.0%}" for p in pares_similares(codigo, UMBRAL_CODIGO)]
    return lineas or ["- Sin pares por encima de los umbrales."]


def _enunciado(entregas: list[Entrega]) -> str:
    """Preguntas y bloques de la plantilla, tomados de la primera entrega legible."""
    for e in entregas:
        if e.archivo.suffix == ".ipynb" and e.reporte:
            texto = e.archivo.read_text(encoding="utf-8", errors="ignore")
            return f"(Plantilla: ver `{e.archivo.name}`; {len(texto)} caracteres)"
    return "(sin plantilla legible)"


def _bloque_alumno(e: Entrega, excel: dict[tuple[str, str], tuple[object, str, str]], act: Actividad) -> str:
    cal, retro, obs = excel.get((e.matricula, act.en_excel), (None, "", ""))
    r = e.reporte
    partes = [
        f"### {e.matricula or '¿sin matrícula?'} · {r.nombre if r else ''}",
        f"Archivo: `{e.archivo.name}`",
        f"Formato: {'; '.join(e.formato) or 'correcto'}",
        f"Excel: calificación {cal} | retro: {retro} | obs: {obs}",
    ]
    if r:
        faltan = [t for ok, t in r.verificacion if not ok]
        partes += [
            f"Verificación: {len(r.verificacion) - len(faltan)}/{len(r.verificacion)} OK; faltan: {faltan}",
            f"Resumen: {r.resumen}",
            f"Celdas sin ejecutar: {r.celdas_sin_ejecutar}; errores: {list(r.errores)}",
            f"Respuestas vacías: {r.respuestas_vacias}",
        ]
        partes += [f"- **{i}**: {t[:1200]}" for i, t in r.respuestas.items()]
        partes += [f"- `{i}` código:\n```\n{b.codigo[:800]}\n```" for i, b in r.bloques.items()]
    return "\n".join(partes)


def main() -> None:
    SALIDA.mkdir(parents=True, exist_ok=True)
    excel = _excel()
    for act in ACTIVIDADES:
        entregas = _entregas(act)
        doc = [
            f"# {act.clave}: {len(entregas)} archivos",
            _enunciado(entregas),
            "## Posibles copias (similitud de n-gramas)",
            *_sospechas(entregas),
            "## Entregas",
            *(_bloque_alumno(e, excel, act) for e in entregas),
        ]
        destino = SALIDA / f"{act.clave}.md"
        destino.write_text("\n\n".join(doc), encoding="utf-8")
        print(f"{act.clave}: {len(entregas)} entregas -> {destino}")


if __name__ == "__main__":
    main()
