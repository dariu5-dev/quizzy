import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from dotenv import load_dotenv

from models import Quiz, Session
from routers import quizzes, sessions, imports

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    client = AsyncIOMotorClient(MONGO_URL)
    await init_beanie(database=client.quizzy, document_models=[Quiz, Session])
    yield
    client.close()


app = FastAPI(title="Quizzy", lifespan=lifespan)

app.include_router(quizzes.router)
app.include_router(sessions.router)
app.include_router(imports.router)

app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/")
async def serve_dashboard():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/{page}.html")
async def serve_page(page: str):
    path = FRONTEND_DIR / f"{page}.html"
    if path.exists():
        return FileResponse(path)
    return FileResponse(FRONTEND_DIR / "index.html")
