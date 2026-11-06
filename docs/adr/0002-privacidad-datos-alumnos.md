# ADR 0002: Privacidad de datos de alumnos

Fecha: 2026-11-05. Estado: aceptado.

## Contexto

El nivel gratuito de Gemini puede usar los datos enviados para mejorar sus productos. Las entregas contienen nombre y matrícula, y en libretas escaneadas el nombre suele estar escrito a mano en la imagen.

## Decisión

- Antes de enviar, nombre y matrícula se cambian por un identificador opaco, tanto en el texto como en los nombres de archivo.
- En imágenes se ofrece recortar el encabezado de la primera página, configurable por elemento.
- Los casos marcados como sensibles se revisan solo con Claude o a mano.
- La tabla de equivalencias entre identificador y alumno vive solo en la base local.

## Riesgo aceptado

Un nombre escrito a mano fuera del encabezado puede llegar al proveedor. Si se vuelve inaceptable, se cambia a una API de pago sin uso de datos para entrenamiento mediante el mismo puerto.
