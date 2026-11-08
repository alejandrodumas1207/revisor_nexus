"""Contrato para leer de NEXUS. El adaptador real usa la API; las pruebas usan uno simulado."""

from collections.abc import Sequence
from typing import Protocol

from revisor.dominio.modelos import CalificacionNexus, Curso, Elemento, EntregaNexus, RubricaNexus


class FuenteNexus(Protocol):
    def listar_cursos(self, carpeta: str | None = None) -> list[Curso]:
        """Cursos de un periodo (por nombre de carpeta); sin carpeta, el periodo más reciente."""
        ...

    def leer_elementos(self, curso_id: int) -> list[Elemento]: ...

    def leer_rubrica(self, elemento: Elemento) -> RubricaNexus | None: ...

    def leer_entregas(self, curso_id: int, elemento: Elemento) -> list[EntregaNexus]:
        """Todo el grupo en una sola consulta: archivos, calificación y retroalimentaciones."""
        ...

    def descargar(self, url_relativa: str) -> bytes: ...


class EscrituraNexus(Protocol):
    """Escribe en NEXUS. Solo se usa con calificaciones y retroalimentaciones validadas por el docente."""

    def guardar_calificaciones(
        self, curso_id: int, elemento: Elemento, calificaciones: Sequence[CalificacionNexus]
    ) -> None: ...

    def guardar_retro(
        self, curso_id: int, elemento: Elemento, cuenta_id: int, texto: str, retro_id: int = 0
    ) -> int:
        """Agrega (retro_id 0) o edita una retroalimentación. Devuelve su id."""
        ...

    def eliminar_retro(self, curso_id: int, elemento: Elemento, retro_id: int) -> None:
        """Solo por elección explícita del docente."""
        ...
