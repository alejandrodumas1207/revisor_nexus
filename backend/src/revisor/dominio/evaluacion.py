"""Evaluación de una entrega con la lista de cotejo, como la propone una IA y luego la valida el docente."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from revisor.dominio.modelos import Origen

NIVELES = ("cumple", "parcial", "no_cumple")


@dataclass(frozen=True, slots=True)
class CriterioLista:
    id: str
    nombre: str
    puntos: float
    cumple: str
    parcial: str
    no_cumple: str


@dataclass(frozen=True, slots=True)
class EvaluacionCriterio:
    nivel: str
    evidencia: str  # para el docente: qué se vio y dónde
    comentario: str  # para el alumno: lo que está bien y lo que falta


@dataclass(frozen=True, slots=True)
class Evaluacion:
    criterios: dict[str, EvaluacionCriterio]
    comentarios_generales: str
    alertas: tuple[str, ...]
    origen: Origen
    modelo: str
    version_prompt: str
    marca_revision: bool | None = None  # ¿la IA vio firma o marcador del profesor? None = no aplica
    detalle_marca: str = ""


class EvaluacionInvalida(ValueError):
    """La respuesta de la IA no respeta la lista de cotejo; no se acepta."""


def evaluacion_desde_datos(
    datos: Mapping[str, Any], lista: Sequence[CriterioLista], origen: Origen, modelo: str, version_prompt: str
) -> Evaluacion:
    """Valida la respuesta (todos los criterios, niveles conocidos) y la convierte en una Evaluacion."""
    por_id = {str(c.get("id")): c for c in datos.get("criterios", [])}
    faltantes = [c.id for c in lista if c.id not in por_id]
    if faltantes:
        raise EvaluacionInvalida(f"Faltan criterios en la respuesta: {faltantes}")
    criterios: dict[str, EvaluacionCriterio] = {}
    for c in lista:
        bruto = por_id[c.id]
        nivel = str(bruto.get("nivel", ""))
        if nivel not in NIVELES:
            raise EvaluacionInvalida(f"Nivel desconocido en {c.id}: {nivel!r}")
        criterios[c.id] = EvaluacionCriterio(
            nivel, str(bruto.get("evidencia", "")), str(bruto.get("comentario", ""))
        )
    alertas = tuple(str(a) for a in datos.get("alertas", []) if str(a).strip())
    generales = str(datos.get("comentarios_generales") or "")
    marca: Mapping[str, Any] = datos.get("marca_revision") or {}
    hay: object = marca.get("hay")
    detalle = str(marca.get("detalle") or "")
    return Evaluacion(
        criterios,
        generales,
        alertas,
        origen,
        modelo,
        version_prompt,
        hay if isinstance(hay, bool) else None,
        detalle,
    )
