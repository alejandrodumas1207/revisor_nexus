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

# Registra lo que NEXUS envía al guardar una calificación (fase 0)
capturar:
    cd backend; uv run python ../herramientas/capturar_guardado.py
