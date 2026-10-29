#!/usr/bin/env bash
set -e

# Change directory to the script's location
cd "$(dirname "$0")"

# Use virtualenv python if available, otherwise python3
if [ -f "./venv/bin/python" ]; then
    PYTHON_CMD="./venv/bin/python"
elif command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
else
    echo "Error: Python was not found on your system."
    exit 1
fi

echo "Using: $($PYTHON_CMD --version)"
$PYTHON_CMD app.py
