#!/usr/bin/env bash
set -euo pipefail

echo "=== HomeDesigner bootstrap ==="

# --- Python (uv) ---
if ! command -v uv &>/dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi
echo "uv: $(uv --version)"

# --- Node.js (via fnm) ---
if ! command -v node &>/dev/null; then
    echo "Installing fnm + Node.js 22..."
    curl -fsSL https://fnm.vercel.app/install | bash -s -- --skip-shell
    export PATH="$HOME/.local/share/fnm:$PATH"
    eval "$(fnm env)"
    fnm install 22
    fnm use 22
else
    echo "node: $(node --version)"
fi

# --- pnpm ---
if ! command -v pnpm &>/dev/null; then
    echo "Installing pnpm..."
    npm install -g pnpm
fi
echo "pnpm: $(pnpm --version)"

# --- Tilt ---
if ! command -v tilt &>/dev/null; then
    echo "Installing Tilt..."
    curl -fsSL https://raw.githubusercontent.com/tilt-dev/tilt/master/scripts/install.sh | bash
fi
echo "tilt: $(tilt version 2>/dev/null | head -1)"

# --- Project deps ---
echo "Installing Python dependencies..."
uv python install 3.12
uv sync --python 3.12

echo "Installing frontend dependencies..."
(cd frontend/designer-next && pnpm install)

# --- Git hooks ---
git config core.hooksPath .hooks

# --- .env ---
if [ ! -f backend/.env ]; then
    cp backend/.env.example backend/.env
    echo "Created backend/.env from .env.example — fill in your API keys"
fi

echo "=== Bootstrap complete ==="
echo "Run 'make dev' or 'tilt up' to start."
