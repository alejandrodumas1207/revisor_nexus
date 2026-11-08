"""Retroalimentación detallada para el alumno: desglose por criterio, ajustes y calificación en NEXUS.

La estructura y los números los pone el código, así siempre cuadran con la calificación registrada.
Los comentarios (qué hizo bien, qué falta, por qué hay sospecha de copia) vienen de la revisión.
Nunca se nombra a otro alumno: una copia se describe como coincidencia con la entrega de un compañero.
"""

from dataclasses import dataclass

from revisor.dominio.integridad import DetalleCalificacion, VeredictoCopia

NOMBRE_NIVEL = {"cumple": "cumple", "parcial": "cumple parcialmente", "no_cumple": "no cumple"}
FACTOR_NIVEL = {"cumple": 1.0, "parcial": 0.7, "no_cumple": 0.0}
_TITULO_COPIA = {
    VeredictoCopia.CONFIRMADA: "Copia confirmada",
    VeredictoCopia.PARCIAL: "Copia parcial",
    VeredictoCopia.SOSPECHA: "Sospecha de copia (sin descuento)",
}


@dataclass(frozen=True, slots=True)
class CriterioEvaluado:
    id: str
    nombre: str
    puntos: float
    nivel: str  # cumple | parcial | no_cumple
    comentario: str

    @property
    def obtenidos(self) -> float:
        return self.puntos * FACTOR_NIVEL[self.nivel]


@dataclass(frozen=True, slots=True)
class InformeAlumno:
    criterios: tuple[CriterioEvaluado, ...]
    detalle: DetalleCalificacion
    fortalezas: str
    pendientes: str
    copia: VeredictoCopia = VeredictoCopia.NINGUNA
    justificacion_copia: str = ""
    avisos: tuple[str, ...] = ()


def componer_retroalimentacion(informe: InformeAlumno) -> str:
    partes = [
        f"Calificación en NEXUS: {informe.detalle.final}",
        _desglose(informe),
        _ajustes(informe.detalle),
        f"Lo que hiciste bien: {informe.fortalezas.strip()}",
        f"Lo que falta o hay que corregir: {informe.pendientes.strip()}",
    ]
    if informe.copia in _TITULO_COPIA:
        partes.append(f"{_TITULO_COPIA[informe.copia]}: {informe.justificacion_copia.strip()}")
    if informe.avisos:
        partes.append("Para la próxima entrega: " + " ".join(a.strip() for a in informe.avisos))
    return "\n\n".join(partes)


def _numero(valor: float) -> str:
    return f"{valor:.1f}".rstrip("0").rstrip(".")


def _desglose(informe: InformeAlumno) -> str:
    lineas = ["Desglose por criterio:"]
    for c in informe.criterios:
        lineas.append(
            f"• {c.id} {c.nombre}: {_numero(c.obtenidos)} de {_numero(c.puntos)} "
            f"({NOMBRE_NIVEL[c.nivel]}). {c.comentario.strip()}"
        )
    obtenidos = sum(c.obtenidos for c in informe.criterios)
    total = sum(c.puntos for c in informe.criterios)
    sobre_10 = _numero(informe.detalle.lista)
    lineas.append(f"Total de la lista: {_numero(obtenidos)} de {_numero(total)} ({sobre_10} de 10)")
    return "\n".join(lineas)


def _ajustes(detalle: DetalleCalificacion) -> str:
    if not detalle.pasos:
        return f"Ajustes: ninguno. Calificación registrada: {detalle.final}."
    lineas = ["Ajustes:"]
    lineas += [f"• {p.descripcion} → {_numero(p.valor)}" for p in detalle.pasos]
    return "\n".join(lineas)
