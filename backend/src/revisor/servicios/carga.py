"""Subir a NEXUS la revisión validada de un alumno: calificación y retroalimentación."""

from collections.abc import Sequence
from dataclasses import dataclass

from revisor.dominio.modelos import CalificacionNexus, Elemento
from revisor.dominio.retroalimentacion import PlanRetro, RetroNexus, TipoAccion, planear_retro
from revisor.puertos.nexus import EscrituraNexus


@dataclass(frozen=True, slots=True)
class ResultadoCarga:
    plan: PlanRetro
    retro_id: int | None  # id de la retroalimentación vigente en NEXUS


def aplicar_plan_retro(
    escritura: EscrituraNexus, curso_id: int, elemento: Elemento, cuenta_id: int, plan: PlanRetro
) -> int | None:
    """Ejecuta las acciones del plan y devuelve el id de la retroalimentación que queda vigente."""
    vigente: int | None = None
    for accion in plan.acciones:
        if accion.tipo is TipoAccion.ELIMINAR:
            escritura.eliminar_retro(curso_id, elemento, accion.retro_id)
        else:
            vigente = escritura.guardar_retro(curso_id, elemento, cuenta_id, accion.texto, accion.retro_id)
    return vigente


def subir_revision(
    escritura: EscrituraNexus,
    curso_id: int,
    elemento: Elemento,
    calificacion: CalificacionNexus,
    retros_existentes: Sequence[RetroNexus],
    retro_validada: str,
    *,
    consolidar: bool = False,
) -> ResultadoCarga:
    """Guarda la calificación y deja en NEXUS la retroalimentación validada (agrega, edita o no toca)."""
    escritura.guardar_calificaciones(curso_id, elemento, [calificacion])
    plan = planear_retro(retros_existentes, retro_validada, consolidar=consolidar)
    vigente = aplicar_plan_retro(escritura, curso_id, elemento, calificacion.cuenta_id, plan)
    if vigente is None and retros_existentes:
        vigente = max(r.id for r in retros_existentes)
    return ResultadoCarga(plan, vigente)
