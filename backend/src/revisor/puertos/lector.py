"""Lee las entregas: contenido para la IA y señal de firma o marcador del profesor."""

from typing import Protocol

from revisor.dominio.contenido import ContenidoEntrega


class LectorEntregas(Protocol):
    def extraer(self, nombre: str, datos: bytes) -> ContenidoEntrega: ...

    def marca_revision(self, nombre: str, datos: bytes) -> bool | None:
        """True/False si el archivo se pudo analizar; None si no aplica (video, notebook, dañado)."""
        ...
