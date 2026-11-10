"""Gemini (nivel gratuito) como proveedor de IA. La clave sale del administrador de credenciales."""

import json
import time
from collections.abc import Sequence
from typing import Any

import keyring
from google import genai
from google.genai import errors, types

from revisor.puertos.ia import CuotaAgotada, IANoDisponible, ModeloNoDisponible

SERVICIO, CUENTA = "revisor_nexus", "gemini_api_key"
MODELO_POR_DEFECTO = "gemini-3.5-flash"
# Modelos gratuitos con cuota diaria propia (sin Lite). "gemini-3.5-flash" se cobra a la cuota de 3.6.
MODELOS_ROTACION = ("gemini-3.5-flash", "gemini-3.7-flash", "gemini-3.8-flash")
_REINTENTABLES = {429, 500, 503}  # cuota por minuto agotada o servicio saturado


class ProveedorGemini:
    def __init__(
        self, modelo: str = MODELO_POR_DEFECTO, reintentos: int = 4, espera_base: float = 15.0
    ) -> None:
        clave = keyring.get_password(SERVICIO, CUENTA)
        if not clave:
            raise IANoDisponible("No hay clave de Gemini guardada. Usa `just clave`.")
        self._cliente = genai.Client(api_key=clave)
        self._modelo = modelo
        self._reintentos = reintentos
        self._espera_base = espera_base

    @property
    def modelo(self) -> str:
        return self._modelo

    def generar_json(
        self, instrucciones: str, contenido: str, esquema: dict[str, Any], imagenes: Sequence[bytes] = ()
    ) -> dict[str, Any]:
        config = types.GenerateContentConfig(
            system_instruction=instrucciones,
            response_mime_type="application/json",
            response_json_schema=esquema,
            temperature=0.2,
        )
        for intento in range(self._reintentos + 1):
            try:
                partes = [
                    contenido,
                    *(types.Part.from_bytes(data=i, mime_type="image/jpeg") for i in imagenes),
                ]
                respuesta = self._cliente.models.generate_content(
                    model=self._modelo, contents=partes, config=config
                )
                return json.loads(respuesta.text or "{}")
            except errors.APIError as e:
                if e.code == 404:
                    raise ModeloNoDisponible(f"{self._modelo} no está disponible para este proyecto.") from e
                if e.code == 429 and "PerDay" in str(e):
                    raise CuotaAgotada(f"Se agotó la cuota diaria de {self._modelo}.") from e
                if e.code not in _REINTENTABLES or intento == self._reintentos:
                    raise IANoDisponible(f"{self._modelo} respondió {e.code}: {str(e)[:200]}") from e
                time.sleep(self._espera_base * (2**intento))
        raise IANoDisponible(f"{self._modelo} no respondió.")
