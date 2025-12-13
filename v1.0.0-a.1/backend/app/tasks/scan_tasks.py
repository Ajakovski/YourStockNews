# ============================================================================
# backend/app/tasks/scan_tasks.py
# ============================================================================
"""Background scan tasks"""
from datetime import datetime
from app.tasks.celery_app import celery_app
from app.database import SessionLocal
from app.models.scan_job import ScanJob
from app.models.watchlist import Watchlist
from app.scanner.yourstocknews import run_single_scan
from app.config import settings


def run_scan_task(scan_job_id: int):
    """
    Background task to run scanner
    
    This runs synchronously in the background via Celery
    """
    db = SessionLocal()
    
    try:
        # Get scan job
        scan_job = db.query(ScanJob).filter(ScanJob.id == scan_job_id).first()
        if not scan_job:
            return
        
        # Update status to running
        scan_job.status = "running"
        scan_job.started_at = datetime.utcnow()
        db.commit()
        
        # Get watchlist and tickers
        watchlist = db.query(Watchlist).filter(Watchlist.id == scan_job.watchlist_id).first()
        if not watchlist:
            scan_job.status = "failed"
            scan_job.error_message = "Watchlist not found"
            scan_job.finished_at = datetime.utcnow()
            db.commit()
            return
        
        tickers = [t.ticker for t in watchlist.tickers]
        
        # Get last scan timestamp
        last_scan = db.query(ScanJob).filter(
            ScanJob.watchlist_id == scan_job.watchlist_id,
            ScanJob.status == "success",
            ScanJob.id != scan_job_id
        ).order_by(ScanJob.finished_at.desc()).first()
        
        last_timestamp = last_scan.last_timestamp if last_scan else None
        
        # Run scanner
        result = run_single_scan(
            user_id=scan_job.user_id,
            watchlist_id=scan_job.watchlist_id,
            tickers=tickers,
            api_key=settings.MARKETAUX_API_KEY,
            last_timestamp=last_timestamp,
            db_path=settings.DATABASE_URL.replace("sqlite:///./", "")
        )
        
        # Update scan job
        if result["status"] == "success":
            scan_job.status = "success"
            scan_job.articles_found = result["articles_found"]
            scan_job.last_timestamp = result["last_timestamp"]
        else:
            scan_job.status = "failed"
            scan_job.error_message = result.get("error", "Unknown error")
        
        scan_job.finished_at = datetime.utcnow()
        db.commit()
        
    except Exception as e:
        # Handle errors
        scan_job.status = "failed"
        scan_job.error_message = str(e)
        scan_job.finished_at = datetime.utcnow()
        db.commit()
    
    finally:
        db.close()
