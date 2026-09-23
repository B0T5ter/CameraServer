#!/bin/bash
cd /home/filip/CameraServer || exit 1

# Sprawdź, czy venv istnieje, jak nie – stwórz go!
if [ ! -d ".venv" ]; then
    echo "Nie ma .venv, tworzę środowisko..."
    python3 -m venv .venv
    ./.venv/bin/pip install --upgrade pip
fi

if ! ./.venv/bin/python -c 'import cv2, flask, flask_login, ultralytics' >/dev/null 2>&1; then
    ./.venv/bin/pip install -r requirements.txt
fi
./.venv/bin/python main.py
