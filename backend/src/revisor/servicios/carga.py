"""Subir a NEXUS la revisión validada de un alumno: calificación y retroalimentación final."""

from collections.abc import Sequence
from dataclasses import dataclass

from revisor.dominio.modelos import CalificacionNexus, Elemento
from revisor.dominio.retroalimentacion import (
    AccionRetro,
    RetroNexus,
    TipoAccion,
    planear_retro,
    validar_borrado,
)
from revisor.puertos.nexus import EscrituraNexus


@dataclass(frozen=True, slots=True)
class ResultadoCarga:
    accion: AccionRetro
    retro_id: int  # id de la retroalimentación vigente en NEXUS


def subir_revision(
    escritura: EscrituraNexus,
    curso_id: int,
    elemento: Elemento,
    calificacion: CalificacionNexus,
    retros_existentes: Sequence[RetroNexus],
    retro_final: str,
) -> ResultadoCarga:
    """Guarda la calificación y deja en NEXUS la retroalimentación final (la agrega, la edita o no la toca).

    La retroalimentación se revisa antes de escribir nada: si hay más de una, no se sube ni la calificación.
    """
    accion = planear_retro(retros_existentes, retro_final)
    escritura.guardar_calificaciones(curso_id, elemento, [calificacion])
    if accion.tipo is TipoAccion.NINGUNA:
        return ResultadoCarga(accion, accion.retro_id)
    retro_id = escritura.guardar_retro(
        curso_id, elemento, calificacion.cuenta_id, accion.texto, accion.retro_id
    )
    return ResultadoCarga(accion, retro_id)


def borrar_retro_elegida(
    escritura: EscrituraNexus,
    curso_id: int,
    elemento: Elemento,
    retros_existentes: Sequence[RetroNexus],
    retro_id: int,
) -> None:
    """Borra la retroalimentación que el docente eligió cuando el alumno tenía más de una."""
    validar_borrado(retros_existentes, retro_id)
    escritura.eliminar_retro(curso_id, elemento, retro_id)
