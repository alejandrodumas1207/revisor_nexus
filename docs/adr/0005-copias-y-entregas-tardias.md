# ADR 0005: Copias y entregas tardías

Fecha: 2026-11-06. Estado: aceptado.

## Contexto

En RNAP E1-E2 hubo copias confirmadas y varios alumnos con 0 por "no se registró entrega" que en realidad entregaron tarde por formulario. Antes, una copia bajaba la calificación a 5 (50 de 100) sin importar la calidad del trabajo. Las fechas límite de NEXUS se han movido varias veces para aceptar entregas.

## Decisión

- **Copia.** Fuera del instrumento: primero se evalúa con la lista de cotejo como a cualquiera y después la calificación se multiplica por 0.5. No es un criterio del instrumento, porque mezclaría calidad con integridad.
  - Se sancionan la copia confirmada (× 0.5) y la copia parcial (× 0.85), siempre validadas por el docente; la sospecha solo se señala (ver veredictos abajo).
  - Aplica a todos los involucrados, salvo que el docente identifique a quien fue copiado y lo exente.
- **Qué cuenta como copia (2026-11-06).** Una plantilla compartida hace que el código se parezca, y eso no es copia. Son indicadores de copia:
  - redacción igual o casi igual en las respuestas escritas;
  - mismos datos o decisiones que cada alumno debía producir por su cuenta (valores elegidos, números de su propia tabla, la misma combinación recomendada sin que salga de sus resultados);
  - errores idiosincrásicos compartidos: las mismas faltas de ortografía, espacios dobles, signos mal puestos, nombres de variables raros o residuos de código idénticos;
  - datos de otro alumno dentro del archivo (matrícula, nombre o salidas que no corresponden).

  Valores iguales (2026-11-08). Las plantillas fijan la semilla aleatoria, así que con las mismas decisiones los resultados salen idénticos:
  - Resultados obtenidos con semilla fija (exactitudes, parámetros, conteos) nunca son evidencia, salvo que el alumno cite un número que no sale de su cuaderno y sí del de otro.
  - Decisiones libres (valores elegidos, recomendaciones): se cuenta cuántos alumnos del grupo comparten cada valor (`valores_compartidos`). Con 3 o más es una opción guiada por la actividad y no cuenta; compartida solo por el par, o con un detalle raro (orden, formato, mismo error), sí es indicio.
  - La redacción sigue siendo el indicador principal.

  Veredictos (2026-11-08), según gravedad y certeza:
  - **Copia confirmada:** copió todo o casi todo (palabra por palabra, o los mismos datos y errores en muchas partes). × 0.5.
  - **Copia parcial:** casi seguro que copió una parte, aunque sea poca o parafraseada (una o dos respuestas). × 0.85: una penalización menor que deja claro que se detectó.
  - **Sospecha:** similitudes que pueden explicarse por coincidencia, por haber hablado entre ellos o por la plantilla (por ejemplo, el mismo valor erróneo y una recomendación común). Sin penalización; se menciona al alumno con el nombre del compañero y el motivo, y el docente decide.
  - **Coincidencia por plantilla:** no es copia y no se muestra.

  El factor se aplica después de evaluar con la lista. La retroalimentación explica el veredicto en los comentarios generales: con quién (nombre y matrícula) y por qué, con evidencia concreta.

- **Entrega tardía.** Se acepta y resta 1 punto de 10, **solo cuando la tardanza es segura** (`Tardanza.CONFIRMADA`). Si hay duda (por ejemplo, la fecha límite se movió y no se sabe cuál regía), la entrega queda como `DUDOSA`: no se penaliza y se le muestra al docente para que decida.
  - Para saber si una entrega es tardía se usa primero la marca `Extemporanea` de NEXUS.
  - Cuando la entrega llega por formulario, se compara la fecha del archivo con la fecha límite del elemento. Si la fecha límite se movió, se usa como referencia la fecha que concentra a la mayoría de las entregas.
- **Formato de entrega.** No es criterio de la lista de cotejo. Entregar otro tipo de archivo (.txt, .pdf, .zip en lugar de .ipynb) resta 1 punto de 10, una cantidad simbólica que se nota en NEXUS. Un nombre de archivo incorrecto no se penaliza; solo se avisa en la retroalimentación.
- **Orden de cálculo:** instrumento, luego formato, luego tardanza, luego copia y al final el ajuste a una calificación válida de NEXUS (hacia arriba). Está en `dominio/integridad.py`.

- **El docente decide (2026-11-08).** Formato, tardanza y copia son recomendaciones de la revisión. El docente las marca o desmarca por alumno; su decisión sustituye a la recomendación (`DecisionDocente`, `integridad_vigente`) y la calificación y la retroalimentación se recalculan con lo vigente. Si quita una copia, desaparece de la retroalimentación; si la marca sin justificación previa, se indica que la determinó el docente. Mientras no exista la interfaz, se marca en las columnas "(aplicar)" del Excel de revisión.

## Consecuencias

- Un buen trabajo copiado obtiene la mitad de lo que vale, y uno malo copiado obtiene menos. Es más proporcional que un 5 fijo.
- La retroalimentación debe mencionar la copia por separado de los criterios.
