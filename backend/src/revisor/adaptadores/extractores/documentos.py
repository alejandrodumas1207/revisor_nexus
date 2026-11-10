"""Extrae texto e imágenes de cualquier entrega: PDF, imagen, Word, PowerPoint o notebook.

- PDF: texto de cada página; se manda imagen de las páginas con poco texto (escaneos, escritura a mano,
  diagramas), que es donde la IA necesita ver.
- Imagen: se reduce y se manda tal cual (fotos de libreta, mapas conceptuales).
- Word y PowerPoint: texto de párrafos o diapositivas e imágenes incrustadas.
- Video y audio: no se analizan; quedan como aviso para revisión manual.
"""

import io
import re
import zipfile
from pathlib import PurePath

import cv2
import defusedxml.ElementTree as xml_seguro
import numpy as np
import pypdfium2 as pdfium

from revisor.adaptadores.extractores.notebook import NotebookInvalido, texto_para_ia
from revisor.dominio.contenido import ContenidoEntrega, ImagenPagina

IMAGENES = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}
MULTIMEDIA = {".mp4", ".mov", ".avi", ".mkv", ".m4a", ".mp3", ".wav", ".ogg", ".opus"}
MAX_PAGINAS = 12
LADO_IMAGEN = 1600  # lado largo de cada imagen enviada: legible y sin gastar de más
CALIDAD_JPEG = 80
TEXTO_MINIMO_PAGINA = 200  # menos caracteres que esto: la página se manda como imagen
_TEXTO_XML = re.compile(r"\}t$")  # etiquetas <w:t> (Word) y <a:t> (PowerPoint)


def extraer(nombre: str, datos: bytes) -> ContenidoEntrega:
    extension = PurePath(nombre).suffix.lower()
    try:
        if extension in {".ipynb", ".txt"}:
            return _notebook(nombre, datos)
        if extension == ".pdf":
            return _pdf(nombre, datos)
        if extension in IMAGENES:
            return _imagen(nombre, datos)
        if extension in {".docx", ".pptx"}:
            return _office(nombre, datos, extension)
    except Exception as e:
        return ContenidoEntrega("", (), (f"{nombre}: no se pudo leer ({type(e).__name__}).",))
    if extension in MULTIMEDIA:
        return ContenidoEntrega("", (), (f"{nombre}: video o audio, requiere revisión manual.",))
    return ContenidoEntrega(
        "", (), (f"{nombre}: tipo de archivo {extension or 'desconocido'} no soportado.",)
    )


def jpeg(imagen: np.ndarray, lado: int = LADO_IMAGEN) -> bytes:
    """Reduce (sin agrandar) y comprime una imagen BGR a JPEG."""
    escala = lado / max(imagen.shape[:2])
    if escala < 1:
        imagen = cv2.resize(imagen, None, fx=escala, fy=escala, interpolation=cv2.INTER_AREA)
    ok, buffer = cv2.imencode(".jpg", imagen, [cv2.IMWRITE_JPEG_QUALITY, CALIDAD_JPEG])
    if not ok:
        raise ValueError("No se pudo comprimir la imagen.")
    return buffer.tobytes()


def decodificar(datos: bytes) -> np.ndarray | None:
    return cv2.imdecode(np.frombuffer(datos, np.uint8), cv2.IMREAD_COLOR)


def paginas_pdf(datos: bytes, lado: int = LADO_IMAGEN) -> list[tuple[int, str, np.ndarray]]:
    """(número, texto, imagen BGR) de cada página, hasta MAX_PAGINAS."""
    documento = pdfium.PdfDocument(datos)
    try:
        resultado: list[tuple[int, str, np.ndarray]] = []
        for i in range(min(len(documento), MAX_PAGINAS)):
            pagina = documento[i]
            texto = pagina.get_textpage().get_text_range()
            imagen = pagina.render(scale=lado / max(pagina.get_size())).to_numpy()
            resultado.append((i + 1, texto, _bgr(imagen)))
        return resultado
    finally:
        documento.close()


def _bgr(imagen: np.ndarray) -> np.ndarray:
    if imagen.ndim == 2:
        return cv2.cvtColor(imagen, cv2.COLOR_GRAY2BGR)
    return imagen[:, :, :3].copy() if imagen.shape[2] == 4 else imagen


def _notebook(nombre: str, datos: bytes) -> ContenidoEntrega:
    try:
        return ContenidoEntrega(f"[Archivo {nombre}]\n{texto_para_ia(datos)}")
    except NotebookInvalido:
        texto = datos.decode("utf-8", errors="replace")
        return ContenidoEntrega(f"[Archivo {nombre}]\n{texto[:20000]}")


def _pdf(nombre: str, datos: bytes) -> ContenidoEntrega:
    partes, imagenes = [f"[Archivo {nombre}]"], []
    for numero, texto, imagen in paginas_pdf(datos):
        if texto.strip():
            partes.append(f"[Página {numero}]\n{texto.strip()}")
        if len(texto.strip()) < TEXTO_MINIMO_PAGINA:
            imagenes.append(ImagenPagina(nombre, numero, jpeg(imagen)))
    return ContenidoEntrega("\n\n".join(partes), tuple(imagenes))


def _imagen(nombre: str, datos: bytes) -> ContenidoEntrega:
    imagen = decodificar(datos)
    if imagen is None:
        return ContenidoEntrega("", (), (f"{nombre}: la imagen está dañada.",))
    return ContenidoEntrega(f"[Archivo {nombre}: imagen adjunta]", (ImagenPagina(nombre, 1, jpeg(imagen)),))


def _office(nombre: str, datos: bytes, extension: str) -> ContenidoEntrega:
    with zipfile.ZipFile(io.BytesIO(datos)) as z:
        prefijo = "word/" if extension == ".docx" else "ppt/"
        xmls = (
            ["word/document.xml"]
            if extension == ".docx"
            else sorted(
                (n for n in z.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)),
                key=lambda n: int(re.findall(r"\d+", n)[-1]),
            )
        )
        partes = [f"[Archivo {nombre}]"]
        for i, xml in enumerate(xmls, start=1):
            texto = _texto_xml(z.read(xml))
            etiqueta = f"[Diapositiva {i}]\n" if extension == ".pptx" else ""
            if texto:
                partes.append(etiqueta + texto)
        medios = sorted(
            n
            for n in z.namelist()
            if n.startswith(f"{prefijo}media/") and PurePath(n).suffix.lower() in IMAGENES
        )
        imagenes = [
            ImagenPagina(nombre, i, jpeg(img))
            for i, n in enumerate(medios[:MAX_PAGINAS], start=1)
            if (img := decodificar(z.read(n))) is not None
        ]
    return ContenidoEntrega("\n\n".join(partes), tuple(imagenes))


def _texto_xml(xml: bytes) -> str:
    raiz = xml_seguro.fromstring(xml)  # defusedxml: el archivo viene del alumno y no es confiable
    parrafos: list[str] = []
    for parrafo in raiz.iter():
        if parrafo.tag.endswith("}p"):
            texto = "".join(t.text or "" for t in parrafo.iter() if _TEXTO_XML.search(t.tag))
            if texto.strip():
                parrafos.append(texto.strip())
    return "\n".join(parrafos)
