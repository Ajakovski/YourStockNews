# ============================================================================
# backend/app/tasks/celery_app.py
# ============================================================================
"""Celery application configuration"""
from celery import Celery
from app.config import settings

celery_app = Celery(
    "yourstocknews",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
