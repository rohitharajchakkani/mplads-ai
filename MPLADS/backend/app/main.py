from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import router
from app.api.intelligence import router as intelligence_router
from app.api.reviews import router as reviews_router
from app.api.benchmarking import router as benchmarking_router
from app.api.executive import router as executive_router
from app.api.ai import router as ai_router
from app.api.admin import router as admin_router
from app.core.config import get_settings

settings = get_settings()
app = FastAPI(
    title="MPLADS AI",
    description="Independent MPLADS public-data transparency platform.",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=[
        "Authorization", "Content-Type",
        "X-MPLADS-Role", "X-MPLADS-State-Scope", "X-MPLADS-District-Scope", "X-MPLADS-MP-Scope", "X-MPLADS-Actor",
        "X-Gateway-Secret",
    ],
)


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    return response


app.include_router(router, prefix=settings.api_prefix)
app.include_router(intelligence_router, prefix=settings.api_prefix)
app.include_router(reviews_router, prefix=settings.api_prefix)
app.include_router(benchmarking_router, prefix=settings.api_prefix)
app.include_router(executive_router, prefix=settings.api_prefix)
app.include_router(ai_router, prefix=settings.api_prefix)
app.include_router(admin_router, prefix=settings.api_prefix)
