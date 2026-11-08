"""Abre NEXUS en Chromium con el perfil guardado y obtiene los encabezados de la sesión del docente.

Si la sesión venció, entra con las credenciales guardadas en el administrador de credenciales de Windows,
UNA sola vez (repetir una contraseña mala puede bloquear la cuenta). Si no hay credenciales o fallan,
espera a que el docente entre a mano. Después de esto todo se hace por API, sin navegador.
Portado de nexus_tools/nexus_lib/sesion.py.
"""

import re
from pathlib import Path

import keyring
from playwright.sync_api import Page, Request, sync_playwright

from revisor.adaptadores.nexus_api.cliente import URL_API, URL_WEB, ClienteHttpNexus, ErrorNexus

ESPERA_MAXIMA = 600  # segundos para que el docente entre a mano
_SERVICIOS_CREDENCIALES = ("revisor_nexus", "nexus_tools")  # nexus_tools ya las tiene guardadas


def credenciales() -> tuple[str, str] | None:
    for servicio in _SERVICIOS_CREDENCIALES:
        usuario = keyring.get_password(servicio, "usuario")
        contrasena = keyring.get_password(servicio, "contrasena")
        if usuario and contrasena:
            return usuario, contrasena
    return None


def sesion_viva(encabezados: dict[str, str]) -> bool:
    try:
        cuerpo = {"CarpetaId": 0, "Pagina": 1, "Paginacion": 5}
        return bool(
            ClienteHttpNexus(encabezados).post_json("Curso/ConsultarCarpetaCursos", cuerpo).get("Carpetas")
        )
    except (ErrorNexus, OSError, ValueError):
        return False


def abrir_sesion(perfil: Path) -> dict[str, str]:
    capturados: dict[str, str] = {}

    def capturar(request: Request) -> None:
        if not request.url.startswith(URL_API) or "Seguridad/" in request.url:
            return
        h = request.headers
        if h.get("token") and h.get("rolid"):
            capturados.update(
                {
                    "Token": h["token"],
                    "AreaAcademicaId": h.get("areaacademicaid", ""),
                    "RolId": h["rolid"],
                    "SistemaId": h.get("sistemaid", ""),
                }
            )

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(perfil), headless=False, no_viewport=True, args=["--start-maximized"]
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.on("request", capturar)
        try:
            page.goto(f"{URL_WEB}/#/App/UnidadesAprendizaje")
            _esperar_login(page, capturados)
        finally:
            ctx.close()
    return dict(capturados)


def _esperar_login(page: Page, capturados: dict[str, str]) -> None:
    intentado, en_login = False, False
    for _ in range(ESPERA_MAXIMA):
        page.wait_for_timeout(1000)
        if capturados and sesion_viva(capturados):
            return
        capturados.clear()  # eran encabezados de una sesión vencida
        if not en_login and page.locator("input[name=usuario]").count() == 0:
            page.goto(f"{URL_WEB}/#/Login")
            en_login = True
            continue
        en_login = True
        datos = credenciales()
        if datos and not intentado and page.locator("input[name=usuario]").count():
            intentado = True
            page.fill("input[name=usuario]", datos[0])
            page.fill("input[name=password]", datos[1])
            page.locator("button[type=submit]").first.click()
        _confirmar_sesion_activa(page)
    raise RuntimeError("No se detectó el inicio de sesión en NEXUS.")


def _confirmar_sesion_activa(page: Page) -> None:
    """NEXUS pregunta si se cierra la otra sesión abierta; se acepta para continuar."""
    dialogo = page.locator("mat-dialog-container").filter(has_text="sesión activa")
    if dialogo.count():
        dialogo.first.locator("button", has_text=re.compile("continuar", re.IGNORECASE)).first.click()
