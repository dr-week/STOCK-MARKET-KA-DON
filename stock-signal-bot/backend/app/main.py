import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.paper_trading.auto_runner import paper_auto_runner


@asynccontextmanager
async def lifespan(_app: FastAPI):
    paper_auto_runner.start()
    try:
        yield
    finally:
        paper_auto_runner.stop()


app = FastAPI(title="NSE Signal Engine", version="2.0.0", lifespan=lifespan)


@app.get("/")
def root() -> dict:
    return {
        "app": "SMKD",
        "service": "NSE Signal Engine",
        "status": "running",
        "api_prefix": "/api",
        "docs_url": "/docs",
    }


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "NSE Signal Engine",
        "version": app.version,
    }


default_origins = [
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "http://127.0.0.1:5174",
    "http://localhost:5174",
    "http://127.0.0.1:4173",
    "http://localhost:4173",
    "http://tauri.localhost",
    "https://dr-week.github.io",
]

env_origins = os.getenv("SMKD_ALLOWED_ORIGINS", "")
if env_origins:
    configured_origins = default_origins + [o.strip() for o in env_origins.split(",") if o.strip()]
else:
    configured_origins = default_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=configured_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0" if os.getenv("PORT") else "127.0.0.1")
    uvicorn.run("app.main:app", host=host, port=port, reload=True)

