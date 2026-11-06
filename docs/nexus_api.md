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

Pendiente de capturar con `just capturar`: guardar calificación (con y sin rúbrica) y agregar retroalimentación.

Captura del 2026-11-05: se recorrió RNAP 5V1 hasta la vista de evaluación, pero no se registró ninguna escritura.
