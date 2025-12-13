# ============================================================================
# backend/app/api/articles.py
# ============================================================================
"""Articles API routes"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_
from typing import Optional, List
from app.database import get_db
from app.models.user import User
from app.models.article import Article, ArticleTicker
from app.schemas.article import ArticleResponse, ArticleList, ArticleStats
from app.dependencies import get_current_user

router = APIRouter()

@router.get("", response_model=ArticleList)
async def list_articles(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    severity: Optional[List[str]] = Query(None),
    tickers: Optional[List[str]] = Query(None),
    search: Optional[str] = None,
    posted: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List articles with filters"""
    query = db.query(Article).filter(Article.user_id == current_user.id)
    
    if severity:
        query = query.filter(Article.severity.in_(severity))
    
    if tickers:
        ticker_ids = db.query(ArticleTicker.article_id).filter(
            ArticleTicker.user_id == current_user.id,
            ArticleTicker.ticker.in_([t.upper() for t in tickers])
        ).distinct()
        query = query.filter(Article.id.in_(ticker_ids))
    
    if search:
        query = query.filter(
            or_(
                Article.title.contains(search),
                Article.description.contains(search)
            )
        )
    
    if posted is not None:
        query = query.filter(Article.posted == posted)
    
    total = query.count()
    articles = query.order_by(desc(Article.detected_at)).offset((page - 1) * page_size).limit(page_size).all()
    
    result = []
    for art in articles:
        result.append(ArticleResponse(
            id=art.id,
            title=art.title,
            description=art.description,
            url=art.url,
            severity=art.severity,
            score=art.score,
            tickers=[t.ticker for t in art.tickers],
            published_at=art.published_at,
            detected_at=art.detected_at,
            posted=art.posted
        ))
    
    return ArticleList(
        articles=result,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )

@router.get("/stats", response_model=ArticleStats)
async def get_article_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get article statistics"""
    total = db.query(Article).filter(Article.user_id == current_user.id).count()
    high = db.query(Article).filter(Article.user_id == current_user.id, Article.severity == "HIGH").count()
    med = db.query(Article).filter(Article.user_id == current_user.id, Article.severity == "MED").count()
    low = db.query(Article).filter(Article.user_id == current_user.id, Article.severity == "LOW").count()
    unread = db.query(Article).filter(Article.user_id == current_user.id, Article.posted == 0).count()
    
    return ArticleStats(total=total, high=high, med=med, low=low, unread=unread)

@router.patch("/{article_id}/read")
async def mark_article_read(
    article_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark article as read"""
    article = db.query(Article).filter(
        Article.id == article_id,
        Article.user_id == current_user.id
    ).first()
    
    if not article:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Article not found")
    
    article.posted = 1
    db.commit()
    
    return {"message": "Article marked as read"}

