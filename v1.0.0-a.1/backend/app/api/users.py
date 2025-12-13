# ============================================================================
# backend/app/api/users.py
# ============================================================================
"""User API routes"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.schemas.user import UserResponse, UserWithSubscription
from app.dependencies import get_current_user, get_user_subscription
from app.models.subscription import Subscription

router = APIRouter()

@router.get("/me", response_model=UserWithSubscription)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
    subscription: Subscription = Depends(get_user_subscription)
):
    """Get current user profile with subscription"""
    return UserWithSubscription(
        id=current_user.id,
        email=current_user.email,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        plan=subscription.plan,
        subscription_status=subscription.status
    )
