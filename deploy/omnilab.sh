#!/bin/sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
deploy_dir=${OMNILAB_DEPLOY_DIR:-"$project_dir/.deploy"}
python_bin=${OMNILAB_PYTHON:-python3}
port=${PORT:-8000}
workers=${WEB_CONCURRENCY:-2}
timeout=${GUNICORN_TIMEOUT:-30}

if [ -z "${OMNILAB_DJANGO_SECRET_KEY:-}" ]; then
    echo "OMNILAB_DJANGO_SECRET_KEY must be set before deployment." >&2
    exit 64
fi

require_positive_integer() {
    value_name=$1
    value=$2
    case "$value" in
        ''|*[!0-9]*)
            echo "$value_name must be a positive integer." >&2
            exit 64
            ;;
        0)
            echo "$value_name must be greater than zero." >&2
            exit 64
            ;;
    esac
}

require_positive_integer PORT "$port"
require_positive_integer WEB_CONCURRENCY "$workers"
require_positive_integer GUNICORN_TIMEOUT "$timeout"

if ! command -v "$python_bin" >/dev/null 2>&1; then
    echo "$python_bin is required but was not found." >&2
    exit 69
fi

export OMNILAB_ENVIRONMENT=${OMNILAB_ENVIRONMENT:-production}
export OMNILAB_DATABASE_PATH=${OMNILAB_DATABASE_PATH:-"$deploy_dir/data/db.sqlite3"}
export OMNILAB_STATIC_ROOT=${OMNILAB_STATIC_ROOT:-"$deploy_dir/staticfiles"}

venv_dir="$deploy_dir/venv"
mkdir -p "$(dirname -- "$OMNILAB_DATABASE_PATH")" "$OMNILAB_STATIC_ROOT"

if [ ! -x "$venv_dir/bin/python" ]; then
    "$python_bin" -m venv "$venv_dir"
fi

cd "$project_dir"
"$venv_dir/bin/python" -m pip install \
    --disable-pip-version-check \
    --no-input \
    -r requirements.txt
"$venv_dir/bin/python" manage.py migrate --noinput
"$venv_dir/bin/python" manage.py collectstatic --noinput

exec "$venv_dir/bin/gunicorn" config.wsgi:application \
    --bind "0.0.0.0:$port" \
    --workers "$workers" \
    --timeout "$timeout" \
    --access-logfile - \
    --error-logfile -
