"""Convención de carpetas de entregas, compatible con nexus_tools."""

import re
from pathlib import PurePath

_DIMENSION = re.compile(r"dimensi[oó]n\s*(\d+)", re.IGNORECASE)
_PROHIBIDOS = re.compile(r'[<>:"/\\|?*]')


def carpeta_elemento(codigo: str, nombre: str = "") -> PurePath:
    """Ruta relativa dentro de Entregas: Etapa 1/Dimensión 2, Etapa 1/Evidencia de Aprendizaje o PIA."""
    if codigo == "PIA":
        return PurePath("PIA")
    etapa, posicion = codigo.split(".")
    dimension = _DIMENSION.search(nombre)
    if dimension:
        final = f"Dimensión {dimension.group(1)}"
    elif nombre.strip().lower().startswith("evidencia"):
        final = "Evidencia de Aprendizaje"
    else:
        final = f"Elemento {posicion}"
    return PurePath(f"Etapa {etapa}") / final


def nombre_seguro(texto: str) -> str:
    """Quita los caracteres que Windows no acepta en nombres de archivo."""
    return _PROHIBIDOS.sub("", texto).strip()


def nombre_archivo_entrega(matricula: str, nombre: str, extension: str, indice: int = 0) -> str:
    """{matrícula}_{NOMBRE}{ext}, con sufijo _k cuando el alumno subió varios archivos."""
    sufijo = f"_{indice}" if indice else ""
    return nombre_seguro(f"{matricula}_{nombre.upper()}{sufijo}{extension.lower()}")
