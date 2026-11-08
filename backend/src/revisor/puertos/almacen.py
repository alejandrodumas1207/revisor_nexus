"""Dónde quedan los archivos descargados. El adaptador real usa la carpeta del curso en disco."""

from pathlib import PurePath
from typing import Protocol


class AlmacenArchivos(Protocol):
    def existe(self, ruta: PurePath, peso: int) -> bool:
        """True si ya está descargado con el mismo tamaño (no se vuelve a bajar)."""
        ...

    def guardar(self, ruta: PurePath, contenido: bytes) -> None: ...
