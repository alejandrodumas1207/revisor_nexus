"""Comprueba que la clave de Gemini guardada funciona, sin mostrarla."""

import httpx
import keyring

SERVICIO = "revisor_nexus"
CUENTA = "gemini_api_key"
URL_MODELOS = "https://generativelanguage.googleapis.com/v1beta/models"


def main() -> None:
    clave = keyring.get_password(SERVICIO, CUENTA)
    if not clave:
        print("No hay clave guardada. Usa `just clave`.")
        return
    limpia = clave.strip()
    print(f"Guardada: {len(clave)} caracteres. Espacios sobrantes: {'sí' if limpia != clave else 'no'}.")
    if " " in limpia or limpia.count("AQ.") > 1 or limpia.count("AIza") > 1:
        print("Parece pegada dos veces o con espacios. Guárdala de nuevo con `just clave`.")
    r = httpx.get(URL_MODELOS, headers={"x-goog-api-key": limpia}, timeout=20)
    if r.status_code == 200:
        flash = [m["name"] for m in r.json().get("models", []) if "flash" in m["name"]]
        print(f"Google aceptó la clave. Modelos Flash disponibles: {len(flash)}.")
    else:
        print(f"Google rechazó la clave (HTTP {r.status_code}). Guárdala de nuevo con `just clave`.")


if __name__ == "__main__":
    main()
