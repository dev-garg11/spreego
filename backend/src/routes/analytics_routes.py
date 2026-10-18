from datetime import datetime, timedelta, timezone
from typing import Any, List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.middlewares.auth_middleware import get_current_user
from src.models.engagement import SpreeView
from src.models.follow import Follow
from src.models.spree import Spree
from src.models.user import User


router = APIRouter(prefix="/api/v1/analytics", tags=["Creator Analytics"])


def _creator_sprees(db: Session, user_id: str) -> List[Spree]:
    return db.query(Spree).filter(Spree.creator_id == user_id).all()


def _compact(value: int) -> str:
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"{value / 1_000:.1f}K"
    return str(value)


@router.get("/kpi", response_model=List[dict[str, Any]])
def get_kpi_metrics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[dict[str, Any]]:
    sprees = _creator_sprees(db, current_user.id)
    views = sum(len(spree.views) for spree in sprees)
    engagements = sum(
        len(spree.claps) + len(spree.comments) + len(spree.saves) + len(spree.shares)
        for spree in sprees
    )
    followers = db.query(Follow).filter(Follow.following_id == current_user.id).count()
    return [
        {"label": "Total Views", "value": _compact(views), "growth_percent": 0, "is_positive": True},
        {"label": "Engagement", "value": _compact(engagements), "growth_percent": 0, "is_positive": True},
        {"label": "New Followers", "value": _compact(followers), "growth_percent": 0, "is_positive": True},
    ]


@router.get("/views-trend", response_model=List[dict[str, Any]])
def get_views_trend(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[dict[str, Any]]:
    sprees = _creator_sprees(db, current_user.id)
    spree_ids = [spree.id for spree in sprees]
    now = datetime.now(timezone.utc)
    points: List[dict[str, Any]] = []
    for offset in range(6, -1, -1):
        day = (now - timedelta(days=offset)).date()
        start = datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc)
        end = start + timedelta(days=1)
        count = 0
        if spree_ids:
            count = (
                db.query(SpreeView)
                .filter(
                    SpreeView.spree_id.in_(spree_ids),
                    SpreeView.created_at >= start,
                    SpreeView.created_at < end,
                )
                .count()
            )
        points.append({"day": day.strftime("%a"), "views": count, "formatted_views": _compact(count)})
    return points


@router.get("/top-content", response_model=List[dict[str, Any]])
def get_top_content(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[dict[str, Any]]:
    sprees = sorted(_creator_sprees(db, current_user.id), key=lambda spree: len(spree.views), reverse=True)
    return [
        {
            "rank": index,
            "title": spree.title,
            "views_display": _compact(len(spree.views)),
            "likes_display": _compact(len(spree.claps)),
            "thumbnail_url": spree.thumbnail_url or spree.media_url,
        }
        for index, spree in enumerate(sprees[:10], start=1)
    ]
