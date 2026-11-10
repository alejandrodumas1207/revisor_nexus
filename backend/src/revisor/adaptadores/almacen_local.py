"""Almacén en disco: la carpeta Entregas de cada curso, con la misma convención que nexus_tools."""

import threading
import zipfile
from pathlib import Path, PurePath


class RutaFueraDelAlmacen(ValueError):
    """Una ruta intentó salir de la carpeta base (por ejemplo con '..')."""


class AlmacenLocal:
    def __init__(self, base: Path) -> None:
        self._base = base.resolve()
        self._carpetas = threading.Lock()  # en Windows, crear la misma carpeta desde dos hilos falla

    def existe(self, ruta: PurePath, peso: int) -> bool:
        destino = self._resolver(ruta)
        return destino.is_file() and destino.stat().st_size == peso

    def guardar(self, ruta: PurePath, contenido: bytes) -> None:
        destino = self._resolver(ruta)
        with self._carpetas:
            destino.parent.mkdir(parents=True, exist_ok=True)
        temporal = destino.with_name(destino.name + ".parcial")
        temporal.write_bytes(contenido)
        temporal.replace(destino)  # nunca queda un archivo a medias con el nombre final
        if destino.suffix.lower() == ".zip":
            self._descomprimir(destino)

    def leer(self, ruta: PurePath) -> bytes:
        return self._resolver(ruta).read_bytes()

    def archivos_de(self, carpeta: PurePath, matricula: str) -> list[PurePath]:
        base = self._resolver(carpeta)
        if not base.is_dir():
            return []
        archivos: list[PurePath] = []
        for p in sorted(base.iterdir()):
            if not p.name.startswith(f"{matricula}_") or p.name.endswith(".parcial"):
                continue
            if p.is_dir():
                archivos += [x.relative_to(self._base) for x in sorted(p.rglob("*")) if x.is_file()]
            elif p.suffix.lower() != ".zip" or not p.with_suffix("").is_dir():
                archivos.append(p.relative_to(self._base))
        return archivos

    def _resolver(self, ruta: PurePath) -> Path:
        # Sin resolve(): en Windows cambia según exista o no la carpeta y falla con hilos simultáneos
        if ruta.is_absolute() or ruta.anchor or ".." in ruta.parts:
            raise RutaFueraDelAlmacen(str(ruta))
        return self._base / ruta

    def _descomprimir(self, archivo: Path) -> None:
        carpeta = archivo.with_suffix("")
        try:
            with zipfile.ZipFile(archivo) as z:
                for miembro in z.namelist():
                    if not (carpeta / miembro).resolve().is_relative_to(carpeta.resolve()):
                        return  # zip con rutas que escapan de su carpeta: no se extrae
                z.extractall(carpeta)
        except zipfile.BadZipFile:
            return
