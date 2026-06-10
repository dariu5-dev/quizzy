import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from beanie import init_beanie
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from motor.motor_asyncio import AsyncIOMotorClient
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from limiter import limiter
from models import Quiz, Session
from routers import imports, quizzes, sessions

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("quizzy")

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

# Pages that are allowed to be served directly — prevents path traversal.
ALLOWED_PAGES = {"index", "create", "take", "leaderboard"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Connecting to MongoDB...")
    client = AsyncIOMotorClient(MONGO_URL)
    await init_beanie(database=client.quizzy, document_models=[Quiz, Session])
    logger.info("Connected. Quizzy is ready.")
    yield
    client.close()
    logger.info("MongoDB connection closed.")


app = FastAPI(title="Quizzy", lifespan=lifespan)

# --- Rate limiting ---
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- Compression ---
app.add_middleware(GZipMiddleware, minimum_size=1000)

# --- CORS ---
# In production set ALLOWED_ORIGINS to your actual domain, e.g. "https://quizzy.com"
allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)


# --- Security headers ---
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# --- Routers ---
app.include_router(quizzes.router)
app.include_router(sessions.router)
app.include_router(imports.router)

# --- Static files ---
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/")
async def serve_dashboard():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/{page}.html")
async def serve_page(page: str):
    # Only serve known pages — blocks path traversal attempts like ../../etc/passwd
    if page not in ALLOWED_PAGES:
        return JSONResponse({"detail": "Not found"}, status_code=404)
    return FileResponse(FRONTEND_DIR / f"{page}.html")
