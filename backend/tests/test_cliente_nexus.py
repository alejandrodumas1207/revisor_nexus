import json

import httpx
import pytest

from revisor.adaptadores.nexus_api.cliente import ClienteHttpNexus, ErrorNexus, SesionVencida

ENCABEZADOS = {"Token": "viejo", "AreaAcademicaId": "19", "RolId": "2", "SistemaId": "1"}


def _cliente(respuestas: list[dict[str, object]], vistos: list[httpx.Request]) -> ClienteHttpNexus:
    def manejar(request: httpx.Request) -> httpx.Response:
        vistos.append(request)
        if request.method == "GET":
            return httpx.Response(200, content=b"%PDF")
        return httpx.Response(200, json=respuestas.pop(0))

    return ClienteHttpNexus(ENCABEZADOS, httpx.Client(transport=httpx.MockTransport(manejar)))


def test_post_json_con_encabezados_de_sesion_y_token_renovado():
    vistos: list[httpx.Request] = []
    cliente = _cliente([{"Estudiantes": [], "Sesion": {"Token": "nuevo"}}, {"ok": 1}], vistos)
    cliente.post_json("Portafolio/ConsultarEstudiantes", {"CursoId": 1})
    cliente.post_json("Portafolio/ConsultarEstudiantes", {"CursoId": 1})
    assert str(vistos[0].url).endswith("/WebApi/Portafolio/ConsultarEstudiantes")
    assert json.loads(vistos[0].content) == {"CursoId": 1}
    assert vistos[0].headers["Token"] == "viejo" and vistos[0].headers["RolId"] == "2"
    assert vistos[1].headers["Token"] == "nuevo"


def test_post_form_manda_multipart():
    vistos: list[httpx.Request] = []
    cliente = _cliente([{"Retroalimentacion": {"RetroalimentacionId": 5}}], vistos)
    cliente.post_form(
        "Retroalimentacion/ActualizarRetroalimentacion", {"RetroalimentacionId": "0", "Descripcion": "Bien"}
    )
    assert vistos[0].headers["Content-Type"].startswith("multipart/form-data")
    assert b'name="Descripcion"' in vistos[0].content and b"Bien" in vistos[0].content


def test_sesion_vencida_y_otros_errores():
    with pytest.raises(SesionVencida):
        _cliente([{"Code": 2011, "Message": "La sesión no existe."}], []).post_json("x", {})
    with pytest.raises(ErrorNexus, match="2003"):
        _cliente([{"Code": 2003, "Message": "Ya existe una sesión activa."}], []).post_json("x", {})


def test_descarga_con_espacios_en_la_url():
    vistos: list[httpx.Request] = []
    contenido = _cliente([], vistos).descargar("Contenedores G2/Contenedor_1/a.pdf")
    assert contenido == b"%PDF"
    assert str(vistos[0].url) == "https://plataformanexus.uanl.mx/Contenedores%20G2/Contenedor_1/a.pdf"
