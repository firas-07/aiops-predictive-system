from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.api.routes_health import router as health_router
from backend.app.api.routes_data import router as data_router
from backend.app.api.routes_training import router as training_router
from backend.app.api.routes_prediction import router as prediction_router
from backend.app.api.routes_threshold import router as threshold_router
from backend.app.api.routes_models import router as models_router
from backend.app.api.routes_applications import router as applications_router

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AIOps Predictive System"
)

# Configure CORS for React Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handler to avoid raw stack trace leaks
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception caught on {request.method} {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred. Please contact system administrator."}
    )

# Mount Real-time Application endpoints directly under /api (as requested in Section 18)
app.include_router(applications_router, prefix="/api")

# Mount API v1 routers
api_prefix = "/api/v1"
app.include_router(health_router, prefix=api_prefix)
app.include_router(data_router, prefix=api_prefix)
app.include_router(training_router, prefix=api_prefix)
app.include_router(prediction_router, prefix=api_prefix)
app.include_router(threshold_router, prefix=api_prefix)
app.include_router(models_router, prefix=api_prefix)
app.include_router(applications_router, prefix=api_prefix)

@app.get("/")
def root():
    return {
        "message": f"Welcome to {settings.app_name} API",
        "docs_url": "/docs",
        "health_check": f"{api_prefix}/health",
        "applications_url": "/api/applications"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
