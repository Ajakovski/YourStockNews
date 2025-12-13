"""
Configuration management for YourStockNews backend
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    APP_NAME: str = "YourStockNews"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"  # development, staging, production
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Database
    DATABASE_URL: str = "sqlite:///./yourstocknews.db"
    
    # Security
    SECRET_KEY: str  # REQUIRED - used for JWT signing
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    
    # MarketAux API (pooled key for all users)
    MARKETAUX_API_KEY: str  # REQUIRED
    
    # Redis (for Celery)
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    
    # Stripe (for payments)
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_PUBLISHABLE_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    STRIPE_PRICE_ID_PRO: Optional[str] = None
    STRIPE_PRICE_ID_ENTERPRISE: Optional[str] = None
    
    # Email (optional)
    SENDGRID_API_KEY: Optional[str] = None
    FROM_EMAIL: Optional[str] = "noreply@yourstocknews.com"
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 60
    
    # Scanner Settings
    SCANNER_BATCH_SIZE: int = 10
    SCANNER_HIGH_THRESHOLD: float = 2.75
    SCANNER_MED_THRESHOLD: float = 1.25
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()