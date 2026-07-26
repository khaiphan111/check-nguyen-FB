import sys
import os

# Đảm bảo có thể import từ backend
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from backend.app.main import app
