import cv2
import numpy as np

from revisor.adaptadores.extractores.firmas import (  # pyright: ignore[reportPrivateUsage]
    _es_firma,
    detectar_marca,
    paginas_de,
)


def _hoja(con_rayon: bool) -> np.ndarray:
    hoja = np.full((2200, 1700, 3), 255, np.uint8)
    for renglon in range(200, 1500, 60):  # texto impreso del alumno
        cv2.putText(
            hoja,
            "Respuesta del alumno sobre redes",
            (150, renglon),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.2,
            (20, 20, 20),
            2,
        )
    if con_rayon:  # rayón curvo de marcador rosa al pie de la página
        cv2.ellipse(hoja, (850, 1850), (420, 160), 0, 200, 340, (180, 105, 255), 22)
    return hoja


FIRMA_TIPICA = {
    "sinuosidad": 2.2,
    "relleno": 0.06,
    "hoyos": 2,
    "recto": 0.2,
    "grosor": 3.5,
    "curva": 0.08,
    "ancho": 0.3,
    "alto": 0.1,
    "y": 0.8,
}


def test_regla_de_firma_acepta_trazo_tipico_al_pie():
    assert _es_firma(FIRMA_TIPICA)


def test_regla_de_firma_rechaza_renglones_y_trazos_a_media_hoja():
    assert not _es_firma({**FIRMA_TIPICA, "recto": 0.9})  # línea recta: renglón o tabla
    assert not _es_firma({**FIRMA_TIPICA, "y": 0.4})  # a media hoja, fuera de la portada
    assert _es_firma({**FIRMA_TIPICA, "y": 0.4}, toda_la_hoja=True)  # en la portada vale en cualquier parte


def test_hoja_solo_con_texto_no_tiene_marca():
    assert not detectar_marca([(1, _hoja(con_rayon=False))]).encontrada


def test_pagina_en_blanco_no_cuenta():
    blanca = np.full((1000, 800, 3), 255, np.uint8)
    marca = detectar_marca([(1, blanca)])
    assert marca.paginas == 0 and not marca.encontrada


def test_lee_imagenes_por_extension():
    png = cv2.imencode(".png", _hoja(con_rayon=True))[1].tobytes()
    assert [n for n, _ in paginas_de("libreta.png", png)] == [1]
    assert list(paginas_de("video.mp4", b"x")) == []
