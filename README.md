# Revisor NEXUS

App personal para descargar entregas de NEXUS UANL, revisarlas con apoyo de IA bajo control del docente y subir calificación y retroalimentación.

Estado: fase 0 (arranque e investigación). El plan completo está en [docs/PROPUESTA.md](docs/PROPUESTA.md) y las decisiones en [docs/adr/](docs/adr/).

## Principios

- La calificación sale de instrumentos propios del docente (listas de cotejo y rúbricas). La IA propone y el docente valida; nada se sube sin validación.
- Los datos de alumnos nunca se versionan. Antes de enviar a un proveedor externo se seudonimizan.
- Credenciales y claves solo en el administrador de credenciales del sistema.

## Requisitos

Python 3.12, [uv](https://docs.astral.sh/uv/), [just](https://just.systems/) y Node.js LTS.

```
just instalar      # dependencias, Chromium y pre-commit
just revisar       # lint, tipos, pruebas y auditoría de seguridad
just clave         # guarda la clave de Gemini en el administrador de credenciales
```
