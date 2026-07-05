#!/usr/bin/env bash
# Backend container entrypoint.
#
# Order matters (PRD Phase 0 healthchecks): Postgres is gated by a compose
# healthcheck, so by the time this runs the DB is accepting connections. We then
# apply Alembic migrations (added in Phase 1) before starting the server, so the
# schema is always current. In Phase 0 there are no migrations yet, so the
# upgrade step is a guarded no-op.
set -euo pipefail

if [ -f "alembic.ini" ]; then
  echo "[entrypoint] Applying database migrations..."
  alembic upgrade head || echo "[entrypoint] No migrations to apply yet."
else
  echo "[entrypoint] alembic.ini not present yet; skipping migrations (Phase 0)."
fi

# Seed the demo user/prefs/analytics (idempotent). Only when running the server,
# so one-off commands (alembic, pytest) don't trigger it.
if [ "${SEED_ON_START:-1}" = "1" ] && printf '%s' "$*" | grep -q "uvicorn"; then
  echo "[entrypoint] Seeding demo data (idempotent)..."
  python -m app.seed.seed || echo "[entrypoint] Seed skipped/failed (non-fatal)."
fi

echo "[entrypoint] Starting: $*"
exec "$@"
