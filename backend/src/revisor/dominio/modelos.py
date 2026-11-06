"""Entidades del dominio: lo que existe en NEXUS y lo que produce la revisión."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from revisor.dominio.retroalimentacion import RetroNexus


class TipoElemento(StrEnum):
    EVIDENCIA = "evidencia"  # TipoElementoId 1 en NEXUS
    PIA = "pia"  # TipoElementoId 2 en NEXUS


class EstadoEntrega(StrEnum):
    SIN_ENTREGA = "sin_entrega"
    DESCARGADA = "descargada"
    EXTRAIDA = "extraida"
    SUGERIDA = "sugerida"
    AUDITADA = "auditada"
    VALIDADA = "validada"
    SUBIDA = "subida"


class Origen(StrEnum):
    """Quién propuso una calificación. Toda calificación guarda su origen."""

    REGLA = "regla"
    GEMINI = "gemini"
    CLAUDE = "claude"
    DOCENTE = "docente"


@dataclass(frozen=True, slots=True)
class Curso:
    id: int
    nombre: str
    grupo: str
    carpeta: str


@dataclass(frozen=True, slots=True)
class Elemento:
    codigo: str  # "1.2" (etapa.posición) o "PIA"
    id: int
    tipo: TipoElemento
    nombre: str
    valor: float
    usa_rubrica: bool
    criterios_nexus: int | None
    fin: datetime | None
    limite: datetime | None


@dataclass(frozen=True, slots=True)
class Alumno:
    matricula: str
    cuenta_id: int
    nombre: str


@dataclass(frozen=True, slots=True)
class Archivo:
    nombre: str
    url: str
    peso: int
    fecha: datetime | None
    extemporaneo: bool


@dataclass(frozen=True, slots=True)
class EntregaNexus:
    """Lo que NEXUS reporta de un alumno en un elemento."""

    matricula: str
    codigo_elemento: str
    archivos: tuple[Archivo, ...]
    calificacion_nexus: float | None  # escala 0-100 de NEXUS
    retros_nexus: tuple[RetroNexus, ...] = field(default=())


@dataclass(frozen=True, slots=True)
class NivelRubricaNexus:
    """Nivel marcado en un criterio de la rúbrica de NEXUS (identificadores de ConsultarRubrica)."""

    rubrica_id: int
    criterio_id: int
    nivel_dominio_id: int
    criterio_nivel_dominio_id: int


@dataclass(frozen=True, slots=True)
class CalificacionNexus:
    cuenta_id: int
    valor: int  # escala 0-100 de NEXUS
    rubrica: tuple[NivelRubricaNexus, ...] = ()
