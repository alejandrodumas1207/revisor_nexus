"""Cliente HTTP de la API de NEXUS con los encabezados de la sesión del docente.

NEXUS siempre contesta HTTP 200; los errores vienen en el cuerpo ({"Code", "Message"}).
Las respuestas traen un Token renovado en "Sesion": se usa en las siguientes peticiones y nunca se registra.
"""

from collections.abc import Mapping
from typing import Any
from urllib.parse import quote

import httpx

URL_API = "https://api.nexus.uanl.mx/WebApi/"
URL_WEB = "https://plataformanexus.uanl.mx"
CODIGO_SESION_VENCIDA = 2011
TIEMPO_DESCARGA = 15 * 60  # videos pesados


class ErrorNexus(RuntimeError):
    """NEXUS respondió con un error en el cuerpo."""


class SesionVencida(ErrorNexus):
    """La sesión ya no existe; hay que volver a entrar."""


class ClienteHttpNexus:
    def __init__(self, encabezados: Mapping[str, str], http: httpx.Client | None = None) -> None:
        self._encabezados = dict(encabezados)
        self._http = http or httpx.Client(timeout=60)

    def post_json(self, ruta: str, cuerpo: Mapping[str, Any]) -> dict[str, Any]:
        respuesta = self._http.post(URL_API + ruta, json=dict(cuerpo), headers=self._encabezados_json())
        return self._procesar(respuesta)

    def post_form(self, ruta: str, campos: Mapping[str, str]) -> dict[str, Any]:
        # (None, valor) obliga a httpx a mandar multipart/form-data, como la web de NEXUS
        partes = {k: (None, v) for k, v in campos.items()}
        respuesta = self._http.post(URL_API + ruta, files=partes, headers=self._encabezados_base())
        return self._procesar(respuesta)

    def descargar(self, url_relativa: str) -> bytes:
        url = f"{URL_WEB}/{quote(url_relativa)}"
        respuesta = self._http.get(url, headers=self._encabezados_base(), timeout=TIEMPO_DESCARGA)
        respuesta.raise_for_status()
        return respuesta.content

    def _encabezados_base(self) -> dict[str, str]:
        return {k: v for k, v in self._encabezados.items() if k.lower() != "content-type"}

    def _encabezados_json(self) -> dict[str, str]:
        return {**self._encabezados_base(), "Content-Type": "application/json", "Accept": "application/json"}

    def _procesar(self, respuesta: httpx.Response) -> dict[str, Any]:
        respuesta.raise_for_status()
        datos: dict[str, Any] = respuesta.json()
        if "Code" in datos and "Message" in datos:
            if datos["Code"] == CODIGO_SESION_VENCIDA:
                raise SesionVencida("La sesión de NEXUS venció; hay que volver a entrar.")
            raise ErrorNexus(f"NEXUS respondió {datos['Code']}: {datos['Message']}")
        sesion = datos.get("Sesion")
        if isinstance(sesion, dict) and sesion.get("Token"):
            self._encabezados["Token"] = str(sesion["Token"])  # pyright: ignore[reportUnknownArgumentType]
        return datos
