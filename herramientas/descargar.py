"""Lista cursos y actividades de NEXUS y descarga las entregas por actividad (solo lectura en NEXUS).

Uso:
  uv run python ../herramientas/descargar.py --listar
  uv run python ../herramientas/descargar.py --curso "Redes" --elementos 1.2 1.4
Los archivos quedan en ~/Desktop/NEXUS/<periodo>/<Curso Grupo>/Entregas/, como en nexus_tools.
"""

import argparse
from pathlib import Path

from revisor.adaptadores.almacen_local import AlmacenLocal
from revisor.adaptadores.nexus_api.cliente import ClienteHttpNexus
from revisor.adaptadores.nexus_api.lectura import LecturaNexusApi
from revisor.adaptadores.nexus_api.sesion import abrir_sesion
from revisor.dominio.modelos import Curso
from revisor.servicios.descarga import descargar_elemento, resumen_texto

RAIZ = Path(__file__).resolve().parent.parent
PERFIL = RAIZ / "datos_locales" / "perfil_nexus"
DATOS = Path.home() / "Desktop" / "NEXUS"


def _elegir(cursos: list[Curso], texto: str) -> Curso:
    candidatos = [c for c in cursos if texto.lower() in f"{c.nombre} {c.grupo}".lower()]
    if len(candidatos) != 1:
        opciones = "; ".join(f"{c.nombre} {c.grupo}" for c in candidatos or cursos)
        raise SystemExit(f"'{texto}' coincide con {len(candidatos)} cursos. Opciones: {opciones}")
    return candidatos[0]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--periodo", default=None, help="carpeta de NEXUS, por ejemplo AD2026; por defecto la más reciente"
    )
    parser.add_argument("--listar", action="store_true")
    parser.add_argument("--curso", default="")
    parser.add_argument("--elementos", nargs="*", default=[], help="códigos como 1.2 1.4 PIA; vacío = todos")
    args = parser.parse_args()

    lectura = LecturaNexusApi(ClienteHttpNexus(abrir_sesion(PERFIL)))
    cursos = lectura.listar_cursos(args.periodo)
    if args.listar:
        for c in cursos:
            elementos = ", ".join(f"{e.codigo} {e.nombre}" for e in lectura.leer_elementos(c.id))
            print(f"- {c.nombre} {c.grupo} [{c.carpeta}]: {elementos}")
        return
    curso = _elegir(cursos, args.curso)
    elementos = [
        e for e in lectura.leer_elementos(curso.id) if not args.elementos or e.codigo in args.elementos
    ]
    almacen = AlmacenLocal(DATOS / curso.carpeta / f"{curso.nombre} {curso.grupo}" / "Entregas")
    resultados = [(e, descargar_elemento(lectura, almacen, curso.id, e)) for e in elementos]
    print(resumen_texto(resultados))
    for _, r in resultados:
        for error in r.errores:
            print(f"  ERROR {error}")


if __name__ == "__main__":
    main()
