import io
import zipfile
from pathlib import Path, PurePath

import pytest

from revisor.adaptadores.almacen_local import AlmacenLocal, RutaFueraDelAlmacen
from revisor.dominio.modelos import (
    Alumno,
    Archivo,
    Curso,
    Elemento,
    EntregaNexus,
    RubricaNexus,
    TipoElemento,
)
from revisor.servicios.descarga import descargar_elemento

DIMENSION = Elemento("1.2", 4560461, TipoElemento.EVIDENCIA, "Dimensión 2", 2.5, False, None, None, None)


def _archivo(nombre: str, contenido: bytes, url: str = "") -> Archivo:
    return Archivo(nombre, url or f"Contenedores G2/{nombre}", len(contenido), None, False)


def _zip() -> bytes:
    memoria = io.BytesIO()
    with zipfile.ZipFile(memoria, "w") as z:
        z.writestr("audio.m4a", b"audio")
    return memoria.getvalue()


ZIP = _zip()
CONTENIDOS = {
    "Contenedores G2/tarea.pdf": b"%PDF-ana",
    "Contenedores G2/p1.jpg": b"jpg1",
    "Contenedores G2/p2.jpg": b"jpg2",
    "Contenedores G2/expo.zip": ZIP,
}


class FuenteFalsa:
    def __init__(self, entregas: list[EntregaNexus], falla: str = "") -> None:
        self.entregas = entregas
        self.falla = falla
        self.bajadas: list[str] = []

    def listar_cursos(self, carpeta: str | None = None) -> list[Curso]:
        return []

    def leer_elementos(self, curso_id: int) -> list[Elemento]:
        return [DIMENSION]

    def leer_rubrica(self, elemento: Elemento) -> RubricaNexus | None:
        return None

    def leer_entregas(self, curso_id: int, elemento: Elemento) -> list[EntregaNexus]:
        return self.entregas

    def descargar(self, url_relativa: str) -> bytes:
        self.bajadas.append(url_relativa)
        if url_relativa == self.falla:
            raise ConnectionError("se cortó la conexión")
        return CONTENIDOS[url_relativa]


def _entregas() -> list[EntregaNexus]:
    ana = Alumno("2012345", 1, "PRUEBA ANA")
    luis = Alumno("2012346", 2, "EJEMPLO LUIS")
    eva = Alumno("2012347", 3, "MUESTRA EVA")
    sin = Alumno("2012348", 4, "SIN ENTREGA")
    return [
        EntregaNexus(ana, "1.2", (_archivo("tarea.pdf", CONTENIDOS["Contenedores G2/tarea.pdf"]),), None),
        EntregaNexus(luis, "1.2", (_archivo("p1.jpg", b"jpg1"), _archivo("p2.jpg", b"jpg2")), None),
        EntregaNexus(eva, "1.2", (_archivo("expo.zip", ZIP),), None),
        EntregaNexus(sin, "1.2", (), None),
    ]


def test_descarga_con_la_convencion_de_carpetas(tmp_path: Path):
    resumen = descargar_elemento(FuenteFalsa(_entregas()), AlmacenLocal(tmp_path), 747689, DIMENSION)
    carpeta = tmp_path / "Etapa 1" / "Dimensión 2"
    assert (carpeta / "2012345_PRUEBA ANA.pdf").read_bytes() == b"%PDF-ana"
    assert (carpeta / "2012346_EJEMPLO LUIS_1.jpg").exists() and (
        carpeta / "2012346_EJEMPLO LUIS_2.jpg"
    ).exists()
    assert (carpeta / "2012347_MUESTRA EVA" / "audio.m4a").read_bytes() == b"audio"  # zip descomprimido
    assert len(resumen.descargados) == 4
    assert [e.alumno.matricula for e in resumen.sin_entrega] == ["2012348"]


def test_no_vuelve_a_bajar_lo_que_ya_existe_con_el_mismo_tamano(tmp_path: Path):
    descargar_elemento(FuenteFalsa(_entregas()), AlmacenLocal(tmp_path), 747689, DIMENSION)
    fuente = FuenteFalsa(_entregas())
    resumen = descargar_elemento(fuente, AlmacenLocal(tmp_path), 747689, DIMENSION)
    assert fuente.bajadas == [] and len(resumen.omitidos) == 4


def test_un_archivo_fallido_no_detiene_al_resto(tmp_path: Path):
    fuente = FuenteFalsa(_entregas(), falla="Contenedores G2/p1.jpg")
    resumen = descargar_elemento(fuente, AlmacenLocal(tmp_path), 747689, DIMENSION)
    assert len(resumen.descargados) == 3
    assert resumen.errores == ["2012346_EJEMPLO LUIS_1.jpg: se cortó la conexión"]


def test_almacen_no_permite_salir_de_su_carpeta(tmp_path: Path):
    with pytest.raises(RutaFueraDelAlmacen):
        AlmacenLocal(tmp_path / "curso").guardar(PurePath("../fuera.txt"), b"x")
