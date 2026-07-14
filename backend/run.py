# FB Live/Die Checker — Tác giả: @khaikhai998 | Hỗ trợ: Telegram/Facebook khaikhai998
import socket
import threading
import webbrowser

import uvicorn

from app.config import APP_NAME, APP_VERSION
from app.main import app

HOST = "127.0.0.1"


def _free_port(start: int = 8000) -> int:
    for p in range(start, start + 30):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((HOST, p))
                return p
            except OSError:
                continue
    return start


PORT = _free_port(8000)


import urllib.request
import time

def _open():
    url = f"http://{HOST}:{PORT}"
    for _ in range(30):
        try:
            urllib.request.urlopen(url + "/api/health", timeout=1)
            webbrowser.open(url)
            return
        except Exception:
            time.sleep(1)
    webbrowser.open(url)


if __name__ == "__main__":
    print(f"{APP_NAME} v{APP_VERSION} - http://{HOST}:{PORT}")
    threading.Timer(4.0, _open).start()
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")
