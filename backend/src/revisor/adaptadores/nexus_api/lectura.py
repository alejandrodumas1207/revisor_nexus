"""Lectura de NEXUS por API: periodos, cursos, estructura, rúbricas y entregas de todo un elemento.

Las funciones `_interpretar_*` convierten las respuestas JSON en entidades del dominio y se prueban sin red.
Formatos documentados en docs/nexus_api.md.
"""

import re
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any, Protocol

from revisor.dominio.modelos import (
    Alumno,
    Archivo,
    CriterioRubricaNexus,
    Curso,
    Elemento,
    EntregaNexus,
    OpcionRubricaNexus,
    RubricaNexus,
    TipoElemento,
)
from revisor.dominio.retroalimentacion import RetroNexus

_TIPO_ID = {TipoElemento.EVIDENCIA: 1, TipoElemento.PIA: 2}
# NEXUS no informa el porcentaje de cada nivel; se asume por posición (Completa, Suficiente, Débil, Sin ev.)
PORCENTAJES_POR_POSICION = {4: (100.0, 70.0, 40.0, 0.0), 3: (100.0, 50.0, 0.0), 2: (100.0, 0.0)}


class ClienteLectura(Protocol):
    def post_json(self, ruta: str, cuerpo: Mapping[str, Any]) -> dict[str, Any]: ...

    def descargar(self, url_relativa: str) -> bytes: ...


class LecturaNexusApi:
    def __init__(self, cliente: ClienteLectura) -> None:
        self._cliente = cliente

    def listar_cursos(self, carpeta: str | None = None) -> list[Curso]:
        raiz = self._cliente.post_json(
            "Curso/ConsultarCarpetaCursos", {"CarpetaId": 0, "Pagina": 1, "Paginacion": 50}
        )
        elegida = _elegir_carpeta(raiz.get("Carpetas") or [], carpeta)
        cuerpo = {"CarpetaId": elegida["CarpetaId"], "Pagina": 1, "Paginacion": 100}
        return _interpretar_cursos(
            self._cliente.post_json("Curso/ConsultarCarpetaCursos", cuerpo), elegida["Nombre"]
        )

    def leer_elementos(self, curso_id: int) -> list[Elemento]:
        respuesta = self._cliente.post_json("Estructura/ConsultarEstructura", {"CursoId": curso_id})
        return _interpretar_estructura(respuesta["Estructura"])

    def leer_rubrica(self, elemento: Elemento) -> RubricaNexus | None:
        if not elemento.usa_rubrica:
            return None
        cuerpo = {"TipoElementoId": _TIPO_ID[elemento.tipo], "ElementoId": elemento.id}
        return _interpretar_rubrica(self._cliente.post_json("Rubrica/ConsultarRubrica", cuerpo)["Rubrica"])

    def leer_entregas(self, curso_id: int, elemento: Elemento) -> list[EntregaNexus]:
        cuerpo = {"CursoId": curso_id, "TipoElementoId": _TIPO_ID[elemento.tipo], "ElementoId": elemento.id}
        respuesta = self._cliente.post_json("Portafolio/ConsultarPortafolioElementoEvaluable", cuerpo)
        return [_interpretar_estudiante(e, elemento.codigo) for e in respuesta.get("Estudiantes", [])]

    def descargar(self, url_relativa: str) -> bytes:
        return self._cliente.descargar(url_relativa)


def limpiar(texto: object) -> str:
    return re.sub(r"\s+", " ", str(texto or "")).strip()


def fecha(texto: object) -> datetime | None:
    """NEXUS manda fracciones de segundo de largo variable ("…58.7", "…58.787")."""
    if not texto or str(texto).startswith("0001-01-01"):
        return None
    normal = re.sub(r"(\.\d{1,6})\d*", lambda m: m.group(1).ljust(7, "0"), str(texto).rstrip("Z"))
    return datetime.fromisoformat(normal)


def _elegir_carpeta(carpetas: Sequence[Mapping[str, Any]], nombre: str | None) -> Mapping[str, Any]:
    if not carpetas:
        raise RuntimeError("NEXUS no devolvió periodos (carpetas).")
    if nombre:
        for c in carpetas:
            if limpiar(c.get("Nombre")).lower() == nombre.strip().lower():
                return c
        raise RuntimeError(f"No existe el periodo {nombre!r} en NEXUS.")
    return max(carpetas, key=lambda c: str(c.get("FechaCreacion", "")))


def _interpretar_cursos(respuesta: Mapping[str, Any], carpeta: str) -> list[Curso]:
    cursos: list[Curso] = []
    for car in respuesta.get("Carpetas", []):
        for cur in car.get("Cursos") or []:
            grupos = ", ".join(limpiar(g.get("Nombre")) for g in cur.get("Grupos") or [])
            cursos.append(Curso(int(cur["CursoId"]), limpiar(cur["Nombre"]), grupos, carpeta))
    return cursos


def _interpretar_estructura(estructura: Mapping[str, Any]) -> list[Elemento]:
    elementos = [
        Elemento(
            f"{etapa['Posicion']}.{v['Posicion']}",
            int(v["EvidenciaId"]),
            TipoElemento.EVIDENCIA,
            limpiar(v.get("Descripcion")),
            float(v.get("Valor") or 0),
            bool(v.get("UsaRubrica")),
            None,
            fecha(v.get("FechaFin")),
            fecha(v.get("FechaLimite")),
        )
        for etapa in estructura.get("Etapas", [])
        for v in etapa.get("Evidencias", [])
    ]
    pia = estructura.get("ProductoIntegrador")
    if pia:
        pia_id = pia.get("ProductoIntegradorId") or pia.get("ElementoId")
        elementos.append(
            Elemento(
                "PIA",
                int(pia_id),
                TipoElemento.PIA,
                limpiar(pia.get("Nombre") or pia.get("Descripcion")),
                float(pia.get("Valor") or 0),
                bool(pia.get("UsaRubrica")),
                None,
                fecha(pia.get("FechaFin")),
                fecha(pia.get("FechaLimite")),
            )
        )
    return elementos


def _interpretar_rubrica(rubrica: Mapping[str, Any]) -> RubricaNexus:
    niveles = sorted(rubrica.get("NivelDominios", []), key=lambda n: n["Posicion"])
    porcentajes = PORCENTAJES_POR_POSICION.get(
        len(niveles),
        tuple(100.0 * (len(niveles) - 1 - i) / max(len(niveles) - 1, 1) for i in range(len(niveles))),
    )
    celdas = {
        (c["CriterioId"], c["NivelDominioId"]): c["CriterioNivelDominioId"]
        for c in rubrica.get("CriterioNivelDominios", [])
    }
    criterios = tuple(
        CriterioRubricaNexus(
            int(c["CriterioId"]),
            limpiar(c.get("Descripcion")),
            tuple(
                OpcionRubricaNexus(
                    int(n["NivelDominioId"]),
                    int(celdas[(c["CriterioId"], n["NivelDominioId"])]),
                    int(n["Posicion"]),
                    p,
                )
                for n, p in zip(niveles, porcentajes, strict=True)
            ),
        )
        for c in sorted(rubrica.get("Criterios", []), key=lambda c: c.get("Posicion", 0))
    )
    return RubricaNexus(int(rubrica["RubricaId"]), criterios)


def _interpretar_estudiante(e: Mapping[str, Any], codigo: str) -> EntregaNexus:
    nombre = limpiar(" ".join(str(e.get(k) or "") for k in ("ApellidoPaterno", "ApellidoMaterno", "Nombre")))
    alumno = Alumno(str(e.get("NombreUsuario") or ""), int(e["CuentaId"]), nombre)
    archivos = tuple(
        Archivo(
            _nombre_documento(n["Documento"]),
            str(n["Documento"]["URL"]),
            int(n["Documento"].get("Peso") or 0),
            fecha(n["Documento"].get("FechaCreacion")),
            bool(n.get("Extemporanea")),
        )
        for n in e.get("Entregas") or []
        if n.get("Estado") and n.get("Documento")
    )
    calificacion = (e.get("Calificacion") or {}).get("Valor")
    retros = tuple(
        RetroNexus(int(r["RetroalimentacionId"]), str(r.get("Descripcion") or ""))
        for r in e.get("Retroalimentaciones") or []
    )
    return EntregaNexus(
        alumno, codigo, archivos, None if calificacion is None else float(calificacion), retros
    )


def _nombre_documento(documento: Mapping[str, Any]) -> str:
    nombre, extension = str(documento.get("Nombre") or "archivo"), str(documento.get("Extension") or "")
    return nombre if not extension or nombre.lower().endswith(extension.lower()) else nombre + extension
