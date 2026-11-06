"""Contrato para leer de NEXUS. El adaptador real usa la API; las pruebas usan uno simulado."""

from collections.abc import Sequence
from typing import Protocol

from revisor.dominio.modelos import Alumno, CalificacionNexus, Curso, Elemento, EntregaNexus


class FuenteNexus(Protocol):
    def listar_cursos(self, carpeta: str | None = None) -> list[Curso]: ...

    def leer_elementos(self, curso_id: int) -> list[Elemento]: ...

    def niveles_rubrica(self, elemento: Elemento) -> list[float]:
        """Porcentaje de cada nivel de la rúbrica real del elemento, de mayor a menor."""
        ...

    def leer_alumnos(self, curso_id: int) -> list[Alumno]: ...

    def leer_entregas(self, curso_id: int, alumno: Alumno) -> list[EntregaNexus]: ...

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
