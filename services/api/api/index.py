import os
import sys

# garante que o pacote "app" (FastAPI) seja encontrado quando a Vercel executa esta função
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app  # noqa: E402,F401
