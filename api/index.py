"""Punto de entrada para Vercel: expone la app Flask como función serverless."""
import os
import sys

# Permite importar main.py y models.py desde la raíz del proyecto.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app  # noqa: E402,F401
