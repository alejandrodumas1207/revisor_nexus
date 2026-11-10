"""Reparte las revisiones entre modelos gratuitos: si uno agota su cuota diaria, sigue el siguiente."""

from collections.abc import Sequence
from typing import Any

from revisor.puertos.ia import CuotaAgotada, ModeloNoDisponible, ProveedorIA


class ProveedorRotativo:
    def __init__(self, proveedores: Sequence[ProveedorIA]) -> None:
        if not proveedores:
            raise ValueError("Se necesita al menos un proveedor.")
        self._proveedores = list(proveedores)
        self._agotados: set[int] = set()
        self._ultimo = 0

    @property
    def modelo(self) -> str:
        return self._proveedores[self._ultimo].modelo

    @property
    def disponibles(self) -> list[str]:
        return [p.modelo for i, p in enumerate(self._proveedores) if i not in self._agotados]

    def generar_json(
        self, instrucciones: str, contenido: str, esquema: dict[str, Any], imagenes: Sequence[bytes] = ()
    ) -> dict[str, Any]:
        for i, proveedor in enumerate(self._proveedores):
            if i in self._agotados:
                continue
            try:
                respuesta = proveedor.generar_json(instrucciones, contenido, esquema, imagenes)
            except (CuotaAgotada, ModeloNoDisponible):
                self._agotados.add(i)
                continue
            self._ultimo = i
            return respuesta
        raise CuotaAgotada("Ningún modelo gratuito tiene cuota disponible hoy.")
