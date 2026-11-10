# Comandos del proyecto. Funcionan igual en Windows y Linux: `just <comando>`.
set windows-shell := ["powershell.exe", "-NoLogo", "-Command"]

# Instala dependencias y el navegador de Playwright
instalar:
    cd backend; uv sync
    cd backend; uv run playwright install chromium
    uv tool install pre-commit
    pre-commit install

# Formato y lint
lint:
    cd backend; uv run ruff format --check .
    cd backend; uv run ruff check .

# Revisión de tipos
tipos:
    cd backend; uv run pyright

# Pruebas con cobertura
test:
    cd backend; uv run pytest --cov=revisor --cov-report=term-missing

# Auditoría de seguridad: código y dependencias
auditar:
    cd backend; uv run bandit -q -r src
    cd backend; uv run pip-audit

# Todo lo que corre la integración continua
revisar: lint tipos test auditar

# Guarda la clave de Gemini en el administrador de credenciales de Windows
clave:
    cd backend; uv run python ../herramientas/guardar_clave.py

# Comprueba que Google acepta la clave guardada, sin mostrarla
verificar-clave:
    cd backend; uv run python ../herramientas/verificar_clave.py

# Registra lo que NEXUS envía al guardar una calificación (fase 0)
capturar:
    cd backend; uv run python ../herramientas/capturar_guardado.py

# Lista cursos y actividades de NEXUS (solo lectura)
listar:
    cd backend; uv run python ../herramientas/descargar.py --listar

# Descarga actividades: just descargar "Redes" 3.2 3.4
descargar curso +elementos:
    cd backend; uv run python ../herramientas/descargar.py --curso "{{curso}}" --elementos {{elementos}}

# Flujo completo de revisión con IA (no sube nada): just revisar-ia "Redes" 3.2
revisar-ia curso +elementos:
    cd backend; uv run python ../herramientas/revisar.py --curso "{{curso}}" --elementos {{elementos}}

# Importa a la base el historial validado de RNAP E1-E2
importar-rnap:
    cd backend; uv run python ../herramientas/importar_rnap.py
