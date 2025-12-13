"""
Watchlist API routes
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.user import User
from app.models.watchlist import Watchlist, WatchlistTicker
from app.models.subscription import Subscription, UsageLimit
from app.schemas.watchlist import (
    WatchlistCreate, WatchlistUpdate, WatchlistResponse,
    WatchlistList, TickerAdd, TickerRemove
)
from app.dependencies import get_current_user, get_user_subscription

router = APIRouter()


@router.post("", response_model=WatchlistResponse, status_code=status.HTTP_201_CREATED)
async def create_watchlist(
    watchlist_data: WatchlistCreate,
    current_user: User = Depends(get_current_user),
    subscription: Subscription = Depends(get_user_subscription),
    db: Session = Depends(get_db)
):
    """Create a new watchlist"""
    # Check usage limits
    usage_limit = db.query(UsageLimit).filter(UsageLimit.plan == subscription.plan).first()
    current_count = db.query(Watchlist).filter(Watchlist.user_id == current_user.id).count()
    
    if current_count >= usage_limit.max_watchlists:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Watchlist limit reached ({usage_limit.max_watchlists}). Upgrade your plan."
        )
    
    # Check ticker limit
    if len(watchlist_data.tickers) > usage_limit.max_tickers_per_watchlist:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Ticker limit exceeded ({usage_limit.max_tickers_per_watchlist})"
        )
    
    # Create watchlist
    watchlist = Watchlist(user_id=current_user.id, name=watchlist_data.name)
    db.add(watchlist)
    db.commit()
    db.refresh(watchlist)
    
    # Add tickers
    for ticker in watchlist_data.tickers:
        ticker_obj = WatchlistTicker(watchlist_id=watchlist.id, ticker=ticker.upper())
        db.add(ticker_obj)
    
    db.commit()
    db.refresh(watchlist)
    
    # Return with tickers
    return WatchlistResponse(
        id=watchlist.id,
        user_id=watchlist.user_id,
        name=watchlist.name,
        tickers=[t.ticker for t in watchlist.tickers],
        created_at=watchlist.created_at,
        updated_at=watchlist.updated_at
    )


@router.get("", response_model=WatchlistList)
async def list_watchlists(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all watchlists for current user"""
    watchlists = db.query(Watchlist).filter(Watchlist.user_id == current_user.id).all()
    
    result = []
    for wl in watchlists:
        result.append(WatchlistResponse(
            id=wl.id,
            user_id=wl.user_id,
            name=wl.name,
            tickers=[t.ticker for t in wl.tickers],
            created_at=wl.created_at,
            updated_at=wl.updated_at
        ))
    
    return WatchlistList(watchlists=result, total=len(result))


@router.get("/{watchlist_id}", response_model=WatchlistResponse)
async def get_watchlist(
    watchlist_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific watchlist"""
    watchlist = db.query(Watchlist).filter(
        Watchlist.id == watchlist_id,
        Watchlist.user_id == current_user.id
    ).first()
    
    if not watchlist:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    
    return WatchlistResponse(
        id=watchlist.id,
        user_id=watchlist.user_id,
        name=watchlist.name,
        tickers=[t.ticker for t in watchlist.tickers],
        created_at=watchlist.created_at,
        updated_at=watchlist.updated_at
    )


@router.post("/{watchlist_id}/tickers", response_model=WatchlistResponse)
async def add_ticker(
    watchlist_id: int,
    ticker_data: TickerAdd,
    current_user: User = Depends(get_current_user),
    subscription: Subscription = Depends(get_user_subscription),
    db: Session = Depends(get_db)
):
    """Add ticker to watchlist"""
    watchlist = db.query(Watchlist).filter(
        Watchlist.id == watchlist_id,
        Watchlist.user_id == current_user.id
    ).first()
    
    if not watchlist:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    
    # Check ticker limit
    usage_limit = db.query(UsageLimit).filter(UsageLimit.plan == subscription.plan).first()
    current_ticker_count = len(watchlist.tickers)
    
    if current_ticker_count >= usage_limit.max_tickers_per_watchlist:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Ticker limit reached ({usage_limit.max_tickers_per_watchlist})"
        )
    
    # Add ticker
    ticker = WatchlistTicker(watchlist_id=watchlist_id, ticker=ticker_data.ticker.upper())
    db.add(ticker)
    
    try:
        db.commit()
        db.refresh(watchlist)
    except Exception:
        raise HTTPException(status_code=400, detail="Ticker already exists in watchlist")
    
    return WatchlistResponse(
        id=watchlist.id,
        user_id=watchlist.user_id,
        name=watchlist.name,
        tickers=[t.ticker for t in watchlist.tickers],
        created_at=watchlist.created_at,
        updated_at=watchlist.updated_at
    )


@router.delete("/{watchlist_id}/tickers/{ticker}")
async def remove_ticker(
    watchlist_id: int,
    ticker: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove ticker from watchlist"""
    watchlist = db.query(Watchlist).filter(
        Watchlist.id == watchlist_id,
        Watchlist.user_id == current_user.id
    ).first()
    
    if not watchlist:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    
    ticker_obj = db.query(WatchlistTicker).filter(
        WatchlistTicker.watchlist_id == watchlist_id,
        WatchlistTicker.ticker == ticker.upper()
    ).first()
    
    if not ticker_obj:
        raise HTTPException(status_code=404, detail="Ticker not found")
    
    db.delete(ticker_obj)
    db.commit()
    
    return {"message": "Ticker removed successfully"}


@router.delete("/{watchlist_id}")
async def delete_watchlist(
    watchlist_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete watchlist"""
    watchlist = db.query(Watchlist).filter(
        Watchlist.id == watchlist_id,
        Watchlist.user_id == current_user.id
    ).first()
    
    if not watchlist:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    
    db.delete(watchlist)
    db.commit()
    
    return {"message": "Watchlist deleted successfully"}