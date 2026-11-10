"""Repositorio en SQLite con SQL explícito y migraciones numeradas (ADR 0006).

Las revisiones son historial: cada propuesta es una fila nueva con su procedencia y nunca se sobrescribe.
"""

import hashlib
import json
import sqlite3
import threading
from collections.abc import Sequence
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from revisor.dominio.evaluacion import CriterioLista, Evaluacion, EvaluacionCriterio
from revisor.dominio.integridad import DecisionDocente, Tardanza, VeredictoCopia
from revisor.dominio.modelos import Curso, Elemento, EntregaNexus, Origen
from revisor.puertos.repositorio import Instrumento, RevisionGuardada

MIGRACIONES: tuple[str, ...] = (
    # 1: esquema inicial
    """
    CREATE TABLE cursos (
        id INTEGER PRIMARY KEY, nombre TEXT NOT NULL, grupo TEXT NOT NULL, carpeta TEXT NOT NULL
    );
    CREATE TABLE elementos (
        curso_id INTEGER NOT NULL REFERENCES cursos(id), id INTEGER NOT NULL, codigo TEXT NOT NULL,
        tipo TEXT NOT NULL, nombre TEXT NOT NULL, valor REAL NOT NULL, usa_rubrica INTEGER NOT NULL,
        PRIMARY KEY (curso_id, id)
    );
    CREATE TABLE alumnos (cuenta_id INTEGER PRIMARY KEY, matricula TEXT NOT NULL, nombre TEXT NOT NULL);
    CREATE TABLE entregas (
        curso_id INTEGER NOT NULL, elemento_id INTEGER NOT NULL, cuenta_id INTEGER NOT NULL REFERENCES alumnos,
        archivos TEXT NOT NULL, calificacion_nexus REAL, retros_nexus TEXT NOT NULL, actualizado TEXT NOT NULL,
        PRIMARY KEY (curso_id, elemento_id, cuenta_id),
        FOREIGN KEY (curso_id, elemento_id) REFERENCES elementos (curso_id, id)
    );
    CREATE TABLE instrumentos (
        id INTEGER PRIMARY KEY AUTOINCREMENT, curso_id INTEGER NOT NULL, elemento_id INTEGER NOT NULL,
        version INTEGER NOT NULL, criterios TEXT NOT NULL, huella TEXT NOT NULL, creado TEXT NOT NULL,
        UNIQUE (curso_id, elemento_id, version)
    );
    CREATE TABLE revisiones (
        id INTEGER PRIMARY KEY AUTOINCREMENT, curso_id INTEGER NOT NULL, elemento_id INTEGER NOT NULL,
        cuenta_id INTEGER NOT NULL, instrumento_id INTEGER NOT NULL REFERENCES instrumentos(id),
        origen TEXT NOT NULL, modelo TEXT NOT NULL, version_prompt TEXT NOT NULL, criterios TEXT NOT NULL,
        comentarios_generales TEXT NOT NULL, alertas TEXT NOT NULL, marca_ia INTEGER, detalle_marca TEXT NOT NULL,
        marca_codigo INTEGER, creado TEXT NOT NULL
    );
    CREATE INDEX revisiones_por_alumno ON revisiones (curso_id, elemento_id, cuenta_id, id);
    CREATE TABLE decisiones (
        curso_id INTEGER NOT NULL, elemento_id INTEGER NOT NULL, cuenta_id INTEGER NOT NULL,
        formato_incorrecto INTEGER, tardanza TEXT, copia TEXT, actualizado TEXT NOT NULL,
        PRIMARY KEY (curso_id, elemento_id, cuenta_id)
    );
    CREATE TABLE cargas (
        id INTEGER PRIMARY KEY AUTOINCREMENT, curso_id INTEGER NOT NULL, elemento_id INTEGER NOT NULL,
        cuenta_id INTEGER NOT NULL, calificacion INTEGER NOT NULL, huella_retro TEXT NOT NULL,
        retro_id INTEGER NOT NULL, subido TEXT NOT NULL
    );
    """,
)


def _ahora() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _huella(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()[:16]


class RepositorioSqlite:
    def __init__(self, ruta: Path | str) -> None:
        self._conexion = sqlite3.connect(str(ruta), check_same_thread=False)
        self._conexion.row_factory = sqlite3.Row
        self._candado = threading.Lock()
        with self._candado:
            self._conexion.execute("PRAGMA foreign_keys = ON")
            if str(ruta) != ":memory:":
                self._conexion.execute("PRAGMA journal_mode = WAL")
            self._migrar()

    def _migrar(self) -> None:
        aplicada = int(self._conexion.execute("PRAGMA user_version").fetchone()[0])
        for numero, sql in enumerate(MIGRACIONES[aplicada:], start=aplicada + 1):
            with self._conexion:
                self._conexion.executescript(sql)
                self._conexion.execute(f"PRAGMA user_version = {numero}")

    @property
    def version_esquema(self) -> int:
        return int(self._conexion.execute("PRAGMA user_version").fetchone()[0])

    def _ejecutar(self, sql: str, parametros: Sequence[Any] = ()) -> sqlite3.Cursor:
        with self._candado, self._conexion:
            return self._conexion.execute(sql, parametros)

    def _consultar(self, sql: str, parametros: Sequence[Any] = ()) -> list[sqlite3.Row]:
        with self._candado:
            return self._conexion.execute(sql, parametros).fetchall()

    # ---------------------------------------------------------------- cursos y entregas
    def guardar_curso(self, curso: Curso, elementos: Sequence[Elemento]) -> None:
        self._ejecutar(
            "INSERT INTO cursos VALUES (?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET nombre=excluded.nombre, "
            "grupo=excluded.grupo, carpeta=excluded.carpeta",
            (curso.id, curso.nombre, curso.grupo, curso.carpeta),
        )
        for e in elementos:
            self._ejecutar(
                "INSERT INTO elementos VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT(curso_id, id) DO UPDATE SET "
                "codigo=excluded.codigo, tipo=excluded.tipo, nombre=excluded.nombre, valor=excluded.valor, "
                "usa_rubrica=excluded.usa_rubrica",
                (curso.id, e.id, e.codigo, e.tipo.value, e.nombre, e.valor, int(e.usa_rubrica)),
            )

    def guardar_entregas(self, curso_id: int, elemento: Elemento, entregas: Sequence[EntregaNexus]) -> None:
        for e in entregas:
            a = e.alumno
            self._ejecutar(
                "INSERT INTO alumnos VALUES (?, ?, ?) ON CONFLICT(cuenta_id) DO UPDATE SET "
                "matricula=excluded.matricula, nombre=excluded.nombre",
                (a.cuenta_id, a.matricula, a.nombre),
            )
            archivos = json.dumps(
                [{**asdict(x), "fecha": x.fecha.isoformat() if x.fecha else None} for x in e.archivos],
                ensure_ascii=False,
            )
            retros = json.dumps([asdict(r) for r in e.retros_nexus], ensure_ascii=False)
            self._ejecutar(
                "INSERT INTO entregas VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT(curso_id, elemento_id, cuenta_id) "
                "DO UPDATE SET archivos=excluded.archivos, calificacion_nexus=excluded.calificacion_nexus, "
                "retros_nexus=excluded.retros_nexus, actualizado=excluded.actualizado",
                (curso_id, elemento.id, a.cuenta_id, archivos, e.calificacion_nexus, retros, _ahora()),
            )

    # ---------------------------------------------------------------- instrumentos
    def guardar_instrumento(
        self, curso_id: int, elemento_id: int, criterios: Sequence[CriterioLista]
    ) -> Instrumento:
        texto = json.dumps([asdict(c) for c in criterios], ensure_ascii=False, sort_keys=True)
        vigente = self.instrumento_vigente(curso_id, elemento_id)
        if vigente and _huella(
            json.dumps([asdict(c) for c in vigente.criterios], ensure_ascii=False, sort_keys=True)
        ) == _huella(texto):
            return vigente
        version = (vigente.version if vigente else 0) + 1
        cursor = self._ejecutar(
            "INSERT INTO instrumentos (curso_id, elemento_id, version, criterios, huella, creado) VALUES (?, ?, ?, ?, ?, ?)",
            (curso_id, elemento_id, version, texto, _huella(texto), _ahora()),
        )
        return Instrumento(int(cursor.lastrowid or 0), version, tuple(criterios))

    def instrumento_vigente(self, curso_id: int, elemento_id: int) -> Instrumento | None:
        filas = self._consultar(
            "SELECT id, version, criterios FROM instrumentos WHERE curso_id=? AND elemento_id=? "
            "ORDER BY version DESC LIMIT 1",
            (curso_id, elemento_id),
        )
        if not filas:
            return None
        criterios = tuple(CriterioLista(**c) for c in json.loads(filas[0]["criterios"]))
        return Instrumento(int(filas[0]["id"]), int(filas[0]["version"]), criterios)

    # ---------------------------------------------------------------- revisiones
    def guardar_revision(
        self,
        curso_id: int,
        elemento_id: int,
        cuenta_id: int,
        instrumento_id: int,
        evaluacion: Evaluacion,
        marca_codigo: bool | None,
    ) -> int:
        e = evaluacion
        criterios = json.dumps({k: asdict(v) for k, v in e.criterios.items()}, ensure_ascii=False)
        cursor = self._ejecutar(
            "INSERT INTO revisiones (curso_id, elemento_id, cuenta_id, instrumento_id, origen, modelo, version_prompt, "
            "criterios, comentarios_generales, alertas, marca_ia, detalle_marca, marca_codigo, creado) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                curso_id,
                elemento_id,
                cuenta_id,
                instrumento_id,
                e.origen.value,
                e.modelo,
                e.version_prompt,
                criterios,
                e.comentarios_generales,
                json.dumps(list(e.alertas), ensure_ascii=False),
                None if e.marca_revision is None else int(e.marca_revision),
                e.detalle_marca,
                None if marca_codigo is None else int(marca_codigo),
                _ahora(),
            ),
        )
        return int(cursor.lastrowid or 0)

    def ultima_revision(self, curso_id: int, elemento_id: int, cuenta_id: int) -> RevisionGuardada | None:
        filas = self._consultar(
            "SELECT * FROM revisiones WHERE curso_id=? AND elemento_id=? AND cuenta_id=? ORDER BY id DESC LIMIT 1",
            (curso_id, elemento_id, cuenta_id),
        )
        if not filas:
            return None
        f = filas[0]
        criterios = {k: EvaluacionCriterio(**v) for k, v in json.loads(f["criterios"]).items()}
        evaluacion = Evaluacion(
            criterios,
            f["comentarios_generales"],
            tuple(json.loads(f["alertas"])),
            Origen(f["origen"]),
            f["modelo"],
            f["version_prompt"],
            None if f["marca_ia"] is None else bool(f["marca_ia"]),
            f["detalle_marca"],
        )
        marca = None if f["marca_codigo"] is None else bool(f["marca_codigo"])
        return RevisionGuardada(int(f["id"]), int(f["instrumento_id"]), evaluacion, marca)

    # ---------------------------------------------------------------- decisiones del docente
    def guardar_decision(
        self, curso_id: int, elemento_id: int, cuenta_id: int, decision: DecisionDocente
    ) -> None:
        d = decision
        self._ejecutar(
            "INSERT INTO decisiones VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT(curso_id, elemento_id, cuenta_id) "
            "DO UPDATE SET formato_incorrecto=excluded.formato_incorrecto, tardanza=excluded.tardanza, "
            "copia=excluded.copia, actualizado=excluded.actualizado",
            (
                curso_id,
                elemento_id,
                cuenta_id,
                None if d.formato_incorrecto is None else int(d.formato_incorrecto),
                None if d.tardanza is None else d.tardanza.value,
                None if d.copia is None else d.copia.value,
                _ahora(),
            ),
        )

    def decision(self, curso_id: int, elemento_id: int, cuenta_id: int) -> DecisionDocente:
        filas = self._consultar(
            "SELECT * FROM decisiones WHERE curso_id=? AND elemento_id=? AND cuenta_id=?",
            (curso_id, elemento_id, cuenta_id),
        )
        if not filas:
            return DecisionDocente()
        f = filas[0]
        return DecisionDocente(
            None if f["formato_incorrecto"] is None else bool(f["formato_incorrecto"]),
            None if f["tardanza"] is None else Tardanza(f["tardanza"]),
            None if f["copia"] is None else VeredictoCopia(f["copia"]),
        )

    # ---------------------------------------------------------------- bitácora de cargas
    def registrar_carga(
        self, curso_id: int, elemento_id: int, cuenta_id: int, calificacion: int, retro: str, retro_id: int
    ) -> None:
        self._ejecutar(
            "INSERT INTO cargas (curso_id, elemento_id, cuenta_id, calificacion, huella_retro, retro_id, subido) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (curso_id, elemento_id, cuenta_id, calificacion, _huella(retro), retro_id, _ahora()),
        )

    def ya_subida(
        self, curso_id: int, elemento_id: int, cuenta_id: int, calificacion: int, retro: str
    ) -> bool:
        filas = self._consultar(
            "SELECT calificacion, huella_retro FROM cargas WHERE curso_id=? AND elemento_id=? AND cuenta_id=? "
            "ORDER BY id DESC LIMIT 1",
            (curso_id, elemento_id, cuenta_id),
        )
        return (
            bool(filas)
            and filas[0]["calificacion"] == calificacion
            and filas[0]["huella_retro"] == _huella(retro)
        )
