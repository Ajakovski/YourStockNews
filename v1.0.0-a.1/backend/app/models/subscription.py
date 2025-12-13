"""
Subscription and UsageLimit models
"""
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Subscription(Base):
    __tablename__ = "subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    plan = Column(String, nullable=False, default="free", index=True)  # free, pro, enterprise
    status = Column(String, nullable=False, default="active", index=True)  # active, canceled, expired, past_due
    stripe_customer_id = Column(String)
    stripe_subscription_id = Column(String)
    current_period_end = Column(DateTime)
    started_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="subscription")


class UsageLimit(Base):
    __tablename__ = "usage_limits"
    
    plan = Column(String, primary_key=True)
    max_watchlists = Column(Integer, nullable=False)
    max_tickers_per_watchlist = Column(Integer, nullable=False)
    max_scans_per_day = Column(Integer, nullable=False)
    article_history_days = Column(Integer, nullable=False)
    webhooks_enabled = Column(Boolean, default=False)
    api_access_enabled = Column(Boolean, default=False)