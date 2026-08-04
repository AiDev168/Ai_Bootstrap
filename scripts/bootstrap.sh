#!/usr/bin/env bash

set -e

echo "======================================="
echo "AI Engineering Bootstrap"
echo "Environment Bootstrap"
echo "======================================="

echo
echo "[1/6] Operating System"
uname -a

echo
echo "[2/6] Python"

if command -v python3 >/dev/null 2>&1; then
    python3 --version
else
    echo "Python3 not found."
fi

echo
echo "[3/6] Git"

if command -v git >/dev/null 2>&1; then
    git --version
else
    echo "Git not found."
fi

echo
echo "[4/6] Docker"

if command -v docker >/dev/null 2>&1; then
    docker --version
else
    echo "Docker not found."
fi

echo
echo "[5/6] GPU"

if command -v nvidia-smi >/dev/null 2>&1; then
    nvidia-smi
else
    echo "No NVIDIA utility found."
fi

echo
echo "[6/6] Virtual Environment"

if [ -n "$VIRTUAL_ENV" ]; then
    echo "Virtual Environment:"
    echo "$VIRTUAL_ENV"
else
    echo "No active virtual environment."
fi

echo
echo "Bootstrap inspection completed."
