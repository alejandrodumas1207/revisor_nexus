# ADR 0003: SQLite como fuente de verdad

Fecha: 2026-11-05. Estado: aceptado.

## Contexto

En `nexus_tools` el maestro `.xlsx` funciona como base de datos. Cada guardado reescribe el archivo (cerca de 1 s), el diseño de columnas está acoplado entre módulos y las migraciones se hacen a mano.

## Decisión

- SQLite, con SQLModel y migraciones de Alembic, guarda cursos, elementos, entregas, instrumentos, revisiones, correcciones y cargas.
- Excel se genera bajo demanda como exportación con el formato de concentrado actual.
- Los maestros existentes se importan una vez como historial.

## Consecuencias

- Hay escrituras concurrentes seguras para los tres trabajadores (modo WAL).
- El docente ya no edita Excel a mano. Los cambios se hacen en la app.
