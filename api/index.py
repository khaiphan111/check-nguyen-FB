import sys
import os
import traceback
from fastapi import FastAPI

# Dummy instance for Vercel AST parser to detect this file as a FastAPI entrypoint
_dummy_app = FastAPI()

# Đảm bảo có thể import từ backend
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Set VERCEL env var
os.environ["VERCEL"] = "1"

try:
    from backend.app.main import app
except Exception as e:
    # Nếu import thất bại, tạo một app đơn giản để báo lỗi
    from fastapi import FastAPI
    app = FastAPI()
    error_msg = traceback.format_exc()
    
    @app.get("/api/health")
    @app.get("/{path:path}")
    def error_handler(path: str = ""):
        return {"ok": False, "error": error_msg}
