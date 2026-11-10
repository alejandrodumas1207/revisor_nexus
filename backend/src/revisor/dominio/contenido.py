"""Lo que se le muestra a la IA de una entrega: texto y, si hace falta, imágenes de sus páginas."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ImagenPagina:
    origen: str  # archivo del que sale
    numero: int  # página, diapositiva o imagen dentro del archivo
    jpeg: bytes


@dataclass(frozen=True, slots=True)
class ContenidoEntrega:
    texto: str
    imagenes: tuple[ImagenPagina, ...] = ()
    avisos: tuple[str, ...] = ()  # archivos que no se pudieron leer (video, audio, dañados)
    cifras_faltantes: dict[str, tuple[str, ...]] | None = (
        None  # solo notebooks: cifras que no salen de sus salidas
    )

    @property
    def vacio(self) -> bool:
        return not self.texto.strip() and not self.imagenes


def unir(contenidos: list[ContenidoEntrega], limite_imagenes: int) -> ContenidoEntrega:
    """Junta los archivos de un alumno en un solo contenido, sin pasar del límite de imágenes."""
    texto = "\n\n".join(c.texto for c in contenidos if c.texto.strip())
    imagenes = tuple(i for c in contenidos for i in c.imagenes)
    avisos = [a for c in contenidos for a in c.avisos]
    cifras = {
        k: v for c in contenidos if c.cifras_faltantes is not None for k, v in c.cifras_faltantes.items()
    }
    hay_notebook = any(c.cifras_faltantes is not None for c in contenidos)
    if len(imagenes) > limite_imagenes:
        avisos.append(f"Se enviaron {limite_imagenes} de {len(imagenes)} imágenes a la revisión.")
        imagenes = imagenes[:limite_imagenes]
    return ContenidoEntrega(texto, imagenes, tuple(avisos), cifras if hay_notebook else None)
