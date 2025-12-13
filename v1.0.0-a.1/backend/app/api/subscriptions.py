# ============================================================================
# backend/app/api/subscriptions.py
# ============================================================================
"""Subscription API routes"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.subscription import Subscription
from app.dependencies import get_current_user

router = APIRouter()

@router.get("/me")
async def get_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's subscription"""
    subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.id
    ).first()
    
    if not subscription:
        # Create default free subscription
        subscription = Subscription(user_id=current_user.id, plan="free", status="active")
        db.add(subscription)
        db.commit()
        db.refresh(subscription)
    
    return {
        "plan": subscription.plan,
        "status": subscription.status,
        "current_period_end": subscription.current_period_end
    }
