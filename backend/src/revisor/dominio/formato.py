"""Revisión del formato de entrega.

Se penaliza el tipo de archivo (debe ser el pedido, por ejemplo .ipynb y no .txt, .pdf o .zip).
El nombre del archivo no se penaliza: si no sigue la convención, solo se avisa en la retroalimentación.
"""

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
    penalizables: tuple[str, ...]  # descuentan en el criterio de formato
    avisos: tuple[str, ...]  # solo van a la retroalimentación

    @property
    def correcto(self) -> bool:
        return not self.penalizables


def nombre_antes_de_forms(nombre: str) -> str:
    """Quita el " - Nombre" que Google Forms agrega al final del archivo."""
    return _SUFIJO_FORMS.sub(r"\1", nombre)


def revisar_formato(nombre_archivo: str, prefijo: str, extension: str = ".ipynb") -> RevisionFormato:
    """Compara el archivo entregado con el tipo pedido y con la convención `{prefijo}..._{matrícula}...`."""
    original = nombre_antes_de_forms(nombre_archivo)
    ruta = PurePath(original)
    ext = "".join(ruta.suffixes[-2:]) if ruta.suffix == ".txt" else ruta.suffix
    matricula = _primera_matricula(original)
    penalizables: list[str] = []
    if ext.lower() != extension:
        penalizables.append(f"Entregó {ext or 'sin extensión'} en lugar de {extension}.")
    avisos: list[str] = []
    if not original.upper().startswith(prefijo.upper()):
        avisos.append(f"El nombre del archivo debe iniciar con {prefijo}.")
    if not matricula:
        avisos.append("El nombre del archivo debe incluir tu matrícula.")
    return RevisionFormato(original, ext, matricula, tuple(penalizables), tuple(avisos))


def _primera_matricula(texto: str) -> str:
    m = _MATRICULA.search(texto)
    return m.group(1) if m else ""
