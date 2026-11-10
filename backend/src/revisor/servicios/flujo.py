"""Flujo de un elemento: sincronizar con NEXUS, descargar y revisar cada entrega con la IA.

Por alumno: reúne sus archivos, extrae texto e imágenes, busca la marca del profesor por código, verifica
cifras de notebooks, seudonimiza el texto, pide la evaluación y la guarda con su procedencia. No repite
una revisión hecha con el mismo instrumento y la misma versión de instrucciones.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field

from revisor.dominio.contenido import ContenidoEntrega, unir
from revisor.dominio.modelos import Curso, Elemento, EntregaNexus
from revisor.dominio.rutas import carpeta_elemento
from revisor.dominio.seudonimo import datos_personales_restantes, seudonimizar
from revisor.puertos.almacen import AlmacenArchivos
from revisor.puertos.ia import CuotaAgotada, ProveedorIA
from revisor.puertos.lector import LectorEntregas
from revisor.puertos.nexus import FuenteNexus
from revisor.puertos.repositorio import Instrumento, Repositorio
from revisor.servicios.descarga import ResumenDescarga, descargar_elemento
from revisor.servicios.revision import VERSION_PROMPT, revisar_entrega

LIMITE_IMAGENES = 10  # por alumno: suficiente para una libreta o un reporte sin agotar la cuota


class SinInstrumento(RuntimeError):
    """El elemento no tiene lista de cotejo; hay que crearla antes de revisar."""


@dataclass(slots=True)
class ResultadoRevision:
    revisados: list[str] = field(default_factory=list[str])
    ya_revisados: list[str] = field(default_factory=list[str])
    sin_contenido: list[str] = field(default_factory=list[str])  # nada legible: lo revisa el docente
    pendientes: list[str] = field(default_factory=list[str])  # sin cuota de IA: para Claude o mañana
    errores: list[str] = field(default_factory=list[str])
    avisos: dict[str, tuple[str, ...]] = field(default_factory=dict[str, tuple[str, ...]])


def sincronizar_elemento(
    fuente: FuenteNexus, almacen: AlmacenArchivos, repo: Repositorio, curso: Curso, elemento: Elemento
) -> ResumenDescarga:
    """Lee el elemento de NEXUS, descarga lo nuevo y guarda el estado de cada alumno."""
    repo.guardar_curso(curso, [elemento])
    resumen = descargar_elemento(fuente, almacen, curso.id, elemento)
    repo.guardar_entregas(curso.id, elemento, resumen.entregas)
    return resumen


def revisar_elemento(
    proveedor: ProveedorIA,
    lector: LectorEntregas,
    almacen: AlmacenArchivos,
    repo: Repositorio,
    curso_id: int,
    elemento: Elemento,
    entregas: Sequence[EntregaNexus],
    contexto: str,
) -> ResultadoRevision:
    instrumento = repo.instrumento_vigente(curso_id, elemento.id)
    if instrumento is None:
        raise SinInstrumento(f"{elemento.codigo} {elemento.nombre} no tiene lista de cotejo.")
    resultado, sin_cuota = ResultadoRevision(), False
    for entrega in (e for e in entregas if e.entrego):
        matricula = entrega.alumno.matricula
        if _ya_revisada(repo, curso_id, elemento, entrega, instrumento):
            resultado.ya_revisados.append(matricula)
            continue
        if sin_cuota:
            resultado.pendientes.append(matricula)
            continue
        try:
            sin_cuota = _revisar_alumno(
                proveedor,
                lector,
                almacen,
                repo,
                curso_id,
                elemento,
                entrega,
                instrumento,
                contexto,
                resultado,
            )
        except Exception as e:
            resultado.errores.append(f"{matricula}: {str(e)[:200]}")
    return resultado


def _ya_revisada(
    repo: Repositorio, curso_id: int, elemento: Elemento, entrega: EntregaNexus, instrumento: Instrumento
) -> bool:
    previa = repo.ultima_revision(curso_id, elemento.id, entrega.alumno.cuenta_id)
    return (
        previa is not None
        and previa.instrumento_id == instrumento.id
        and previa.evaluacion.version_prompt == VERSION_PROMPT
    )


def _revisar_alumno(
    proveedor: ProveedorIA,
    lector: LectorEntregas,
    almacen: AlmacenArchivos,
    repo: Repositorio,
    curso_id: int,
    elemento: Elemento,
    entrega: EntregaNexus,
    instrumento: Instrumento,
    contexto: str,
    resultado: ResultadoRevision,
) -> bool:
    """Revisa un alumno. Devuelve True si se agotó la cuota de IA."""
    matricula = entrega.alumno.matricula
    contenido, marca = _leer(lector, almacen, elemento, matricula)
    if contenido.avisos:
        resultado.avisos[matricula] = contenido.avisos
    if contenido.vacio:
        resultado.sin_contenido.append(matricula)
        return False
    texto = seudonimizar(contenido.texto, [entrega.alumno.nombre])
    if restos := datos_personales_restantes(texto, [entrega.alumno.nombre]):
        raise ValueError(f"No se envió: quedaron datos personales en el texto ({len(restos)}).")
    try:
        evaluacion = revisar_entrega(
            proveedor, instrumento.criterios, contexto, texto, contenido.cifras_faltantes, contenido.imagenes
        )
    except CuotaAgotada:
        resultado.pendientes.append(matricula)
        return True
    repo.guardar_revision(curso_id, elemento.id, entrega.alumno.cuenta_id, instrumento.id, evaluacion, marca)
    resultado.revisados.append(matricula)
    return False


def _leer(
    lector: LectorEntregas, almacen: AlmacenArchivos, elemento: Elemento, matricula: str
) -> tuple[ContenidoEntrega, bool | None]:
    contenidos: list[ContenidoEntrega] = []
    marcas: list[bool] = []
    for ruta in almacen.archivos_de(carpeta_elemento(elemento.codigo, elemento.nombre), matricula):
        datos = almacen.leer(ruta)
        contenidos.append(lector.extraer(ruta.name, datos))
        marca = lector.marca_revision(ruta.name, datos)
        if marca is not None:
            marcas.append(marca)
    return unir(contenidos, LIMITE_IMAGENES), (any(marcas) if marcas else None)
