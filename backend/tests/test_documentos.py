import io
import zipfile

import cv2
import numpy as np

from revisor.adaptadores.extractores.documentos import extraer
from revisor.dominio.contenido import ContenidoEntrega, ImagenPagina, unir


def _png(ancho: int = 3000, alto: int = 2000) -> bytes:
    imagen = np.full((alto, ancho, 3), 255, np.uint8)
    cv2.putText(imagen, "Mapa", (100, 300), cv2.FONT_HERSHEY_SIMPLEX, 5, (0, 0, 0), 8)
    return cv2.imencode(".png", imagen)[1].tobytes()


def _office(archivos: dict[str, bytes]) -> bytes:
    memoria = io.BytesIO()
    with zipfile.ZipFile(memoria, "w") as z:
        for nombre, contenido in archivos.items():
            z.writestr(nombre, contenido)
    return memoria.getvalue()


W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
A = 'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"'


def _pdf(texto: str) -> bytes:
    """PDF mínimo de una página con texto (sin dependencias)."""
    contenido = f"BT /F1 24 Tf 72 720 Td ({texto}) Tj ET".encode()
    objetos = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(contenido)).encode() + b" >>\nstream\n" + contenido + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    salida, posiciones = io.BytesIO(), []
    salida.write(b"%PDF-1.4\n")
    for i, obj in enumerate(objetos, start=1):
        posiciones.append(salida.tell())
        salida.write(f"{i} 0 obj\n".encode() + obj + b"\nendobj\n")
    inicio = salida.tell()
    salida.write(f"xref\n0 {len(objetos) + 1}\n0000000000 65535 f \n".encode())
    for p in posiciones:
        salida.write(f"{p:010d} 00000 n \n".encode())
    salida.write(f"trailer << /Size {len(objetos) + 1} /Root 1 0 R >>\nstartxref\n{inicio}\n%%EOF".encode())
    return salida.getvalue()


def test_imagen_se_reduce_y_se_adjunta():
    c = extraer("mapa.png", _png())
    assert len(c.imagenes) == 1
    imagen = cv2.imdecode(np.frombuffer(c.imagenes[0].jpeg, np.uint8), cv2.IMREAD_COLOR)
    assert imagen is not None and max(imagen.shape[:2]) == 1600


def test_pdf_con_poco_texto_manda_texto_e_imagen():
    c = extraer("reporte.pdf", _pdf("Conclusion de la practica"))
    assert "[Página 1]\nConclusion de la practica" in c.texto
    assert len(c.imagenes) == 1  # menos de 200 caracteres: la IA también ve la página


def test_word_con_parrafos_e_imagen_incrustada():
    documento = (
        f"<w:document {W}><w:body><w:p><w:r><w:t>Hola </w:t></w:r><w:r><w:t>mundo</w:t></w:r></w:p>"
        "<w:p><w:r><w:t>Segundo</w:t></w:r></w:p></w:body></w:document>"
    )
    c = extraer(
        "ensayo.docx",
        _office({"word/document.xml": documento.encode(), "word/media/image1.png": _png(400, 300)}),
    )
    assert "Hola mundo\nSegundo" in c.texto
    assert len(c.imagenes) == 1


def test_presentacion_en_orden_de_diapositivas():
    diapo = f"<p:sld xmlns:p='p' {A}><a:p><a:r><a:t>{{}}</a:t></a:r></a:p></p:sld>"
    archivos = {f"ppt/slides/slide{i}.xml": diapo.format(f"Tema {i}").encode() for i in (10, 2, 1)}
    c = extraer("expo.pptx", _office(archivos))
    assert c.texto.index("Tema 1") < c.texto.index("Tema 2") < c.texto.index("Tema 10")
    assert "[Diapositiva 1]\nTema 1" in c.texto


def test_video_y_archivos_danados_quedan_como_aviso():
    assert "revisión manual" in extraer("expo.mp4", b"x").avisos[0]
    danado = extraer("roto.pdf", b"no es pdf")
    assert danado.vacio and "no se pudo leer" in danado.avisos[0]


def test_unir_respeta_el_limite_de_imagenes():
    img = ImagenPagina("a.png", 1, b"j")
    total = unir([ContenidoEntrega("uno", (img, img)), ContenidoEntrega("dos", (img,))], limite_imagenes=2)
    assert total.texto == "uno\n\ndos" and len(total.imagenes) == 2
    assert "2 de 3 imágenes" in total.avisos[0]
