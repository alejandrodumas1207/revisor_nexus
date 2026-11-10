from datetime import datetime
from pathlib import Path

from revisor.adaptadores.persistencia.sqlite import MIGRACIONES, RepositorioSqlite
from revisor.dominio.evaluacion import CriterioLista, Evaluacion, EvaluacionCriterio
from revisor.dominio.integridad import DecisionDocente, Tardanza, VeredictoCopia
from revisor.dominio.modelos import Alumno, Archivo, Curso, Elemento, EntregaNexus, Origen, TipoElemento
from revisor.dominio.retroalimentacion import RetroNexus

CURSO = Curso(747689, "Redes Neuronales", "5V1", "AD2026")
DIMENSION = Elemento("3.2", 99, TipoElemento.EVIDENCIA, "Dimensión 2", 2.5, False, None, None, None)
LISTA = (
    CriterioLista("C1", "Código", 40, "corre", "detalles", "no corre"),
    CriterioLista("C2", "Análisis", 60, "cita", "una cifra", "genérico"),
)


def _repo(tmp_path: Path) -> RepositorioSqlite:
    repo = RepositorioSqlite(tmp_path / "revisor.db")
    repo.guardar_curso(CURSO, [DIMENSION])
    return repo


def _evaluacion(nivel: str = "parcial") -> Evaluacion:
    criterios = {
        "C1": EvaluacionCriterio("cumple", "7/7", "Corre."),
        "C2": EvaluacionCriterio(nivel, "cita 0.81", "Tu tabla dice 0.79."),
    }
    return Evaluacion(
        criterios, "", ("alerta",), Origen.GEMINI, "gemini-3.7-flash", "revision-v3", True, "Rayón"
    )


def test_migraciones_se_aplican_una_vez(tmp_path: Path):
    assert _repo(tmp_path).version_esquema == len(MIGRACIONES)
    assert RepositorioSqlite(tmp_path / "revisor.db").version_esquema == len(MIGRACIONES)  # reabrir no repite


def test_entregas_se_actualizan_sin_duplicar(tmp_path: Path):
    repo = _repo(tmp_path)
    ana = Alumno("2012345", 1, "PRUEBA ANA")
    archivo = Archivo("mapa.png", "x/mapa.png", 10, datetime(2026, 10, 1), False)
    repo.guardar_entregas(CURSO.id, DIMENSION, [EntregaNexus(ana, "3.2", (archivo,), None)])
    repo.guardar_entregas(
        CURSO.id, DIMENSION, [EntregaNexus(ana, "3.2", (archivo,), 90.0, (RetroNexus(5, "Bien"),))]
    )
    filas = repo._consultar("SELECT calificacion_nexus FROM entregas")  # pyright: ignore[reportPrivateUsage]
    assert [f["calificacion_nexus"] for f in filas] == [90.0]


def test_instrumento_versiona_solo_si_cambia(tmp_path: Path):
    repo = _repo(tmp_path)
    v1 = repo.guardar_instrumento(CURSO.id, DIMENSION.id, LISTA)
    assert repo.guardar_instrumento(CURSO.id, DIMENSION.id, LISTA).id == v1.id
    cambiada = (LISTA[0], CriterioLista("C2", "Análisis", 60, "cita sus cifras", "una cifra", "genérico"))
    v2 = repo.guardar_instrumento(CURSO.id, DIMENSION.id, cambiada)
    assert (v1.version, v2.version) == (1, 2)
    vigente = repo.instrumento_vigente(CURSO.id, DIMENSION.id)
    assert vigente is not None and vigente.criterios[1].cumple == "cita sus cifras"


def test_revisiones_son_historial_con_procedencia(tmp_path: Path):
    repo = _repo(tmp_path)
    instrumento = repo.guardar_instrumento(CURSO.id, DIMENSION.id, LISTA)
    repo.guardar_revision(
        CURSO.id, DIMENSION.id, 1, instrumento.id, _evaluacion("parcial"), marca_codigo=False
    )
    repo.guardar_revision(CURSO.id, DIMENSION.id, 1, instrumento.id, _evaluacion("cumple"), marca_codigo=True)
    ultima = repo.ultima_revision(CURSO.id, DIMENSION.id, 1)
    assert ultima is not None and ultima.evaluacion.criterios["C2"].nivel == "cumple"
    assert (ultima.evaluacion.modelo, ultima.evaluacion.version_prompt) == ("gemini-3.7-flash", "revision-v3")
    assert ultima.evaluacion.marca_revision is True and ultima.marca_codigo is True
    total = repo._consultar("SELECT COUNT(*) AS n FROM revisiones")  # pyright: ignore[reportPrivateUsage]
    assert total[0]["n"] == 2


def test_decisiones_del_docente(tmp_path: Path):
    repo = _repo(tmp_path)
    assert repo.decision(CURSO.id, DIMENSION.id, 1) == DecisionDocente()
    decision = DecisionDocente(copia=VeredictoCopia.PARCIAL, tardanza=Tardanza.CONFIRMADA)
    repo.guardar_decision(CURSO.id, DIMENSION.id, 1, decision)
    assert repo.decision(CURSO.id, DIMENSION.id, 1) == decision


def test_no_se_repite_una_carga_identica(tmp_path: Path):
    repo = _repo(tmp_path)
    assert not repo.ya_subida(CURSO.id, DIMENSION.id, 1, 9, "Bien hecho.")
    repo.registrar_carga(CURSO.id, DIMENSION.id, 1, 9, "Bien hecho.", 40458364)
    assert repo.ya_subida(CURSO.id, DIMENSION.id, 1, 9, "Bien hecho.")
    assert not repo.ya_subida(CURSO.id, DIMENSION.id, 1, 9, "Retro corregida.")
