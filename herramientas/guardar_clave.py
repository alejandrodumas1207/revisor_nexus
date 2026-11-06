"""Guarda la clave de Gemini en el administrador de credenciales de Windows.

La clave se escribe oculta y nunca se muestra ni se guarda en archivos.
"""

import getpass

import keyring

SERVICIO = "revisor_nexus"
CUENTA = "gemini_api_key"


def main() -> None:
    print("Pega la clave con clic derecho o Ctrl+V y presiona Enter. No se verá al pegarla.")
    clave = getpass.getpass("Clave: ").strip()
    if not clave:
        print("No se guardó nada: la clave llegó vacía.")
        return
    keyring.set_password(SERVICIO, CUENTA, clave)
    print(f"Clave guardada ({len(clave)} caracteres).")


if __name__ == "__main__":
    main()
