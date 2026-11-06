# ADR 0004: Instrumentos propios como fuente de la calificación

Fecha: 2026-11-06. Estado: aceptado. Reemplaza lo dicho en la propuesta sobre importar la rúbrica de NEXUS como instrumento.

## Contexto

Las rúbricas de NEXUS no siempre están bien planteadas, y elementos como las Dimensiones 2 y 3 no tienen rúbrica. El docente quiere evaluar con instrumentos propios (listas de cotejo, rúbricas propias) adaptados a cada actividad.

## Decisión

- La calificación se decide solo con instrumentos propios, versionados por elemento: lista de cotejo o rúbrica propia. Ambos producen una calificación de 0 a 10.
- NEXUS solo recibe el resultado:
  - en elementos sin rúbrica, el número directo (escala 0-100 de NEXUS);
  - en elementos con rúbrica, los niveles que reproducen esa calificación, calculados con `combinacion_rubrica`. Los descriptores de los criterios de NEXUS no se toman en cuenta.
- Si la calificación del instrumento no es registrable en NEXUS (por ejemplo 3 con tres criterios de 100/70/40/0), se ajusta a una calificación válida según la política del elemento: hacia arriba (por defecto, como en nexus_tools), hacia abajo o a la más cercana. La interfaz muestra el ajuste antes de validar.
- La rúbrica de NEXUS se sigue leyendo para conocer cuántos criterios y qué porcentajes tienen sus niveles, que es lo que limita las calificaciones válidas.

## Consecuencias

- El docente puede cambiar el instrumento a mitad de la revisión sin depender de cómo se configuró la rúbrica en NEXUS.
- La retroalimentación se escribe a partir del instrumento propio, no de los descriptores de NEXUS.
