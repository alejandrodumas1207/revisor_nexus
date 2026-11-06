# ADR 0005: Copias y entregas tardías

Fecha: 2026-11-06. Estado: aceptado.

## Contexto

En RNAP E1-E2 hubo copias confirmadas y varios alumnos con 0 por "no se registró entrega" que en realidad entregaron tarde por formulario. Antes, una copia bajaba la calificación a 5 (50 de 100) sin importar la calidad del trabajo. Las fechas límite de NEXUS se han movido varias veces para aceptar entregas.

## Decisión

- **Copia.** Fuera del instrumento: primero se evalúa con la lista de cotejo como a cualquiera y después la calificación se multiplica por 0.5. No es un criterio del instrumento, porque mezclaría calidad con integridad.
  - Solo la copia confirmada por el docente se sanciona. "Probable" se señala para hablar con el alumno; "coincidencia por plantilla" no tiene efecto.
  - Aplica a todos los involucrados, salvo que el docente identifique a quien fue copiado y lo exente.
- **Entrega tardía.** Se acepta. La penalización queda configurable en puntos y por ahora vale 0.
  - Para saber si una entrega es tardía se usa primero la marca `Extemporanea` de NEXUS.
  - Cuando la entrega llega por formulario, se compara la fecha del archivo con la fecha límite del elemento. Si la fecha límite se movió, se usa como referencia la fecha que concentra a la mayoría de las entregas.
- **Orden de cálculo:** instrumento, luego tardanza, luego copia y al final el ajuste a una calificación válida de NEXUS (hacia arriba). Está en `dominio/integridad.py`.

## Consecuencias

- Un buen trabajo copiado obtiene la mitad de lo que vale, y uno malo copiado obtiene menos. Es más proporcional que un 5 fijo.
- La retroalimentación debe mencionar la copia por separado de los criterios.
