"""Revisión del formato de entrega: tipo de archivo y nombre según la convención pedida."""

import re
from dataclasses import dataclass
from pathlib import PurePath

# Google Forms renombra "archivo.ext" como "archivo - Nombre del alumno.ext"
_SUFIJO_FORMS = re.compile(r" - [^/\\]+?(\.[A-Za-z0-9]+)$")
_MATRICULA = re.compile(r"(?<!\d)(\d{7})(?!\d)")


@dataclass(frozen=True, slots=True)
class RevisionFormato:
    nombre_original: str
    extension: str
    matricula_en_nombre: str
    observaciones: tuple[str, ...]

    @property
    def correcto(self) -> bool:
        return not self.observaciones


def nombre_antes_de_forms(nombre: str) -> str:
    """Quita el " - Nombre" que Google Forms agrega al final del archivo."""
    return _SUFIJO_FORMS.sub(r"\1", nombre)


def revisar_formato(nombre_archivo: str, prefijo: str, extension: str = ".ipynb") -> RevisionFormato:
    """Compara el nombre entregado con la convención `{prefijo}..._{matrícula}_{Apellido}{extension}`."""
    original = nombre_antes_de_forms(nombre_archivo)
    ruta = PurePath(original)
    ext = "".join(ruta.suffixes[-2:]) if ruta.suffix == ".txt" else ruta.suffix
    matricula = _primera_matricula(original)
    observaciones: list[str] = []
    if ext.lower() != extension:
        observaciones.append(f"Entregó {ext or 'sin extensión'} en lugar de {extension}.")
    if not original.upper().startswith(prefijo.upper()):
        observaciones.append(f"El nombre no inicia con {prefijo}.")
    if not matricula:
        observaciones.append("El nombre no incluye la matrícula.")
    return RevisionFormato(original, ext, matricula, tuple(observaciones))


def _primera_matricula(texto: str) -> str:
    m = _MATRICULA.search(texto)
    return m.group(1) if m else ""
