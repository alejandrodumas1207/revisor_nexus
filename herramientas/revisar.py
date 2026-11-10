"""Flujo completo de una o varias actividades: sincronizar con NEXUS, descargar y revisar con IA.

Solo lee de NEXUS; nada se sube. Las revisiones quedan en datos_locales/revisor.db con su procedencia.
Uso:
  uv run python ../herramientas/revisar.py --curso "Redes" --elementos 3.2 [--lista lista_3_2.json]
--lista: JSON con la lista de cotejo [{"id", "nombre", "puntos", "cumple", "parcial", "no_cumple"}];
si se omite, se usa la vigente del elemento en la base.
"""

import argparse
import json
from pathlib import Path

from revisor.adaptadores.almacen_local import AlmacenLocal
from revisor.adaptadores.extractores.lector import LectorArchivos
from revisor.adaptadores.ia.gemini import MODELOS_ROTACION, ProveedorGemini
from revisor.adaptadores.ia.rotacion import ProveedorRotativo
from revisor.adaptadores.nexus_api.cliente import ClienteHttpNexus
from revisor.adaptadores.nexus_api.lectura import LecturaNexusApi
from revisor.adaptadores.nexus_api.sesion import abrir_sesion
from revisor.adaptadores.persistencia.sqlite import RepositorioSqlite
from revisor.dominio.evaluacion import CriterioLista
from revisor.servicios.flujo import revisar_elemento, sincronizar_elemento

RAIZ = Path(__file__).resolve().parent.parent
DATOS = RAIZ / "datos_locales"
NEXUS = Path.home() / "Desktop" / "NEXUS"


def _lista(ruta: Path) -> list[CriterioLista]:
    return [CriterioLista(**c) for c in json.loads(ruta.read_text(encoding="utf-8"))]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--periodo", default=None)
    parser.add_argument("--curso", required=True)
    parser.add_argument("--elementos", nargs="+", required=True)
    parser.add_argument("--lista", type=Path, default=None, help="lista de cotejo (solo con un elemento)")
    args = parser.parse_args()
    if args.lista and len(args.elementos) != 1:
        raise SystemExit("--lista se usa con un solo elemento.")

    lectura = LecturaNexusApi(ClienteHttpNexus(abrir_sesion(DATOS / "perfil_nexus")))
    cursos = [
        c
        for c in lectura.listar_cursos(args.periodo)
        if args.curso.lower() in f"{c.nombre} {c.grupo}".lower()
    ]
    if len(cursos) != 1:
        raise SystemExit(f"'{args.curso}' coincide con {len(cursos)} cursos.")
    curso = cursos[0]
    repo = RepositorioSqlite(DATOS / "revisor.db")
    almacen = AlmacenLocal(NEXUS / curso.carpeta / f"{curso.nombre} {curso.grupo}" / "Entregas")
    proveedor = ProveedorRotativo([ProveedorGemini(m) for m in MODELOS_ROTACION])
    for elemento in (e for e in lectura.leer_elementos(curso.id) if e.codigo in args.elementos):
        descarga = sincronizar_elemento(lectura, almacen, repo, curso, elemento)
        if args.lista:
            repo.guardar_instrumento(curso.id, elemento.id, _lista(args.lista))
        r = revisar_elemento(
            proveedor,
            LectorArchivos(),
            almacen,
            repo,
            curso.id,
            elemento,
            descarga.entregas,
            f"{curso.nombre}, {elemento.codigo} {elemento.nombre}",
        )
        print(
            f"{elemento.codigo}: {len(r.revisados)} revisados, {len(r.ya_revisados)} ya estaban, "
            f"{len(r.sin_contenido)} sin contenido legible, {len(r.pendientes)} pendientes (sin cuota), "
            f"{len(r.errores)} con error"
        )
        for error in r.errores:
            print(f"  ERROR {error}")


if __name__ == "__main__":
    main()
