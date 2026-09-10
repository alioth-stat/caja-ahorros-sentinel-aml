#!/usr/bin/env bash
# Sets up (if needed) and runs the backend + frontend dev servers together.
set -euo pipefail
cd "$(dirname "$0")"

# Check for the actual binary, not just the directory -- a venv left behind
# by a prior failed install would otherwise pass a bare `-d .venv` check and
# get silently skipped forever, with no fastapi/uvicorn ever installed into it.
if [ ! -x .venv/bin/uvicorn ]; then
    echo "Creando entorno virtual e instalando dependencias de Python..."
    [ -d .venv ] || python3 -m venv .venv
    .venv/bin/pip install -q -r requirements.txt
fi

if [ ! -d frontend/node_modules ]; then
    echo "Instalando dependencias del frontend..."
    (cd frontend && npm install)
fi

# ponytail: this workspace runs several sibling challenge repos side by side,
# each defaulting to the same 8000/5173 pair -- auto-pick the next free port
# instead of colliding, but still let BACKEND_PORT/FRONTEND_PORT override.
port_in_use() {
    (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null
}
find_free_port() {
    local port=$1
    while port_in_use "$port"; do
        port=$((port + 1))
    done
    echo "$port"
}

BACKEND_PORT="${BACKEND_PORT:-$(find_free_port 8000)}"
FRONTEND_PORT="${FRONTEND_PORT:-$(find_free_port 5173)}"

cleanup() {
    echo "Deteniendo servidores..."
    fuser -k "${BACKEND_PORT}/tcp" "${FRONTEND_PORT}/tcp" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

.venv/bin/uvicorn api:app --port "$BACKEND_PORT" &
(cd frontend && VITE_BACKEND_PORT="$BACKEND_PORT" npm run dev -- --port "$FRONTEND_PORT" --strictPort) &

echo ""
echo "Backend:  http://localhost:${BACKEND_PORT}"
echo "Frontend: http://localhost:${FRONTEND_PORT}"
echo "(Ctrl+C para detener ambos)"

wait
