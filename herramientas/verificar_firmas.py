"""Compara el detector de firmas portado con el original de nexus_tools sobre entregas reales.

Uso local (usa datos de alumnos; no corre en CI): uv run python ../herramientas/verificar_firmas.py [N]
"""

import random
import sys
from pathlib import Path

from revisor.adaptadores.extractores.firmas import detectar_marca, paginas_de

sys.path.insert(0, str(Path.home() / "Desktop" / "nexus_tools"))
from nexus_lib import firmas as original  # pyright: ignore[reportMissingImports]

BASE = Path.home() / "Desktop" / "NEXUS"


def main() -> None:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    archivos = [p for p in BASE.rglob("*") if p.suffix.lower() in {".pdf", ".jpg", ".jpeg", ".png"}]
    muestra = random.Random(1).sample(archivos, min(n, len(archivos)))  # noqa: S311 — muestreo, no criptografía
    iguales = 0
    for p in muestra:
        viejo = original.analizar_archivo(p)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
        nuevo = detectar_marca(list(paginas_de(p.name, p.read_bytes())))
        if viejo["pagina"] == nuevo.pagina:
            iguales += 1
        else:
            print(f"DIFERENTE {p.name}: original {viejo['pagina']}, nuevo {nuevo.pagina}")
    print(f"{iguales}/{len(muestra)} iguales")


if __name__ == "__main__":
    main()
