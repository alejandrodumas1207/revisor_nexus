"""Importa a la base el historial validado de RNAP E1-E2: listas de cotejo y revisiones (fase 0).

Lee de NEXUS solo la lista de cada elemento (CuentaId de cada matrícula); no descarga ni modifica nada.
Uso: uv run python ../herramientas/importar_rnap.py
"""

import json
from pathlib import Path
from typing import Any

from revisor.adaptadores.nexus_api.cliente import ClienteHttpNexus
from revisor.adaptadores.nexus_api.lectura import LecturaNexusApi
from revisor.adaptadores.nexus_api.sesion import abrir_sesion
from revisor.adaptadores.persistencia.sqlite import RepositorioSqlite
from revisor.dominio.evaluacion import CriterioLista, Evaluacion, EvaluacionCriterio
from revisor.dominio.modelos import Origen

RAIZ = Path(__file__).resolve().parent.parent
DATOS = RAIZ / "datos_locales"
CURSO_ID = 747689  # Redes Neuronales y Aprendizaje Profundo 5V1 (hoja Config del maestro)
ACTIVIDADES = {"E1D3": "1.3", "E1D4": "1.4", "E2D3": "2.3", "E2D4": "2.4"}
VERSION = "rnap-v2.2"  # revisión hecha con Claude y validada por el docente


def _evaluacion(a: dict[str, Any]) -> Evaluacion:
    criterios = {
        cid: EvaluacionCriterio(
            nivel, a.get("evidencia", {}).get(cid, ""), a.get("comentarios", {}).get(cid, "")
        )
        for cid, nivel in a["niveles"].items()
    }
    return Evaluacion(
        criterios,
        str(a.get("comentarios_generales") or ""),
        tuple(a.get("alertas") or []),
        Origen.CLAUDE,
        "claude-code",
        VERSION,
    )


def main() -> None:
    lectura = LecturaNexusApi(ClienteHttpNexus(abrir_sesion(DATOS / "perfil_nexus")))
    curso = next(c for c in lectura.listar_cursos("AD2026") if c.id == CURSO_ID)
    elementos = {e.codigo: e for e in lectura.leer_elementos(CURSO_ID)}
    repo = RepositorioSqlite(DATOS / "revisor.db")
    repo.guardar_curso(curso, list(elementos.values()))
    for actividad, codigo in ACTIVIDADES.items():
        elemento = elementos[codigo]
        entregas = lectura.leer_entregas(CURSO_ID, elemento)
        repo.guardar_entregas(CURSO_ID, elemento, entregas)
        cuentas = {e.alumno.matricula: e.alumno.cuenta_id for e in entregas}
        rev = json.loads((DATOS / "rnap" / f"{actividad}_revision_v2.json").read_text(encoding="utf-8"))
        lista = [
            CriterioLista(
                c["id"],
                c["criterio"],
                float(c["puntos"]),
                c["cumple"],
                c.get("parcial") or "",
                c["no_cumple"],
            )
            for c in rev["lista_cotejo"]
        ]
        instrumento = repo.guardar_instrumento(CURSO_ID, elemento.id, lista)
        importados = 0
        for a in rev["alumnos"]:
            if a.get("niveles") and a["matricula"] in cuentas:
                repo.guardar_revision(
                    CURSO_ID, elemento.id, cuentas[a["matricula"]], instrumento.id, _evaluacion(a), None
                )
                importados += 1
        print(f"{actividad} ({codigo}): lista v{instrumento.version}, {importados} revisiones importadas")


if __name__ == "__main__":
    main()
