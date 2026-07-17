from fastapi import APIRouter
from app.api.routes import auth, documents, query, analytics, eval

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(documents.router)
api_router.include_router(query.router)
api_router.include_router(analytics.router)
api_router.include_router(eval.router)
