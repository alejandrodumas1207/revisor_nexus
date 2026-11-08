"""Traduce una calificación (ya válida en NEXUS) a los niveles que hay que marcar en su rúbrica (ADR 0004).

Los descriptores de la rúbrica de NEXUS no se usan: solo su número de criterios y sus porcentajes.
"""

from revisor.dominio.calificacion import calificaciones_validas, combinacion_rubrica
from revisor.dominio.modelos import NivelRubricaNexus, RubricaNexus


class CalificacionNoRegistrable(ValueError):
    """La calificación no se puede registrar exactamente con esta rúbrica."""


def niveles_para_calificacion(rubrica: RubricaNexus, cal10: int) -> tuple[NivelRubricaNexus, ...]:
    """Un nivel por criterio cuyo promedio da exactamente `cal10` × 10."""
    criterios, porcentajes = len(rubrica.criterios), rubrica.porcentajes
    if cal10 not in calificaciones_validas(criterios, porcentajes):
        raise CalificacionNoRegistrable(f"{cal10} no se puede registrar con esta rúbrica; ajústala antes.")
    combo = combinacion_rubrica(cal10, criterios, porcentajes)
    if combo is None:
        raise CalificacionNoRegistrable(f"No hay combinación de niveles para {cal10}.")
    return tuple(
        NivelRubricaNexus(
            rubrica.rubrica_id,
            criterio.criterio_id,
            criterio.opciones[indice].nivel_dominio_id,
            criterio.opciones[indice].criterio_nivel_dominio_id,
        )
        for criterio, indice in zip(rubrica.criterios, combo.niveles, strict=True)
    )
