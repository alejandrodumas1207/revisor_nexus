"""Fase 0: registra las peticiones que NEXUS envía mientras el docente guarda una calificación a mano.

El script solo observa. No da clics, no llena campos y no guarda nada en NEXUS.
Los encabezados (incluido el Token) no se registran. La salida queda en datos_locales/, que no se versiona.

Uso: cierra nexus_tools, ejecuta `just capturar`, guarda la calificación y la retroalimentación
de un alumno en NEXUS y cierra la ventana del navegador.
"""

import json
import shutil
from datetime import datetime
from pathlib import Path

from playwright.sync_api import Request, sync_playwright

URL_NEXUS = "https://plataformanexus.uanl.mx"
URL_API = "https://api.nexus.uanl.mx/WebApi/"
DATOS_LOCALES = Path(__file__).resolve().parent.parent / "datos_locales"
# Copia del perfil de nexus_tools: abrirlo con otra versión de Chromium podría dejarlo inservible
PERFIL_ORIGEN = Path.home() / "Desktop" / "nexus_tools" / ".perfil_nexus"
PERFIL = DATOS_LOCALES / "perfil_nexus"
SALIDA = DATOS_LOCALES / "capturas"
LIMITE_CUERPO = 4000


def _es_lectura(ruta: str) -> bool:
    return "/Consultar" in ruta or ruta.startswith("Seguridad/")


def _registro(request: Request) -> dict[str, object]:
    ruta = request.url.removeprefix(URL_API)
    respuesta = request.response()
    return {
        "hora": datetime.now().isoformat(timespec="seconds"),
        "metodo": request.method,
        "ruta": ruta,
        "cuerpo": (request.post_data or "")[:LIMITE_CUERPO],
        "estado": respuesta.status if respuesta else None,
        "respuesta": (respuesta.text()[:LIMITE_CUERPO] if respuesta else ""),
    }


def _preparar_perfil() -> None:
    if PERFIL.exists() or not PERFIL_ORIGEN.exists():
        return
    print("Copiando la sesión de nexus_tools (solo la primera vez)...")
    shutil.copytree(PERFIL_ORIGEN, PERFIL, ignore=shutil.ignore_patterns("Singleton*", "*.lock", "lockfile"))


def main() -> None:
    _preparar_perfil()
    SALIDA.mkdir(parents=True, exist_ok=True)
    archivo = SALIDA / f"guardado_{datetime.now():%Y%m%d_%H%M%S}.jsonl"
    with sync_playwright() as p, archivo.open("w", encoding="utf-8") as destino:
        ctx = p.chromium.launch_persistent_context(
            str(PERFIL), headless=False, viewport={"width": 1200, "height": 900}
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        def al_terminar(request: Request) -> None:
            if not request.url.startswith(URL_API):
                return
            datos = _registro(request)
            destino.write(json.dumps(datos, ensure_ascii=False) + "\n")
            destino.flush()
            if not _es_lectura(str(datos["ruta"])):
                print(f"ESCRITURA {datos['metodo']} {datos['ruta']} -> {datos['estado']}")

        page.on("requestfinished", al_terminar)
        page.goto(f"{URL_NEXUS}/#/App/UnidadesAprendizaje")
        print("Entra a NEXUS si te lo pide, guarda una calificación y su retroalimentación.")
        print("Al terminar, cierra la ventana del navegador.")
        page.wait_for_event("close", timeout=0)
    print(f"Captura guardada en {archivo}")


if __name__ == "__main__":
    main()
