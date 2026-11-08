"""Retroalimentación detallada para el alumno: desglose por criterio, ajustes y calificación en NEXUS.

La estructura y los números los pone el código, así siempre cuadran con la calificación registrada.
Los apartados son por criterio: en cada uno, lo que está bien y lo que falta. Al final, comentarios
generales opcionales; la copia o sospecha se explica ahí con el nombre del compañero y el motivo.
"""

from dataclasses import dataclass

from revisor.dominio.integridad import DetalleCalificacion, VeredictoCopia

NOMBRE_NIVEL = {"cumple": "cumple", "parcial": "cumple parcialmente", "no_cumple": "no cumple"}
FACTOR_NIVEL = {"cumple": 1.0, "parcial": 0.7, "no_cumple": 0.0}
_TITULO_COPIA = {
    VeredictoCopia.CONFIRMADA: "Copia confirmada (calificación × 0.5)",
    VeredictoCopia.PARCIAL: "Copia parcial (calificación × 0.75)",
    VeredictoCopia.SOSPECHA: "Sospecha de copia (sin penalización)",
}


@dataclass(frozen=True, slots=True)
class CriterioEvaluado:
    id: str
    nombre: str
    puntos: float
    nivel: str  # cumple | parcial | no_cumple
    comentario: str  # lo que está bien y lo que falta en este criterio

    @property
    def obtenidos(self) -> float:
        return self.puntos * FACTOR_NIVEL[self.nivel]


@dataclass(frozen=True, slots=True)
class InformeAlumno:
    criterios: tuple[CriterioEvaluado, ...]
    detalle: DetalleCalificacion
    comentarios_generales: str = ""  # opcional
    copia: VeredictoCopia = VeredictoCopia.NINGUNA
    copia_con: tuple[str, ...] = ()  # "Nombre Apellido (matrícula)" de cada compañero involucrado
    justificacion_copia: str = ""
    avisos: tuple[str, ...] = ()


def componer_retroalimentacion(informe: InformeAlumno) -> str:
    partes = [
        f"Calificación en NEXUS: {informe.detalle.final}",
        _desglose(informe),
        _ajustes(informe.detalle),
    ]
    generales = _comentarios_generales(informe)
    if generales:
        partes.append(generales)
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


def _comentarios_generales(informe: InformeAlumno) -> str:
    lineas: list[str] = []
    if informe.copia in _TITULO_COPIA:
        con = f" con {', '.join(informe.copia_con)}" if informe.copia_con else ""
        lineas.append(f"• {_TITULO_COPIA[informe.copia]}{con}: {informe.justificacion_copia.strip()}")
    if informe.comentarios_generales.strip():
        lineas.append(f"• {informe.comentarios_generales.strip()}")
    lineas += [f"• Para la próxima entrega: {a.strip()}" for a in informe.avisos]
    return "\n".join(["Comentarios generales:", *lineas]) if lineas else ""
