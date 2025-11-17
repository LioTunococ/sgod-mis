#!/bin/bash
# Simple PythonAnywhere deploy helper for sgod_mis
# - Syncs to remote HEAD
# - Activates venv
# - Installs requirements
# - Runs migrate + collectstatic (prod settings)
# - Reloads the web app

set -euo pipefail

# Config (override via env if needed)
PROJECT_HOME=${PROJECT_HOME:-"$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"}
BRANCH=${BRANCH:-main}
DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE:-sgod_mis.settings.prod}
VENV=${VENV:-"$PROJECT_HOME/.venv"}
WSGI=${WSGI:-/var/www/leinster_pythonanywhere_com_wsgi.py}

echo "[deploy] Project: $PROJECT_HOME"
echo "[deploy] Branch : $BRANCH"
echo "[deploy] Venv   : $VENV"
echo "[deploy] WSGI   : $WSGI"
echo "[deploy] Settings: $DJANGO_SETTINGS_MODULE"

cd "$PROJECT_HOME"

echo "\n[deploy] Fetching latest commits..."
git fetch --prune

echo "[deploy] Resetting to origin/$BRANCH..."
git reset --hard "origin/$BRANCH"

echo "\n[deploy] Activating virtualenv..."
if [ ! -f "$VENV/bin/activate" ]; then
  echo "[deploy][error] Cannot find venv at $VENV" >&2
  exit 1
fi
source "$VENV/bin/activate"

echo "\n[deploy] Installing requirements..."
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo "\n[deploy] Applying migrations..."
python manage.py migrate --noinput --settings="$DJANGO_SETTINGS_MODULE"

echo "\n[deploy] Collecting static files..."
python manage.py collectstatic --noinput --settings="$DJANGO_SETTINGS_MODULE"

echo "\n[deploy] Reloading web app..."
touch "$WSGI"

echo "\n[deploy] Done. Current HEAD: $(git rev-parse --short HEAD)"
echo "[deploy] Visit your site to verify: https://leinster.pythonanywhere.com"
