from collections.abc import Sequence
from pathlib import Path, PurePath
from typing import Any

import pytest

from revisor.adaptadores.almacen_local import AlmacenLocal
from revisor.adaptadores.persistencia.sqlite import RepositorioSqlite
from revisor.dominio.contenido import ContenidoEntrega, ImagenPagina
from revisor.dominio.evaluacion import CriterioLista
from revisor.dominio.modelos import Alumno, Archivo, Curso, Elemento, EntregaNexus, TipoElemento
from revisor.puertos.ia import CuotaAgotada
from revisor.servicios.flujo import SinInstrumento, revisar_elemento

CURSO = Curso(747689, "Redes Neuronales", "5V1", "AD2026")
MAPA = Elemento(
    "3.2", 99, TipoElemento.EVIDENCIA, "Dimensión 2. Mapa conceptual", 2.5, False, None, None, None
)
LISTA = (
    CriterioLista("C1", "Conceptos", 50, "a", "b", "c"),
    CriterioLista("C2", "Relaciones", 50, "a", "b", "c"),
)
ANA = Alumno("2012345", 1, "PRUEBA LUNA ANA")
LUIS = Alumno("2012346", 2, "EJEMPLO SOL LUIS")
EVA = Alumno("2012347", 3, "MUESTRA RIO EVA")


class Lector:
    def extraer(self, nombre: str, datos: bytes) -> ContenidoEntrega:
        if nombre.endswith(".mp4"):
            return ContenidoEntrega("", (), (f"{nombre}: video o audio, requiere revisión manual.",))
        return ContenidoEntrega(datos.decode(), (ImagenPagina(nombre, 1, b"jpg"),))

    def marca_revision(self, nombre: str, datos: bytes) -> bool | None:
        return b"firma" in datos


class Proveedor:
    modelo = "falso-1"

    def __init__(self, cuota: int = 99) -> None:
        self.cuota = cuota
        self.textos: list[str] = []

    def generar_json(
        self, instrucciones: str, contenido: str, esquema: dict[str, Any], imagenes: Sequence[bytes] = ()
    ) -> dict[str, Any]:
        if self.cuota <= 0:
            raise CuotaAgotada("sin cuota")
        self.cuota -= 1
        self.textos.append(contenido)
        criterios = [{"id": c.id, "nivel": "cumple", "evidencia": "e", "comentario": "c"} for c in LISTA]
        return {
            "criterios": criterios,
            "comentarios_generales": "",
            "alertas": [],
            "marca_revision": {"hay": False, "detalle": ""},
        }


def _preparar(tmp_path: Path) -> tuple[AlmacenLocal, RepositorioSqlite, list[EntregaNexus]]:
    almacen, repo = AlmacenLocal(tmp_path / "Entregas"), RepositorioSqlite(tmp_path / "revisor.db")
    carpeta = PurePath("Etapa 3/Dimensión 2")
    almacen.guardar(carpeta / "2012345_PRUEBA LUNA ANA.png", b"Mapa de Ana Prueba con firma")
    almacen.guardar(carpeta / "2012346_EJEMPLO SOL LUIS.png", b"Mapa de Luis")
    almacen.guardar(carpeta / "2012347_MUESTRA RIO EVA.mp4", b"video")
    archivo = Archivo("x.png", "u", 1, None, False)
    entregas = [EntregaNexus(a, "3.2", (archivo,), None) for a in (ANA, LUIS, EVA)]
    entregas.append(EntregaNexus(Alumno("2012348", 4, "SIN ENTREGA"), "3.2", (), None))
    repo.guardar_curso(CURSO, [MAPA])
    repo.guardar_entregas(CURSO.id, MAPA, entregas)
    return almacen, repo, entregas


def _revisar(
    proveedor: Proveedor, almacen: AlmacenLocal, repo: RepositorioSqlite, entregas: list[EntregaNexus]
):
    return revisar_elemento(proveedor, Lector(), almacen, repo, CURSO.id, MAPA, entregas, "Mapa conceptual")


def test_sin_lista_de_cotejo_no_se_revisa(tmp_path: Path):
    almacen, repo, entregas = _preparar(tmp_path)
    with pytest.raises(SinInstrumento):
        _revisar(Proveedor(), almacen, repo, entregas)


def test_revisa_guarda_y_no_repite(tmp_path: Path):
    almacen, repo, entregas = _preparar(tmp_path)
    repo.guardar_instrumento(CURSO.id, MAPA.id, LISTA)
    proveedor = Proveedor()
    resultado = _revisar(proveedor, almacen, repo, entregas)
    assert resultado.revisados == ["2012345", "2012346"]
    assert resultado.sin_contenido == ["2012347"] and "revisión manual" in resultado.avisos["2012347"][0]
    guardada = repo.ultima_revision(CURSO.id, MAPA.id, ANA.cuenta_id)
    assert guardada is not None and guardada.marca_codigo is True and guardada.evaluacion.modelo == "falso-1"
    assert "Ana" not in proveedor.textos[0] and "Prueba" not in proveedor.textos[0]  # seudonimizado
    otra = _revisar(Proveedor(), almacen, repo, entregas)
    assert otra.ya_revisados == ["2012345", "2012346"] and not otra.revisados


def test_sin_cuota_el_resto_queda_pendiente(tmp_path: Path):
    almacen, repo, entregas = _preparar(tmp_path)
    repo.guardar_instrumento(CURSO.id, MAPA.id, LISTA)
    resultado = _revisar(Proveedor(cuota=1), almacen, repo, entregas)
    # sin cuota ya no se abre nada más: el resto queda pendiente y se clasifica al reintentar
    assert resultado.revisados == ["2012345"] and resultado.pendientes == ["2012346", "2012347"]
