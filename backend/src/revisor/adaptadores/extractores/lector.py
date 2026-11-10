"""Lector de entregas: extractores de documentos y detector de firma o marcador juntos."""

from revisor.adaptadores.extractores.documentos import extraer
from revisor.adaptadores.extractores.firmas import detectar_marca, paginas_de
from revisor.dominio.contenido import ContenidoEntrega


class LectorArchivos:
    def extraer(self, nombre: str, datos: bytes) -> ContenidoEntrega:
        return extraer(nombre, datos)

    def marca_revision(self, nombre: str, datos: bytes) -> bool | None:
        try:
            paginas = list(paginas_de(nombre, datos))
        except Exception:
            return None
        if not paginas:
            return None
        return detectar_marca(paginas).encontrada
