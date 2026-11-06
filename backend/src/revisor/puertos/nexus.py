"""Contrato para leer de NEXUS. El adaptador real usa la API; las pruebas usan uno simulado."""

from typing import Protocol

from revisor.dominio.modelos import Alumno, Curso, Elemento, EntregaNexus


class FuenteNexus(Protocol):
    def listar_cursos(self, carpeta: str | None = None) -> list[Curso]: ...

    def leer_elementos(self, curso_id: int) -> list[Elemento]: ...

    def niveles_rubrica(self, elemento: Elemento) -> list[float]:
        """Porcentaje de cada nivel de la rúbrica real del elemento, de mayor a menor."""
        ...

    def leer_alumnos(self, curso_id: int) -> list[Alumno]: ...

    def leer_entregas(self, curso_id: int, alumno: Alumno) -> list[EntregaNexus]: ...

    def descargar(self, url_relativa: str) -> bytes: ...
