# FB Live/Die Checker & Tiktok Checker
import os

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from . import config, db
from .api import router as api_router
from .bot import manager, zalo_manager
from .poller import poller

app = FastAPI(title=config.APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.on_event("startup")
async def on_startup():
    db.init_db()
    db.migrate_db()
    
    token = db.get_setting("bot_token")
    zalo_token = db.get_setting("zalo_bot_token")
    
    started_any = False
    if token and db.get_setting("setup_done") == "1":
        if await manager.start(token):
            started_any = True
            
    if zalo_token:
        if await zalo_manager.start(zalo_token):
            started_any = True
            
    if started_any:
        poller.start()


@app.on_event("shutdown")
async def on_shutdown():
    await poller.stop()
    await manager.stop()
    await zalo_manager.stop()


@app.get("/api/health")
def health():
    return {"ok": True, "app": config.APP_NAME, "version": config.APP_VERSION}


if os.path.isdir(config.STATIC_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(config.STATIC_DIR, "assets")), name="assets")
    images_dir = os.path.join(os.path.dirname(__file__), "..", "data", "images")
    if not os.path.isdir(images_dir):
        os.makedirs(images_dir, exist_ok=True)
    app.mount("/images", StaticFiles(directory=images_dir), name="images")

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        if full_path.startswith("api/"):
            return JSONResponse({"detail": "Not found"}, status_code=404)
        index = os.path.join(config.STATIC_DIR, "index.html")
        if os.path.isfile(index):
            return FileResponse(index)
        return JSONResponse({"detail": "Frontend chưa build"}, status_code=404)
