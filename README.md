# Revisor NEXUS

App personal para descargar entregas de NEXUS UANL, revisarlas con apoyo de IA bajo control del docente y subir calificación y retroalimentación.

Estado: fases 0 y 1 cerradas (investigación, núcleo, descarga y revisión con IA). Sigue la fase 2: interfaz. El plan completo está en [docs/PROPUESTA.md](docs/PROPUESTA.md) y las decisiones en [docs/adr/](docs/adr/).

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
just listar        # cursos y actividades de NEXUS (solo lectura)
just descargar "Redes" 3.2 3.4   # descarga entregas por actividad
just revisar-ia "Redes" 3.2      # descarga y revisa con IA; nada se sube
```

## Cómo está hecho

Arquitectura hexagonal (`backend/src/revisor`): `dominio` (reglas puras), `puertos` (interfaces), `adaptadores` (NEXUS, Gemini, extractores, SQLite) y `servicios` (casos de uso). Las decisiones están en `docs/adr/` y la API de NEXUS en `docs/nexus_api.md`.
