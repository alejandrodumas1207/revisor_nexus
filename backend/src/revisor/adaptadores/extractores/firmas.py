"""Busca la firma o el rayón de marcador del profesor en una entrega (PDF, imagen o Word).

No lee la firma: busca un trazo grande, curvo y delgado en una zona libre de la página, o un rayón grueso
de marcador de color. Es una señal más para la revisión (la IA también mira las imágenes).
Portado sin cambios de umbrales de nexus_tools/nexus_lib/firmas.py (VERSION 4).
"""

import io
import zipfile
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import PurePath
from typing import Any

import cv2
import numpy as np

from revisor.adaptadores.extractores.documentos import IMAGENES, decodificar, paginas_pdf

VERSION = 4
LADO = 1400  # lado largo de cada página al analizarla
LADO_RENDER = 2200  # lado largo al convertir un PDF en imagen
UMBRALES: dict[str, Any] = {
    "contraste": 0.16,  # qué tan oscuro debe ser el trazo frente a su fondo
    "ancho_min": 0.13,  # respecto al lado corto de la página
    "alto_min": 0.055,
    "ancho_vs_alto": 1.15,  # la firma es más ancha que alta
    "lado_max": 0.62,
    "sinuosidad": (1.4, 3.7),  # largo del trazo entre diagonal de su caja
    "relleno_max": 0.155,
    "hoyos_max": 7,
    "recto_max": 0.62,  # parte del trazo que es línea recta (renglones, tablas)
    "grosor_max": 5.6,
    "curva_min": 0.045,  # separación media respecto a una recta
    "zona_alta": 0.22,  # la firma va al pie de la página, o arriba si la foto está invertida
    "zona_baja": 0.55,
    # Rayón con marcador de color (rojo, rosa o azul): se reconoce por color y grosor, en cualquier parte
    "color_min": 14,
    "color_fuerte": 24,  # descarta encabezados pálidos y sombras de color
    "marcador_grosor": 5.0,  # la pluma de los alumnos es más delgada
    "marcador_largo": 0.13,
    "marcador_ancho": 0.05,
    "marcador_relleno": (0.06, 0.6),
    "marcador_recto_max": 0.85,
    "marcador_mezcla_max": 14,  # un logotipo mezcla colores; el marcador es de un solo color
    "marcador_luz_min": 150,  # en hoja blanca digital solo vale si es claro: fuera logotipos y sellos
    "marcador_luz_abs": 45,  # más oscuro que esto es tinta negra o texto impreso
    "fondo_digital": 246,
}


@dataclass(frozen=True, slots=True)
class MarcaRevision:
    encontrada: bool
    paginas: int  # páginas con contenido analizadas
    pagina: int | None = None  # dónde está la marca más grande
    caja: tuple[int, int, int, int] | None = None


def paginas_de(nombre: str, datos: bytes) -> Iterator[tuple[int, np.ndarray]]:
    extension = PurePath(nombre).suffix.lower()
    if extension == ".pdf":
        for numero, _texto, imagen in paginas_pdf(datos, LADO_RENDER):
            yield numero, imagen
    elif extension == ".docx":
        with zipfile.ZipFile(io.BytesIO(datos)) as z:
            medios = sorted(
                n
                for n in z.namelist()
                if n.startswith("word/media/") and PurePath(n).suffix.lower() in IMAGENES
            )
            for i, n in enumerate(medios, start=1):
                if (imagen := decodificar(z.read(n))) is not None:
                    yield i, imagen
    elif extension in IMAGENES and (imagen := decodificar(datos)) is not None:
        yield 1, imagen


def detectar_marca(paginas: Sequence[tuple[int, np.ndarray]]) -> MarcaRevision:
    """Una firma o rayón en cualquier página basta. En la primera página la firma vale en toda la hoja."""
    analizadas, mejor = 0, (0, None, None)
    for numero, imagen in paginas:
        pagina = normalizar(imagen)
        if pagina is None:  # página en blanco
            continue
        analizadas += 1
        halladas = [
            c for c in candidatos(pagina) if _es_firma(c, toda_la_hoja=analizadas == 1)
        ] + marcas_color(pagina)
        for c in halladas:
            if c["area"] > mejor[0]:
                mejor = (c["area"], numero, tuple(c["caja"]))
    _, pagina_marca, caja = mejor
    return MarcaRevision(pagina_marca is not None, analizadas, pagina_marca, caja)


def normalizar(img: np.ndarray) -> np.ndarray | None:
    """Quita el margen blanco y lleva la página a un tamaño fijo."""
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    ys, xs = np.where(g < 245)
    if len(xs) < 100:
        return None
    x0, x1 = int(np.percentile(xs, 0.2)), int(np.percentile(xs, 99.8))
    y0, y1 = int(np.percentile(ys, 0.2)), int(np.percentile(ys, 99.8))
    r = img[y0 : y1 + 1, x0 : x1 + 1]
    if min(r.shape[:2]) < 100:
        return None
    e = LADO / max(r.shape[:2])
    return cv2.resize(r, None, fx=e, fy=e, interpolation=cv2.INTER_AREA)


def mapa_trazos(img: np.ndarray) -> np.ndarray:
    """Trazos oscuros y delgados. Mide contraste relativo para aguantar sombras y fotos oscuras."""
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    g = cv2.GaussianBlur(g, (3, 3), 0)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25))
    fondo = cv2.GaussianBlur(cv2.morphologyEx(g, cv2.MORPH_CLOSE, k), (0, 0), 9)
    rel = (fondo - g) / (fondo + 25)
    m = (rel > UMBRALES["contraste"]).astype(np.uint8) * 255
    for ks in ((90, 1), (1, 90)):  # quita renglones y bordes de tabla
        o = cv2.morphologyEx(m, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, ks))
        m = cv2.subtract(m, cv2.dilate(o, np.ones((5, 5), np.uint8)))
    return m


def _parte_recta(tinta: np.ndarray) -> float:
    lineas = cv2.HoughLinesP(tinta, 1, np.pi / 180, 40, minLineLength=70, maxLineGap=4)
    if lineas is None:
        return 0.0
    c = np.zeros_like(tinta)
    for x1, y1, x2, y2 in lineas.reshape(-1, 4):
        cv2.line(c, (int(x1), int(y1)), (int(x2), int(y2)), 255, 7)
    return float(((c > 0) & (tinta > 0)).sum() / max((tinta > 0).sum(), 1))


def _medir(tinta: np.ndarray, w: int, h: int) -> dict[str, Any]:
    contornos, jer = cv2.findContours(tinta, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    perim = sum(cv2.arcLength(k, True) for k in contornos)
    area = int((tinta > 0).sum())
    grosor = 2 * area / max(perim, 1)
    diag = (w * w + h * h) ** 0.5
    pts = np.column_stack(np.where(tinta > 0)[::-1]).astype(np.float32)
    vx, vy, x0, y0 = cv2.fitLine(pts, cv2.DIST_L2, 0, 0.01, 0.01).ravel()
    curva = float(np.abs((pts[:, 0] - x0) * vy - (pts[:, 1] - y0) * vx).mean() / diag)
    return {
        "relleno": area / (w * h),
        "grosor": grosor,
        "sinuosidad": area / max(grosor, 1) / diag,
        "hoyos": sum(1 for j in jer[0] if j[3] >= 0) if jer is not None else 0,
        "curva": curva,
        "recto": _parte_recta(tinta),
        "area": area,
    }


def _es_firma(c: dict[str, Any], u: dict[str, Any] = UMBRALES, toda_la_hoja: bool = False) -> bool:
    s0, s1 = u["sinuosidad"]
    return bool(
        s0 <= c["sinuosidad"] <= s1
        and c["relleno"] <= u["relleno_max"]
        and c["hoyos"] <= u["hoyos_max"]
        and c["recto"] <= u["recto_max"]
        and c["grosor"] <= u["grosor_max"]
        and c["curva"] >= u["curva_min"]
        and c["ancho"] >= u["ancho_min"]
        and c["alto"] >= u["alto_min"]
        and c["ancho"] >= u["ancho_vs_alto"] * c["alto"]
        and (toda_la_hoja or c["y"] >= u["zona_baja"] or c["y"] <= u["zona_alta"])
    )


def candidatos(pagina: np.ndarray) -> list[dict[str, Any]]:
    m = mapa_trazos(pagina)
    alto_p, ancho_p = m.shape
    base = min(alto_p, ancho_p)
    n, lab, st, _ = cv2.connectedComponentsWithStats(cv2.dilate(m, np.ones((3, 3), np.uint8)), connectivity=8)
    salida: list[dict[str, Any]] = []
    for i in range(1, n):
        x, y, w, h, _a = (int(v) for v in st[i])
        if max(w, h) < 0.12 * base or min(w, h) < 0.04 * base or max(w, h) > UMBRALES["lado_max"] * base:
            continue
        if x <= 1 or y <= 1 or x + w >= ancho_p - 1 or y + h >= alto_p - 1:
            continue
        tinta = (lab[y : y + h, x : x + w] == i).astype(np.uint8) * m[y : y + h, x : x + w]
        if (tinta > 0).sum() < 80:
            continue
        c = _medir(tinta, w, h)
        c.update(caja=[x, y, w, h], ancho=w / base, alto=h / base, y=(y + h / 2) / alto_p)
        salida.append(c)
    return salida


def marcas_color(pagina: np.ndarray) -> list[dict[str, Any]]:
    """Rayones gruesos de marcador de color."""
    u = UMBRALES
    lab_img = cv2.cvtColor(pagina, cv2.COLOR_BGR2LAB).astype(np.float32)
    alto_p, ancho_p = lab_img.shape[:2]
    base = min(alto_p, ancho_p)
    fondo = [
        cv2.resize(
            cv2.medianBlur(cv2.resize(lab_img[:, :, i], None, fx=0.1, fy=0.1).astype(np.uint8), 31),
            (ancho_p, alto_p),
        ).astype(np.float32)
        for i in (1, 2)
    ]
    croma = np.sqrt((lab_img[:, :, 1] - fondo[0]) ** 2 + (lab_img[:, :, 2] - fondo[1]) ** 2)
    m = cv2.morphologyEx(
        (croma > u["color_min"]).astype(np.uint8) * 255, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)
    )
    n, lab, st, _ = cv2.connectedComponentsWithStats(cv2.dilate(m, np.ones((9, 9), np.uint8)), connectivity=8)
    salida: list[dict[str, Any]] = []
    for i in range(1, n):
        x, y, w, h, _a = (int(v) for v in st[i])
        if (
            max(w, h) < u["marcador_largo"] * base
            or min(w, h) < u["marcador_ancho"] * base
            or max(w, h) > u["lado_max"] * base
        ):
            continue
        tinta = (lab[y : y + h, x : x + w] == i).astype(np.uint8) * m[y : y + h, x : x + w]
        if (tinta > 0).sum() < 150:
            continue
        c = _medir(tinta, w, h)
        if _es_marcador(c, lab_img[y : y + h, x : x + w], tinta, (x, y, w, h), (ancho_p, alto_p)):
            c.update(caja=[x, y, w, h])
            salida.append(c)
    return salida


def _es_marcador(
    c: dict[str, Any],
    recorte: np.ndarray,
    tinta: np.ndarray,
    caja: tuple[int, int, int, int],
    tam: tuple[int, int],
) -> bool:
    u = UMBRALES
    pix = recorte[tinta > 0]
    ca, cb = float(np.median(pix[:, 1])) - 128, float(np.median(pix[:, 2])) - 128
    r0, r1 = u["marcador_relleno"]
    if (
        (ca * ca + cb * cb) ** 0.5 < u["color_fuerte"]
        or c["grosor"] < u["marcador_grosor"]
        or not r0 <= c["relleno"] <= r1
        or c["recto"] > u["marcador_recto_max"]
        or max(float(np.std(pix[:, 1])), float(np.std(pix[:, 2]))) > u["marcador_mezcla_max"]
    ):
        return False
    luz = float(np.median(pix[:, 0]))
    if luz < u["marcador_luz_abs"]:
        return False
    hoja_blanca = float(np.median(recorte[:, :, 0][tinta == 0])) >= u["fondo_digital"]
    if hoja_blanca and luz < u["marcador_luz_min"]:
        return False
    # En una foto, lo que toca la orilla suele ser una carpeta o el fondo. En un escaneo sí puede ser firma
    x, y, w, h = caja
    toca_orilla = x <= 2 or y <= 2 or x + w >= tam[0] - 2 or y + h >= tam[1] - 2
    return hoja_blanca or not toca_orilla
