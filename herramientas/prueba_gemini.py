"""Fase 0: ¿Gemini llega a las mismas conclusiones que la revisión validada por el docente?

Para cada alumno de una actividad: convierte su notebook a texto, lo seudonimiza (y verifica que no quede
nombre ni matrícula), pide la evaluación a Gemini con la misma lista de cotejo y la compara con la
referencia (datos_locales/rnap/<ACT>_revision_v2.json). Guarda cada respuesta para poder reanudar.

Uso: uv run python ../herramientas/prueba_gemini.py E1D3 [--limite 5] [--modelo gemini-3.5-flash]
Sin --modelo rota entre los gratuitos; si se acaba la cuota, deja las entregas para revisión con Claude.
"""

import argparse
import json
import re
import time
from pathlib import Path
from typing import Any

from revisor.adaptadores.extractores.notebook import NotebookInvalido, leer_notebook, texto_para_ia
from revisor.adaptadores.ia.gemini import MODELOS_ROTACION, ProveedorGemini
from revisor.adaptadores.ia.rotacion import ProveedorRotativo
from revisor.dominio.evaluacion import CriterioLista, Evaluacion
from revisor.dominio.seudonimo import seudonimizar
from revisor.dominio.verificacion import cifras_no_encontradas, sin_trabajo
from revisor.puertos.ia import CuotaAgotada, ProveedorIA
from revisor.servicios.revision import revisar_entrega, seccion_verificacion

RAIZ = Path(__file__).resolve().parent.parent / "datos_locales"
FORMULARIOS = Path.home() / "Desktop" / "RNAP_Revision_E1_E2" / "formularios"
PATRON = {"E1D3": "E1_D3*", "E1D4": "E1_D4*", "E2D3": "ETAPA 2_DIMENSI*3*", "E2D4": "ETAPA 2_DIMENSI*4*"}
CONTEXTO = {
    "E1D3": "Etapa 1, Dimensión 3: longitud de secuencia (maxlen) en un clasificador de sentimiento con RNN.",
    "E1D4": "Etapa 1, Evidencia: clasificador de sentimiento, limpieza, matriz de confusión y sobreajuste.",
    "E2D3": "Etapa 2, Dimensión 3: RNN simple contra LSTM para predecir temperatura y memoria larga.",
    "E2D4": "Etapa 2, Evidencia: clasificador de párrafos ATA con BiLSTM, matriz de confusión y conclusión.",
}
PAUSA = 6.0  # segundos entre llamadas, para no agotar la cuota por minuto del nivel gratuito


def _lista(rev: dict[str, Any]) -> list[CriterioLista]:
    return [
        CriterioLista(
            c["id"], c["criterio"], float(c["puntos"]), c["cumple"], c.get("parcial") or "", c["no_cumple"]
        )
        for c in rev["lista_cotejo"]
    ]


def _notebooks(actividad: str) -> dict[str, tuple[bytes, str]]:
    """Contenido y NOMBRE declarado de cada notebook legible, por matrícula."""
    encontrados: dict[str, tuple[bytes, str]] = {}
    for archivo in (f for c in FORMULARIOS.glob(PATRON[actividad]) for f in c.rglob("*") if f.is_file()):
        contenido = archivo.read_bytes()
        try:
            r = leer_notebook(contenido)
        except NotebookInvalido:
            continue
        matricula = r.matricula or (m.group(0) if (m := re.search(r"\d{7}", archivo.name)) else "")
        encontrados.setdefault(matricula, (contenido, r.nombre))
    return encontrados


def _texto_seguro(contenido: bytes, nombres: list[str], matricula: str) -> str:
    """Texto seudonimizado. Si aún aparece la matrícula o una palabra del nombre, no se envía."""
    texto = seudonimizar(texto_para_ia(contenido), nombres)
    palabras = {p for n in nombres for p in re.split(r"[\s_]+", n) if len(p) >= 3}
    restos = [p for p in palabras if re.search(rf"(?<![^\W_]){re.escape(p)}(?![^\W_])", texto, re.IGNORECASE)]
    if matricula in texto or restos:
        raise ValueError(f"Quedaron datos personales en el texto: {restos or [matricula]}")
    return texto


def _a_json(e: Evaluacion) -> dict[str, Any]:
    return {
        "niveles": {k: v.nivel for k, v in e.criterios.items()},
        "evidencia": {k: v.evidencia for k, v in e.criterios.items()},
        "comentarios": {k: v.comentario for k, v in e.criterios.items()},
        "comentarios_generales": e.comentarios_generales,
        "alertas": list(e.alertas),
        "modelo": e.modelo,
        "version_prompt": e.version_prompt,
    }


def _proveedor(modelo: str | None) -> ProveedorIA:
    """Un modelo fijo si se pide; si no, rotación entre los gratuitos sin Lite."""
    if modelo:
        return ProveedorGemini(modelo)
    return ProveedorRotativo([ProveedorGemini(m) for m in MODELOS_ROTACION])


def _sin_trabajo(lista: list[CriterioLista]) -> dict[str, Any]:
    """Resultado sin IA para una entrega sin respuestas ni celdas ejecutadas."""
    return {
        "niveles": {c.id: "no_cumple" for c in lista},
        "evidencia": {c.id: "Sin respuestas ni celdas con salida (verificado por código)." for c in lista},
        "comentarios": {c.id: "Plantilla sin responder." for c in lista},
        "comentarios_generales": "",
        "alertas": [],
        "modelo": "regla",
        "version_prompt": "",
    }


def _dejar_para_claude(actividad: str, matricula: str, texto: str, verificacion: str) -> Path:
    """Guarda la entrega seudonimizada para que Claude la revise desde Claude Code (sin costo extra)."""
    carpeta = RAIZ / "gemini" / "pendientes_claude" / actividad
    carpeta.mkdir(parents=True, exist_ok=True)
    archivo = carpeta / f"{matricula}.txt"
    archivo.write_text(f"{texto}\n\n{verificacion}", encoding="utf-8")
    return archivo


def _revisar_alumno(
    a: dict[str, Any],
    datos: tuple[bytes, str],
    lista: list[CriterioLista],
    actividad: str,
    proveedor: ProveedorIA,
    sin_cuota: bool,
) -> tuple[dict[str, Any], bool]:
    """Devuelve el resultado del alumno y si ya no queda cuota."""
    contenido, nombre_nb = datos
    reporte = leer_notebook(contenido)
    if sin_trabajo(reporte.respuestas, reporte.celdas_con_salida):
        return _sin_trabajo(lista), sin_cuota
    faltantes = cifras_no_encontradas(reporte.respuestas, reporte.salidas)
    texto = _texto_seguro(contenido, [a.get("nombre") or "", nombre_nb], a["matricula"])
    if not sin_cuota:
        try:
            evaluacion = revisar_entrega(proveedor, lista, CONTEXTO[actividad], texto, faltantes)
            return {**_a_json(evaluacion), "cifras_no_encontradas": faltantes}, False
        except CuotaAgotada:
            sin_cuota = True
    archivo = _dejar_para_claude(actividad, a["matricula"], texto, seccion_verificacion(faltantes))
    return {"pendiente_claude": str(archivo), "cifras_no_encontradas": faltantes}, sin_cuota


def evaluar(actividad: str, limite: int | None, modelo: str | None) -> Path:
    rev = json.loads((RAIZ / "rnap" / f"{actividad}_revision_v2.json").read_text(encoding="utf-8"))
    destino = RAIZ / "gemini" / f"{actividad}.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    hechos: dict[str, Any] = json.loads(destino.read_text(encoding="utf-8")) if destino.exists() else {}
    notebooks, lista, proveedor = _notebooks(actividad), _lista(rev), _proveedor(modelo)
    pendientes = [
        a
        for a in rev["alumnos"]
        if a.get("niveles")
        and a["matricula"] in notebooks
        and "niveles" not in hechos.get(a["matricula"], {})
    ]
    sin_cuota = False
    for a in pendientes[:limite]:
        inicio = time.time()
        try:
            hechos[a["matricula"]], sin_cuota = _revisar_alumno(
                a, notebooks[a["matricula"]], lista, actividad, proveedor, sin_cuota
            )
            estado = hechos[a["matricula"]].get("modelo") or "pendiente para Claude"
            print(f"{a['matricula']}: {estado} ({time.time() - inicio:.0f} s)")
        except Exception as e:
            hechos[a["matricula"]] = {"error": str(e)[:300]}
            print(f"{a['matricula']}: ERROR {str(e)[:120]}")
        destino.write_text(json.dumps(hechos, ensure_ascii=False, indent=1), encoding="utf-8")
        if not sin_cuota and hechos[a["matricula"]].get("modelo") not in (None, "regla"):
            time.sleep(PAUSA)
    return destino


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("actividad", choices=sorted(PATRON))
    parser.add_argument("--limite", type=int, default=None)
    parser.add_argument("--modelo", default=None, help="un modelo fijo; si se omite, rotación")
    args = parser.parse_args()
    print(f"-> {evaluar(args.actividad, args.limite, args.modelo)}")


if __name__ == "__main__":
    main()
