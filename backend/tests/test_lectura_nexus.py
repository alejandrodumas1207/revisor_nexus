"""Lectura de NEXUS con respuestas de ejemplo que imitan el formato real (sin datos de alumnos reales)."""

from collections.abc import Mapping
from datetime import datetime
from typing import Any

import pytest

from revisor.adaptadores.nexus_api.lectura import LecturaNexusApi, fecha
from revisor.dominio.modelos import TipoElemento

CARPETAS = {
    "Carpetas": [
        {"CarpetaId": 1, "Nombre": "AD2025", "FechaCreacion": "2025-01-10T00:00:00", "Cursos": []},
        {"CarpetaId": 2, "Nombre": "AD2026", "FechaCreacion": "2026-01-10T00:00:00", "Cursos": []},
    ]
}
CURSOS = {
    "Carpetas": [
        {"Cursos": [{"CursoId": 747689, "Nombre": "Redes  Neuronales", "Grupos": [{"Nombre": "5V1"}]}]}
    ]
}
ESTRUCTURA = {
    "Estructura": {
        "Etapas": [
            {
                "Posicion": 1,
                "Nombre": "Etapa 1",
                "Evidencias": [
                    {
                        "EvidenciaId": 4560461,
                        "Posicion": 2,
                        "Descripcion": "Dimensión 2",
                        "Valor": 2.5,
                        "UsaRubrica": False,
                        "FechaFin": "2026-08-30T23:59:00",
                        "FechaLimite": None,
                    },
                    {
                        "EvidenciaId": 4560463,
                        "Posicion": 4,
                        "Descripcion": "Evidencia de aprendizaje",
                        "Valor": 5,
                        "UsaRubrica": True,
                        "FechaFin": None,
                        "FechaLimite": None,
                    },
                ],
            }
        ],
        "ProductoIntegrador": {"ProductoIntegradorId": 99, "Nombre": "PIA", "Valor": 10, "UsaRubrica": True},
    }
}
RUBRICA = {
    "Rubrica": {
        "RubricaId": 1909378,
        "Criterios": [
            {"CriterioId": 11, "Descripcion": "Comprensión", "Posicion": 1},
            {"CriterioId": 12, "Descripcion": "Desarrollo", "Posicion": 2},
        ],
        "NivelDominios": [
            {"NivelDominioId": 70 + i, "Nombre": n, "Posicion": i + 1}
            for i, n in enumerate(["Completa", "Suficiente", "Débil", "Sin evidencia"])
        ],
        "CriterioNivelDominios": [
            {"CriterioNivelDominioId": c * 100 + i, "CriterioId": c, "NivelDominioId": 70 + i}
            for c in (11, 12)
            for i in range(4)
        ],
    }
}
ESTUDIANTES = {
    "Estudiantes": [
        {
            "CuentaId": 748333,
            "NombreUsuario": "2012345",
            "Nombre": "Ana",
            "ApellidoPaterno": "Prueba",
            "ApellidoMaterno": None,
            "Entregas": [
                {
                    "Estado": True,
                    "Extemporanea": True,
                    "Documento": {
                        "Nombre": "tarea",
                        "Extension": ".pdf",
                        "Peso": 210885,
                        "URL": "Contenedores G2/x.pdf",
                        "FechaCreacion": "2026-08-30T13:11:58.7",
                    },
                }
            ],
            "Retroalimentaciones": [{"RetroalimentacionId": 40458364, "Descripcion": "Bien."}],
            "Calificacion": {"Valor": 90.0},
        },
        {
            "CuentaId": 748348,
            "NombreUsuario": "2012346",
            "Nombre": "Luis",
            "ApellidoPaterno": "Ejemplo",
            "Entregas": [{"Estado": False, "Documento": {"Nombre": "vieja.pdf", "URL": "y"}}],
            "Retroalimentaciones": [],
            "Calificacion": None,
        },
    ]
}


class ClienteFalso:
    def __init__(self) -> None:
        self.consultas: list[tuple[str, Mapping[str, Any]]] = []

    def post_json(self, ruta: str, cuerpo: Mapping[str, Any]) -> dict[str, Any]:
        self.consultas.append((ruta, cuerpo))
        if ruta == "Curso/ConsultarCarpetaCursos":
            return CARPETAS if cuerpo["CarpetaId"] == 0 else CURSOS
        return {
            "Estructura/ConsultarEstructura": ESTRUCTURA,
            "Rubrica/ConsultarRubrica": RUBRICA,
            "Portafolio/ConsultarPortafolioElementoEvaluable": ESTUDIANTES,
        }[ruta]

    def descargar(self, url_relativa: str) -> bytes:
        return b"contenido"


def test_cursos_del_periodo_mas_reciente():
    cliente = ClienteFalso()
    cursos = LecturaNexusApi(cliente).listar_cursos()
    assert cliente.consultas[1][1]["CarpetaId"] == 2
    assert (cursos[0].id, cursos[0].nombre, cursos[0].grupo, cursos[0].carpeta) == (
        747689,
        "Redes Neuronales",
        "5V1",
        "AD2026",
    )


def test_periodo_inexistente():
    with pytest.raises(RuntimeError, match="AD1999"):
        LecturaNexusApi(ClienteFalso()).listar_cursos("AD1999")


def test_estructura_con_evidencias_y_pia():
    elementos = LecturaNexusApi(ClienteFalso()).leer_elementos(747689)
    assert [e.codigo for e in elementos] == ["1.2", "1.4", "PIA"]
    assert elementos[0].fin == datetime(2026, 8, 30, 23, 59)
    assert elementos[2].tipo is TipoElemento.PIA and elementos[1].usa_rubrica


def test_rubrica_con_identificadores_por_criterio_y_nivel():
    lectura = LecturaNexusApi(ClienteFalso())
    evidencia = lectura.leer_elementos(747689)[1]
    rubrica = lectura.leer_rubrica(evidencia)
    assert rubrica is not None and rubrica.porcentajes == [100.0, 70.0, 40.0, 0.0]
    assert rubrica.criterios[1].opciones[1].criterio_nivel_dominio_id == 1201
    assert lectura.leer_rubrica(lectura.leer_elementos(747689)[0]) is None


def test_entregas_de_todo_el_grupo_en_una_consulta():
    lectura = LecturaNexusApi(ClienteFalso())
    elemento = lectura.leer_elementos(747689)[0]
    ana, luis = lectura.leer_entregas(747689, elemento)
    assert (ana.alumno.matricula, ana.alumno.cuenta_id, ana.alumno.nombre) == (
        "2012345",
        748333,
        "Prueba Ana",
    )
    assert ana.archivos[0].nombre == "tarea.pdf" and ana.archivos[0].extemporaneo
    assert ana.calificacion_nexus == 90.0 and ana.retros_nexus[0].id == 40458364
    assert not luis.entrego  # su única entrega está dada de baja
    assert luis.calificacion_nexus is None


def test_fechas_de_nexus():
    assert fecha("2026-08-30T13:11:58.787") == datetime(2026, 8, 30, 13, 11, 58, 787000)
    assert fecha("0001-01-01T00:00:00") is None
