"""Contrato con un proveedor de IA. El adaptador real usa Gemini; las pruebas usan uno simulado."""

from typing import Any, Protocol


class ProveedorIA(Protocol):
    @property
    def modelo(self) -> str: ...

    def generar_json(self, instrucciones: str, contenido: str, esquema: dict[str, Any]) -> dict[str, Any]:
        """Devuelve la respuesta del modelo como JSON que respeta `esquema`."""
        ...
