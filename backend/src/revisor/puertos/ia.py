"""Contrato con un proveedor de IA. El adaptador real usa Gemini; las pruebas usan uno simulado."""

from typing import Any, Protocol


class IANoDisponible(RuntimeError):
    """El proveedor no está configurado o no respondió tras los reintentos."""


class CuotaAgotada(IANoDisponible):
    """Se acabó la cuota gratuita del día; la entrega pasa a otro modelo o a revisión con Claude."""


class ModeloNoDisponible(IANoDisponible):
    """El modelo no existe o no está habilitado para el proyecto; se salta en la rotación."""


class ProveedorIA(Protocol):
    @property
    def modelo(self) -> str:
        """Modelo que generó la última respuesta (queda en la procedencia)."""
        ...

    def generar_json(self, instrucciones: str, contenido: str, esquema: dict[str, Any]) -> dict[str, Any]:
        """Devuelve la respuesta del modelo como JSON que respeta `esquema`."""
        ...
