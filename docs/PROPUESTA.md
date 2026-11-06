# Revisor NEXUS v3: plan del proyecto

## Contexto

Hoy `C:\Users\aleja\Desktop\nexus_tools` (Python + Playwright, v2.0) ya entra a NEXUS, descarga entregas por API y sube calificaciones por la interfaz. La revisión, que es la parte crítica, se limita a detectar firmas con OpenCV y reglas fijas (10/7/0). Las libretas, los notebooks `.ipynb` y los documentos quedan para revisión manual, y la retroalimentación detallada (por ejemplo `RNAP_Revision_E1_E2\Revision_RNAP_E1_E2.xlsx`) se hizo fuera de la app. Excel funciona como base de datos, no hay git, pruebas ni tipado, y `actualizar_maestro` mezcla responsabilidades.

Objetivo: una app personal que descargue, ayude a revisar con IA bajo tu control (rúbricas, listas de cotejo y casos particulares que aprende de tus correcciones) y suba calificación y retroalimentación, con etapas que corren en paralelo y una estructura auditable.

Decisiones tomadas contigo:
- Motor híbrido: Gemini Flash gratuito para la primera pasada con datos seudonimizados, Claude (vía Claude Code, con tu suscripción) como auditor y diseñador de instrumentos, y tú validas.
- Prioridad de revisión: libretas escaneadas, notebooks `.ipynb` y documentos Word/PDF. Video y audio quedan en manual.
- Stack: Python (FastAPI) + React (TypeScript).
- Fuente de verdad: SQLite. Excel solo se exporta.

## Ubicación y reutilización

Proyecto nuevo en `C:\Users\aleja\Desktop\revisor_nexus\`. `nexus_tools` queda intacto como respaldo hasta terminar la fase 5. Los datos siguen en `Desktop\NEXUS\AD2026\` con la misma convención de carpetas, así no se descarga nada dos veces.

Código que se porta (refactorizado, con tipos y pruebas):
- `nexus_lib/sesion.py`: captura de encabezados `Token/AreaAcademicaId/RolId/SistemaId`, login único con keyring, perfil persistente `.perfil_nexus`.
- `nexus_lib/datos.py`: endpoints `Curso/ConsultarCarpetaCursos`, `Estructura/ConsultarEstructura`, `Rubrica/ConsultarRubrica`, `Portafolio/ConsultarEstudiantes`, `Portafolio/ConsultarPortafolioEstudiante`.
- `nexus_lib/maestro.py` `_descargar` y `carpeta_elemento`: organización de archivos, descompresión de zips, omitir si ya existe.
- `maestro.py` `calificaciones_validas` y `combinacion_rubrica`: qué calificaciones puede registrar NEXUS con rúbrica.
- `nexus_lib/carga.py`: selectores de carga, idempotencia por hash del comentario (hoy en la hoja `_Cargas`).
- `nexus_lib/firmas.py`: queda como una señal más dentro del motor de revisión.
- `nexus_lib/credenciales.py`: keyring. También guardará la API key de Gemini.

## Arquitectura

```
revisor_nexus/
  backend/                 Python 3.12, uv, FastAPI, SQLModel + SQLite, Playwright async
    src/revisor/
      dominio/             entidades puras: Curso, Elemento, Alumno, Entrega, Instrumento,
                           Criterio, Nivel, Revision, Sugerencia, Correccion, Carga
      puertos/             interfaces (Protocol): FuenteNexus, CargadorNexus, ProveedorIA, Extractor
      adaptadores/
        nexus_api/         lectura y descarga (portado de datos.py y sesion.py)
        nexus_ui/          carga con Playwright (portado de carga.py)
        ia/gemini.py       primera pasada, salida JSON con esquema
        ia/simulado.py     para pruebas sin red
        extractores/       pdf (pypdfium2), imagen, docx, ipynb (nbformat)
      servicios/           descarga, panorama, instrumentos, revision, auditoria, carga, exportar_excel
      trabajos/            cola con 3 trabajadores independientes
      api/                 rutas FastAPI, solo 127.0.0.1, token de sesión local
      mcp/                 servidor MCP para Claude Code (FastMCP)
    tests/                 pytest, NEXUS simulado, datos de muestra anonimizados
  frontend/                React + TypeScript + Vite, Tailwind v4, shadcn/ui (Radix),
                           TanStack Query y Router, react-pdf para el visor
  docs/adr/                decisiones de arquitectura numeradas
  CLAUDE.md                reglas del proyecto para Claude Code
```

La regla de dependencias es estricta. `dominio` no importa nada externo, los `servicios` dependen solo de `puertos`, y los `adaptadores` se conectan al arrancar. Así puedes cambiar Gemini por otro modelo, o la carga por UI por carga por API, sin tocar la lógica. Se sigue la skill `proyectos-ml-buenas-practicas` para el empaquetado.

## Flujo y paralelismo

Tres trabajadores comparten la base de datos y corren al mismo tiempo:

1. **Descarga**: usa la API JSON con `httpx` async (varias descargas simultáneas, con un límite cortés). No ocupa la ventana del navegador.
2. **Revisión IA**: toma entregas nuevas en cuanto llegan y respeta los límites de Gemini (unas 1,000 solicitudes diarias, con ritmo por minuto). Si se agota la cuota, la entrega queda en espera y no falla.
3. **Carga**: un solo navegador Playwright sube lo que validaste, alumno por alumno, mientras sigues revisando otros.

Como la descarga va por API y la carga por la interfaz, ambas pueden convivir con la misma sesión. En la fase 0 se investigará qué endpoint llama NEXUS al guardar calificación y retroalimentación. Si se puede usar directamente, la carga pasa a ser por API: mucho más rápida y sin depender de selectores, tamaños de ventana ni esperas fijas.

Estados de una entrega: `descargada → extraída → sugerida (IA) → auditada (Claude, opcional) → validada (tú) → subida`. Nada se sube sin tu validación.

## Motor de revisión (la parte crítica)

**1. Extracción.** PDF y fotos se convierten en imágenes por página, más texto si lo tienen. De DOCX se toman texto e imágenes incrustadas. De `.ipynb` se toman celdas de código, markdown y salidas. Se calculan huellas para duplicados.

**2. Identificación de la actividad.** Cada elemento tiene una "ficha" con título, consigna, palabras o ejercicios esperados y ejemplos. La IA indica si la entrega corresponde a esa actividad, a otra, o si está incompleta, con la página o celda como evidencia. Esto detecta casos como el notebook subido en la actividad equivocada.

**3. Panorama previo.** Antes de revisar, la app toma una muestra de entregas (por ejemplo 8 a 12, variadas) y genera un resumen: qué parece pedir la actividad, la estructura común, entregas atípicas, extensión típica y una propuesta de lista de cotejo o rúbrica. Sirve para refrescarte la memoria si no recuerdas la actividad.

**4. Instrumentos.** Se guardan rúbricas y listas de cotejo versionadas por elemento, con criterios, descriptores por nivel, peso y reglas especiales. La calificación sale solo de estos instrumentos propios; NEXUS recibe el número final o, si el elemento tiene rúbrica, los niveles que lo reproducen (ADR 0004). De la rúbrica de NEXUS solo se leen el número de criterios y los porcentajes de sus niveles, que limitan las calificaciones registrables. Puedes crearlos desde cero, desde el panorama, desde plantillas (por ejemplo "libreta de inglés estándar") o ajustarlos en medio de la revisión. Al cambiar un instrumento se recalculan las sugerencias no validadas.

**5. Primera pasada (Gemini Flash).** Por cada entrega devuelve JSON validado con Pydantic: nivel por criterio, evidencia citada (página o celda), confianza, calificación calculada (ajustada a las calificaciones válidas de NEXUS) y retroalimentación en tu estilo. Antes de enviar, el nombre y la matrícula se cambian por un identificador. En libretas escaneadas el nombre escrito a mano puede aparecer en la imagen. Se ofrece recortar el encabezado de la primera página y queda documentado como riesgo aceptado (ADR).

**6. Aprendizaje sobre la marcha, sin entrenar un modelo.** Cada vez que corriges una sugerencia se guarda la corrección: criterio, sugerencia, decisión final y motivo opcional. Con eso se construyen dos cosas:
- una **biblioteca de casos particulares** en forma de reglas en lenguaje natural ("si resolvió en hoja suelta pegada, cuenta como completo"), que tú apruebas y que se inyectan en el prompt de ese curso o elemento;
- **ejemplos de referencia** (few-shot) recuperados por similitud para entregas parecidas.

Esto da personalización real con modelos gratuitos y es auditable, porque cada regla es visible y editable. Entrenar un modelo propio no compensa con el volumen de un docente.

**7. Plagio y duplicados.** Para notebooks: código normalizado, n-gramas y similitud entre pares, con grupos sospechosos. Para imágenes: hash perceptual para fotos idénticas o casi idénticas. Las coincidencias se marcan y nunca se califican solas.

**8. Triaje por confianza.**
- Confianza alta y sin alertas: va a "aprobación rápida", donde ves la tarjeta y confirmas con una tecla.
- Confianza baja, desacuerdo con reglas, plagio o actividad equivocada: va a "auditoría Claude" y a tu revisión detallada.

**9. Conexión con Claude.** El backend expone un servidor MCP con herramientas como `listar_pendientes`, `ver_entrega`, `ver_instrumento`, `proponer_revision`, `proponer_instrumento` y `proponer_regla`. Desde Claude Code, abierto en la carpeta del proyecto, pides por ejemplo "audita los casos dudosos del 2.3 de CIITI". Claude lee las entregas y escribe propuestas marcadas como "Claude", que aparecen en la interfaz para que las aceptes. No hay costo extra de API, y Claude nunca sube calificaciones directamente.

**10. Procedencia.** Cada calificación guarda quién la propuso (regla, Gemini, Claude o tú), la versión del instrumento, la versión del prompt y el modelo. Así cualquier calificación se puede explicar y auditar.

## Interfaz (UX/UI)

Pantallas:
- **Inicio**: cursos y elementos con conteos por estado y la actividad de los tres trabajadores en vivo.
- **Panorama**: resumen del elemento y editor del instrumento.
- **Revisión**: visor del documento a la izquierda, con saltos a la evidencia citada. A la derecha, criterios con el nivel sugerido, retroalimentación editable y alertas. Atajos de teclado (número de nivel, Enter para validar, J/K para navegar).
- **Aprobación rápida**: cuadrícula de tarjetas para validar en bloque.
- **Carga**: cola, vista previa en modo prueba y bitácora.

Criterios de diseño para evitar el aspecto genérico de IA:
- tokens de diseño definidos (escala tipográfica, espaciado de 4 px, paleta neutra con un solo color de acento, Radix Colors);
- tipografía de sistema o Inter/Geist;
- sin degradados decorativos, emojis ni tarjetas con sombras exageradas;
- densidad de información pensada para trabajo repetitivo, como Linear;
- estados vacíos y de error escritos para ti, modo oscuro y foco visible para teclado.

Antes de construir se valida un prototipo de la pantalla de revisión.

## Calidad, seguridad y auditoría

- **Herramientas**: instalar git (hoy no está), con commits pequeños y convencionales. `uv`, `ruff`, `pyright` en modo estricto en `dominio` y `servicios`, `pytest` con cobertura en servicios. Frontend con ESLint/Biome, Vitest y tipos generados del OpenAPI de FastAPI. `pre-commit` corre todo esto.
- **Seguridad**:
  - servidor solo en `127.0.0.1` con token local y validación de rutas (como hace hoy `app.py`);
  - credenciales y API keys solo en keyring, nunca en archivos ni en logs;
  - los logs ocultan nombres y matrículas;
  - `pip-audit`, `npm audit` y `bandit` en pre-commit;
  - el contenido de las entregas se trata como dato, nunca como instrucción para la IA (defensa contra prompt injection, por ejemplo un alumno que escriba "ponme 10").
- **Pruebas sin tocar NEXUS**: adaptador NEXUS simulado (reemplaza el `NEXUS_SIMULAR` que falta) y respuestas grabadas de la API.
- **Revisiones de código**: `/code-review` y `/security-review` al cerrar cada fase. Las decisiones relevantes van en `docs/adr/`.

## Fases

| Fase | Entregable |
|---|---|
| 0. Arranque e investigación | Repo, herramientas y CLAUDE.md. Captura del endpoint de guardado de NEXUS. Prueba de Gemini con 10 entregas reales anonimizadas (libreta, notebook y PDF). |
| 1. Núcleo | Dominio, SQLite y migraciones (Alembic). Sesión, lectura y descarga portadas. Importación de los maestros `.xlsx` y del workbook de RNAP como historial. |
| 2. Revisión manual con instrumentos | Interfaz de revisión completa, editor de rúbricas y listas, calificaciones válidas de NEXUS y exportación a Excel. Ya es útil sin IA. |
| 3. Motor IA | Extractores, identificación, panorama, primera pasada con Gemini, triaje y detector de plagio. |
| 4. Personalización y Claude | Memoria de correcciones, biblioteca de casos particulares y servidor MCP para Claude. |
| 5. Carga y paralelismo | Carga por API si la fase 0 lo permitió, si no por interfaz endurecida. Los tres trabajadores en paralelo. Retiro de `nexus_tools`. |
| 6. Endurecimiento | Auditoría de seguridad, métricas de concordancia y documentación de uso. |

## Verificación

- **Concordancia IA contra docente**: usar `Revision_RNAP_E1_E2.xlsx` (unos 100 notebooks ya calificados a mano) y las calificaciones de CIITI e IPER ya existentes en NEXUS. Se miden acuerdo exacto, acuerdo ±1 y kappa ponderado por criterio. Meta inicial: ±1 en al menos 85% antes de usar la aprobación rápida.
- **Pruebas unitarias e integración** con NEXUS simulado: descarga idempotente, cálculo de calificaciones válidas y carga sin duplicados.
- **Prueba en vivo controlada**: carga en modo prueba sobre un elemento y un alumno, comprobación en NEXUS, y luego el grupo completo.
- **Prueba de paralelismo**: descargar un elemento nuevo mientras se sube otro ya validado, revisando la bitácora y la consistencia de la base.
