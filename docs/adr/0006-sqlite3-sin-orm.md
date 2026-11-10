# ADR 0006: SQLite con `sqlite3` y SQL explícito, sin ORM

Fecha: 2026-11-09. Estado: aceptado. Precisa el ADR 0003 (SQLite como fuente de verdad), que proponía SQLModel y Alembic.

## Contexto

La base guarda pocas tablas con relaciones simples: cursos, elementos, alumnos, entregas, instrumentos versionados, revisiones (historial), decisiones del docente y bitácora de cargas. El dominio ya tiene sus propias entidades (dataclasses puras) y `pyright` estricto en dominio y servicios.

## Decisión

- Adaptador `adaptadores/persistencia/sqlite.py` con el módulo estándar `sqlite3` y SQL escrito a mano, detrás del puerto `puertos/repositorio.py`.
- Migraciones numeradas en el mismo adaptador; la versión aplicada se guarda en `PRAGMA user_version`. Una migración nunca se edita después de publicada: se agrega la siguiente.
- Modo WAL y claves foráneas activas, para que descarga, revisión y carga escriban en paralelo.
- Los valores compuestos (niveles por criterio, comentarios, archivos) se guardan como JSON en columnas de texto.
- Las revisiones son historial: cada propuesta (IA, Claude o docente) es una fila nueva con su procedencia; nunca se sobrescribe.

## Consecuencias

- Sin dependencias nuevas y con todo el SQL a la vista para auditarlo.
- Las entidades del dominio se convierten a filas en el adaptador; si el modelo crece mucho, se puede reconsiderar un ORM.
