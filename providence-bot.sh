#!/bin/bash
source .venv/bin/activate

while true; do
    echo "Lancement de main.py..."
    python src/main.py
    echo "main.py a crashé avec le code $?. Redémarrage dans 3 secondes..."
    sleep 3
done
