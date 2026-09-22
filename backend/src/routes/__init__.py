from src.routes.auth_routes import router as auth_router
from src.routes.user_routes import router as user_router
from src.routes.feed_routes import router as feed_router
from src.routes.buzzer_routes import router as buzzer_router
from src.routes.spree_routes import router as spree_router
from src.routes.engagement_routes import router as engagement_router

__all__ = [
    "auth_router",
    "user_router",
    "feed_router",
    "buzzer_router",
    "spree_router",
    "engagement_router",
]

