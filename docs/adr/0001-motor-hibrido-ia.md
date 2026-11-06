# ADR 0001: Motor de revisión híbrido

Fecha: 2026-11-05. Estado: aceptado.

## Contexto

Revisar libretas escaneadas, notebooks y documentos consume la mayor parte del tiempo. Se busca bajo costo, personalización por curso y una validación rápida por el docente.

## Decisión

- Gemini Flash, nivel gratuito, hace la primera pasada con salida JSON validada por esquema.
- Claude, usado desde Claude Code mediante un servidor MCP local, audita los casos de baja confianza y propone instrumentos y reglas.
- El docente valida todo antes de subir.
- La personalización se logra con reglas de casos particulares aprobadas por el docente y ejemplos recuperados de correcciones previas. No se entrena un modelo propio.

## Consecuencias

- Costo de API cercano a cero, sujeto a los límites diarios de Gemini. La cola espera cuando se agota la cuota.
- El proveedor queda detrás del puerto `ProveedorIA`, así que puede cambiarse sin tocar los servicios.
- Hay riesgo de privacidad, que se trata en el ADR 0002.
