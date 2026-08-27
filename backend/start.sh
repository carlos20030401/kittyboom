#!/bin/sh
set -eu

alembic upgrade head
python -m app.create_admin

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers --forwarded-allow-ips="*"