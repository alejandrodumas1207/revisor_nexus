"""Dónde se guarda el estado de la app: entregas, instrumentos, revisiones, decisiones y cargas."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from revisor.dominio.evaluacion import CriterioLista, Evaluacion
from revisor.dominio.integridad import DecisionDocente
from revisor.dominio.modelos import Curso, Elemento, EntregaNexus


@dataclass(frozen=True, slots=True)
class Instrumento:
    id: int
    version: int
    criterios: tuple[CriterioLista, ...]


@dataclass(frozen=True, slots=True)
class RevisionGuardada:
    id: int
    instrumento_id: int
    evaluacion: Evaluacion
    marca_codigo: bool | None  # firma o marcador detectado por código


class Repositorio(Protocol):
    def guardar_curso(self, curso: Curso, elementos: Sequence[Elemento]) -> None: ...

    def guardar_entregas(
        self, curso_id: int, elemento: Elemento, entregas: Sequence[EntregaNexus]
    ) -> None: ...

    def guardar_instrumento(
        self, curso_id: int, elemento_id: int, criterios: Sequence[CriterioLista]
    ) -> Instrumento:
        """Crea una versión nueva solo si los criterios cambiaron; si no, devuelve la vigente."""
        ...

    def instrumento_vigente(self, curso_id: int, elemento_id: int) -> Instrumento | None: ...

    def guardar_revision(
        self,
        curso_id: int,
        elemento_id: int,
        cuenta_id: int,
        instrumento_id: int,
        evaluacion: Evaluacion,
        marca_codigo: bool | None,
    ) -> int: ...

    def ultima_revision(self, curso_id: int, elemento_id: int, cuenta_id: int) -> RevisionGuardada | None: ...

    def guardar_decision(
        self, curso_id: int, elemento_id: int, cuenta_id: int, decision: DecisionDocente
    ) -> None: ...

    def decision(self, curso_id: int, elemento_id: int, cuenta_id: int) -> DecisionDocente: ...

    def registrar_carga(
        self, curso_id: int, elemento_id: int, cuenta_id: int, calificacion: int, retro: str, retro_id: int
    ) -> None: ...

    def ya_subida(
        self, curso_id: int, elemento_id: int, cuenta_id: int, calificacion: int, retro: str
    ) -> bool:
        """True si exactamente esta calificación y retroalimentación ya se subieron (no se repite)."""
        ...
