"""Descargar las entregas de un elemento completo: una consulta a NEXUS y los archivos en paralelo."""

from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import PurePath, PurePosixPath

from revisor.dominio.modelos import Archivo, Elemento, EntregaNexus
from revisor.dominio.rutas import carpeta_elemento, nombre_archivo_entrega
from revisor.puertos.almacen import AlmacenArchivos
from revisor.puertos.nexus import FuenteNexus

PARALELOS = 4  # descargas simultáneas; prudente con el servidor de NEXUS


@dataclass(frozen=True, slots=True)
class Pendiente:
    ruta: PurePath
    archivo: Archivo


@dataclass(slots=True)
class ResumenDescarga:
    entregas: list[EntregaNexus]
    descargados: list[PurePath] = field(default_factory=list[PurePath])
    omitidos: list[PurePath] = field(default_factory=list[PurePath])
    errores: list[str] = field(default_factory=list[str])

    @property
    def sin_entrega(self) -> list[EntregaNexus]:
        return [e for e in self.entregas if not e.entrego]


def rutas_de_entrega(elemento: Elemento, entrega: EntregaNexus) -> list[Pendiente]:
    """Dónde va cada archivo del alumno: Etapa N/Dimensión K/{matrícula}_{NOMBRE}[_k].ext."""
    carpeta = carpeta_elemento(elemento.codigo, elemento.nombre)
    varios = len(entrega.archivos) > 1
    return [
        Pendiente(
            carpeta
            / nombre_archivo_entrega(
                entrega.alumno.matricula, entrega.alumno.nombre, _extension(a), k if varios else 0
            ),
            a,
        )
        for k, a in enumerate(entrega.archivos, start=1)
    ]


def descargar_elemento(
    fuente: FuenteNexus,
    almacen: AlmacenArchivos,
    curso_id: int,
    elemento: Elemento,
    paralelos: int = PARALELOS,
) -> ResumenDescarga:
    resumen = ResumenDescarga(fuente.leer_entregas(curso_id, elemento))
    pendientes: list[Pendiente] = []
    for entrega in resumen.entregas:
        for p in rutas_de_entrega(elemento, entrega):
            if almacen.existe(p.ruta, p.archivo.peso):
                resumen.omitidos.append(p.ruta)
            else:
                pendientes.append(p)

    def bajar(p: Pendiente) -> tuple[PurePath, str | None]:
        return _bajar(fuente, almacen, p)

    with ThreadPoolExecutor(max_workers=paralelos) as grupo:
        for ruta, error in grupo.map(bajar, pendientes):
            if error:
                resumen.errores.append(f"{ruta.name}: {error}")
            else:
                resumen.descargados.append(ruta)
    return resumen


def _bajar(fuente: FuenteNexus, almacen: AlmacenArchivos, p: Pendiente) -> tuple[PurePath, str | None]:
    try:
        almacen.guardar(p.ruta, fuente.descargar(p.archivo.url))
    except Exception as e:
        return p.ruta, str(e).splitlines()[0][:150] if str(e) else type(e).__name__
    return p.ruta, None


def _extension(archivo: Archivo) -> str:
    for nombre in (archivo.nombre, archivo.url):
        sufijo = PurePosixPath(nombre).suffix
        if sufijo:
            return sufijo
    return ""


def resumen_texto(resumenes: Sequence[tuple[Elemento, ResumenDescarga]]) -> str:
    lineas = [
        f"{e.codigo} {e.nombre}: {len(r.descargados)} nuevos, {len(r.omitidos)} ya estaban, "
        f"{len(r.sin_entrega)} sin entrega, {len(r.errores)} con error"
        for e, r in resumenes
    ]
    return "\n".join(lineas)
