#!/bin/bash
cd /home/filip/CameraServer || exit 1

# Sprawdź, czy venv istnieje, jak nie – stwórz go! 🔥
if [ ! -d "venv" ]; then
    echo "Nie ma venv, robię reanimację... 🥶"
    python3 -m venv venv
    ./venv/bin/pip install --upgrade pip
    # Tutaj dopisz biblioteki, których używasz, np.:
    ./venv/bin/pip install flask opencv-python
fi

# Odpal program
./venv/bin/python main.py
