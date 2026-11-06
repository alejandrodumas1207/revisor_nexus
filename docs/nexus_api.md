# API de NEXUS: lo que se sabe

Base: `https://api.nexus.uanl.mx/WebApi/`. Todas las llamadas son POST con JSON y los encabezados `Token`, `AreaAcademicaId`, `RolId` y `SistemaId` que envía la propia aplicación web. Una sesión vencida responde HTTP 200 con `{"Code": 2011, "Message": "La sesión no existe."}`, así que el estado HTTP no basta para detectarla.

## Sesión

| Ruta | Uso |
|---|---|
| `Seguridad/CrearSesion` | Inicio de sesión. Si ya hay otra activa responde `Code 2003` y la web pregunta si continuar. |
| `Seguridad/ConsultarPerfil` | Datos de la cuenta del docente. |

## Lectura

| Ruta | Cuerpo | Uso |
|---|---|---|
| `Curso/ConsultarCarpetaCursos` | `{CarpetaId, Pagina, Paginacion}` | Periodos (`CarpetaId: 0`) y cursos de un periodo. |
| `Estructura/ConsultarEstructura` | `{CursoId}` | Etapas, evidencias y PIA. |
| `Portafolio/ConsultarEstudiantes` | `{CursoId}` | Lista del grupo. |
| `Portafolio/ConsultarPortafolioEstudiante` | `{CursoId, CuentaId}` | Todo lo de un alumno (lo usa nexus_tools: una llamada por alumno). |
| `Portafolio/ConsultarPortafolioElementoEvaluable` | `{CursoId, TipoElementoId, ElementoId}` | **Todo un elemento en una llamada**: por alumno, entregas (documento, URL, extemporánea), `Calificacion` y `Retroalimentaciones`. Reemplaza las N llamadas por alumno. |
| `Rubrica/ConsultarRubrica` | `{TipoElementoId, ElementoId}` | **Rúbrica completa**: `Criterios` (descripción, posición), `NivelDominios` (Completa, Suficiente, Débil, Sin evidencia) y `CriterioNivelDominios` con el descriptor de cada criterio en cada nivel. Se puede importar tal cual como instrumento de revisión. |
| `Grupo/ConsultarGruposDeCurso`, `Equipo/ConsultarEquiposPorCurso`, `Recurso/ConsultarRecursos` | | Grupos, equipos y recursos del curso. |

Descarga de archivos: GET a `https://plataformanexus.uanl.mx/{Documento.URL}`.

## Escritura

Capturada el 2026-11-06 en RNAP 5V1. Todas responden HTTP 200; el resultado real va en el cuerpo.

### Calificación: `Portafolio/ActualizarCalificacionesElementoEvaluable`

JSON. Acepta **varios alumnos en una sola petición** (`Estudiantes` es una lista). `Valor` va en escala 0-100.

Sin rúbrica (Dimensiones 2 y 3). La web reenvía el objeto completo del alumno tal como lo devolvió `ConsultarPortafolioElementoEvaluable`, con `Valor` y `Calificacion.Valor` cambiados:

```json
{"CursoId": 0, "TipoElementoId": 1, "ElementoId": 0, "UsaRubrica": false,
 "Estudiantes": [{"CuentaId": 0, "Valor": "100", "Calificacion": {"Rubrica": [], "Calificado": false, "Valor": "100"}, "...": "resto del objeto"}]}
```

Con rúbrica (EA y PIA). Por criterio, el nivel elegido; los identificadores salen de `ConsultarRubrica` (`CriterioNivelDominios`):

```json
{"CursoId": 0, "TipoElementoId": 1, "ElementoId": 0, "UsaRubrica": true,
 "Estudiantes": [{"CuentaId": 0, "Valor": 100,
   "Rubrica": [{"RubricaId": 0, "CriterioId": 0, "NivelDominioId": 0, "CriterioNivelDominioId": 0}]}]}
```

Respuesta: `{"Calificaiones": [{"CuentaId", "Valor", "Rubrica", "FechaModificacion", ...}]}` (sic: "Calificaiones").

### Retroalimentación: `Retroalimentacion/ActualizarRetroalimentacion`

`multipart/form-data`. Con `RetroalimentacionId = 0` crea una nueva; con un id existente **la edita en su lugar**, lo que permite corregir retroalimentaciones equivocadas sin duplicarlas.

| Campo | Valor |
|---|---|
| `RetroalimentacionId` | 0 (nueva) o el id a editar |
| `Descripcion` | texto |
| `DerechoReplica` | `false` |
| `Estado` | `true` |
| `CursoId`, `TipoElementoId`, `ElementoId` | del elemento |
| `Estudiantes` | `CuentaId` del alumno |
| `EquipoId` | `0` |

Respuesta: `{"Retroalimentacion": {"RetroalimentacionId", "Descripcion", ...}}`.

### Eliminar retroalimentación: `Retroalimentacion/EliminarRetroalimentacion`

JSON `{"CursoId", "TipoElementoId", "ElementoId", "RetroalimentacionId"}`. Respuesta `{"RetroalimentacionEliminada": true}`.

## Consecuencias para la app

- La carga se hace por API, sin navegador ni selectores. Un elemento completo de Dimensión 2 o 3 se califica con una sola petición.
- Las respuestas traen un `Token` nuevo de sesión: nunca se registran en logs ni capturas.
