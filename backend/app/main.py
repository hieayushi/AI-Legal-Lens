"""
LegalLens AI — FastAPI application entry point
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.db.database import init_db, get_sync_db
from app.api import api_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────────────────
    logger.info("Initializing MongoDB Indexes and schemas...")
    init_db()

    # Rebuild / warm up BM25 indexes from existing pages database
    try:
        from app.services.indexing.indexer import warm_up_bm25_indexes
        sync_db = get_sync_db()
        warm_up_bm25_indexes(sync_db)
    except Exception as e:
        logger.warning(f"BM25 warm-up skipped: {e}")

    logger.info("LegalLens AI Backend lifespans verified successfully.")
    yield
    # ── Shutdown ─────────────────────────────────────────────────────────────
    logger.info("Shutting down LegalLens AI backend.")


app = FastAPI(
    title="LegalLens AI",
    description="Explainable Judicial & Governance Intelligence Platform — API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — must be added before other http middleware so it wraps outermost
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info("Incoming request %s %s", request.method, request.url)
    response = await call_next(request)
    logger.info("Response status %s for %s %s", response.status_code, request.method, request.url)
    return response

# Routes
app.include_router(api_router)



@app.get("/", include_in_schema=False)
@app.head("/", include_in_schema=False)
def root():
    return {"message": "LegalLens AI API", "version": "1.0.0", "docs": "/docs"}


@app.get("/health", tags=["health"])
@app.head("/health", tags=["health"])
def health():
    return {"status": "ok"}
