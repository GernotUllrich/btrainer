#!/usr/bin/env bash
# Source this file to configure the local development environment.
#   source scripts/env.sh
# Add "source $(pwd)/scripts/env.sh" to your shell configuration or use direnv.

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="$PROJECT_ROOT"

: "${BTRAINER_DATABASE_URL:=postgresql+psycopg://localhost/btrainer}"
export BTRAINER_DATABASE_URL

echo "PYTHONPATH=$PYTHONPATH"
echo "BTRAINER_DATABASE_URL=$BTRAINER_DATABASE_URL"
