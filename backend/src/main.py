from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.config.database import Base, engine
from src.config.settings import settings
import src.models  # Ensures all SQLAlchemy models are registered on Base.metadata
from src.routes.auth_routes import router as auth_router
from src.routes.user_routes import router as user_router
from src.routes.feed_routes import router as feed_router
from src.routes.buzzer_routes import router as buzzer_router
from src.routes.spree_routes import router as spree_router
from src.routes.engagement_routes import router as engagement_router
from src.routes.open_routes import router as open_router
from src.routes.membership_routes import router as membership_router
from src.routes.product_routes import router as product_router
from src.routes.order_routes import router as order_router
from src.routes.wallet_routes import router as wallet_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables on startup (only in non-testing environments)
    if settings.ENVIRONMENT != "testing":
        try:
            Base.metadata.create_all(bind=engine)
        except Exception as exc:
            import logging
            logging.getLogger("spreego").warning(f"Database startup warning: {exc}")
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="SPREEGO Clean Architecture API",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(feed_router)
app.include_router(buzzer_router)
app.include_router(spree_router)
app.include_router(engagement_router)
app.include_router(open_router)
app.include_router(membership_router)
app.include_router(product_router)
app.include_router(order_router)
app.include_router(wallet_router)



@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": settings.PROJECT_NAME, "version": settings.VERSION}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
