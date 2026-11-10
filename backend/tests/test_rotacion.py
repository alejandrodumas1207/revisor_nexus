from collections.abc import Sequence
from typing import Any

import pytest

from revisor.adaptadores.ia.rotacion import ProveedorRotativo
from revisor.puertos.ia import CuotaAgotada, ModeloNoDisponible


class Modelo:
    def __init__(self, nombre: str, cuota: int) -> None:
        self.modelo = nombre
        self.cuota = cuota
        self.llamadas = 0

    def generar_json(
        self, instrucciones: str, contenido: str, esquema: dict[str, Any], imagenes: Sequence[bytes] = ()
    ) -> dict[str, Any]:
        self.llamadas += 1
        if self.cuota <= 0:
            raise CuotaAgotada(self.modelo)
        self.cuota -= 1
        return {"modelo": self.modelo}


def test_usa_el_primero_mientras_tenga_cuota():
    a, b = Modelo("a", 2), Modelo("b", 5)
    rotativo = ProveedorRotativo([a, b])
    assert rotativo.generar_json("", "", {}) == {"modelo": "a"}
    assert rotativo.modelo == "a"


def test_pasa_al_siguiente_y_no_vuelve_al_agotado():
    a, b = Modelo("a", 1), Modelo("b", 5)
    rotativo = ProveedorRotativo([a, b])
    rotativo.generar_json("", "", {})
    assert rotativo.generar_json("", "", {}) == {"modelo": "b"}
    assert rotativo.modelo == "b"
    rotativo.generar_json("", "", {})
    assert a.llamadas == 2  # la llamada que descubrió el agotamiento y ninguna más
    assert rotativo.disponibles == ["b"]


def test_todos_agotados():
    rotativo = ProveedorRotativo([Modelo("a", 0), Modelo("b", 0)])
    with pytest.raises(CuotaAgotada, match="Ningún"):
        rotativo.generar_json("", "", {})


class Inexistente(Modelo):
    def generar_json(
        self, instrucciones: str, contenido: str, esquema: dict[str, Any], imagenes: Sequence[bytes] = ()
    ) -> dict[str, Any]:
        self.llamadas += 1
        raise ModeloNoDisponible(self.modelo)


def test_modelo_inexistente_se_salta():
    fantasma, b = Inexistente("fantasma", 9), Modelo("b", 5)
    rotativo = ProveedorRotativo([fantasma, b])
    assert rotativo.generar_json("", "", {}) == {"modelo": "b"}
    rotativo.generar_json("", "", {})
    assert fantasma.llamadas == 1
