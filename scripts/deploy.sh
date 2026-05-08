#!/usr/bin/env bash
set -euo pipefail

# Deploy script for VPS + systemd.
# Default behavior:
# - Pull latest code
# - Install/update Python dependencies
# - Restart systemd service
# - Optionally run SQL seed only when --with-seed is passed
#
# Usage:
#   ./scripts/deploy.sh
#   ./scripts/deploy.sh --branch main
#   ./scripts/deploy.sh --service aritstats --with-seed
#
# Optional environment vars:
#   APP_DIR=/srv/aritstats
#   SERVICE_NAME=aritstats
#   BRANCH=<auto>
#   VENV_PATH=.venv
#   SEED_SQL_PATH=sql/todo_aritmetrica.sql

APP_DIR="${APP_DIR:-/srv/aritstats}"
SERVICE_NAME="${SERVICE_NAME:-aritstats}"
BRANCH="${BRANCH:-}"
VENV_PATH="${VENV_PATH:-.venv}"
SEED_SQL_PATH="${SEED_SQL_PATH:-sql/todo_aritmetrica.sql}"
RUN_SEED="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --with-seed)
      RUN_SEED="true"
      shift
      ;;
    --branch)
      BRANCH="${2:?Missing value for --branch}"
      shift 2
      ;;
    --service)
      SERVICE_NAME="${2:?Missing value for --service}"
      shift 2
      ;;
    --app-dir)
      APP_DIR="${2:?Missing value for --app-dir}"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

echo "==> Deploying ${APP_DIR} (service: ${SERVICE_NAME})"
cd "${APP_DIR}"

echo "==> Fetching latest changes"
git fetch --all --prune

if [[ -z "${BRANCH}" ]]; then
  if git symbolic-ref -q --short refs/remotes/origin/HEAD >/dev/null 2>&1; then
    BRANCH="$(git symbolic-ref -q --short refs/remotes/origin/HEAD | sed 's|^origin/||')"
  else
    BRANCH="$(git rev-parse --abbrev-ref HEAD)"
  fi
fi

echo "==> Using branch: ${BRANCH}"
git checkout "${BRANCH}"
git pull --ff-only origin "${BRANCH}"

if [[ ! -x "${VENV_PATH}/bin/python" ]]; then
  echo "==> Virtual environment not found in ${VENV_PATH}. Creating it."
  python3 -m venv "${VENV_PATH}"
fi

echo "==> Installing dependencies"
"${VENV_PATH}/bin/python" -m pip install --upgrade pip
"${VENV_PATH}/bin/pip" install -r requirements.txt

if [[ "${RUN_SEED}" == "true" ]]; then
  echo "==> Running SQL seed (manual mode)"
  if [[ -f "${SEED_SQL_PATH}" ]]; then
    echo "About to run ${SEED_SQL_PATH}."
    echo "This script drops and recreates project tables."
    read -r -p "Continue? (yes/no): " confirm
    if [[ "${confirm}" == "yes" ]]; then
      echo "Run this command manually with your MySQL user:"
      echo "mysql -h 127.0.0.1 -u TU_USUARIO -p < ${SEED_SQL_PATH}"
    else
      echo "Seed skipped."
    fi
  else
    echo "Seed file not found: ${SEED_SQL_PATH}"
    exit 1
  fi
fi

echo "==> Restarting systemd service"
sudo systemctl daemon-reload
sudo systemctl restart "${SERVICE_NAME}"

echo "==> Service status"
sudo systemctl --no-pager --full status "${SERVICE_NAME}" || true

echo "==> Last logs"
sudo journalctl -u "${SERVICE_NAME}" -n 50 --no-pager || true

echo "Deploy complete."
