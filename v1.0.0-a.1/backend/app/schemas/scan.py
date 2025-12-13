"""
Scan job schemas
"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict


class ScanTrigger(BaseModel):
    """Trigger new scan"""
    watchlist_id: int


class ScanJobResponse(BaseModel):
    """Scan job status response"""
    id: int
    user_id: int
    watchlist_id: int
    status: str
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    articles_found: int
    last_timestamp: Optional[str]
    error_message: Optional[str]
    
    class Config:
        from_attributes = True


class ScanJobList(BaseModel):
    """List of scan jobs"""
    scan_jobs: list[ScanJobResponse]
    total: int


class ScanResult(BaseModel):
    """Scan result from scanner"""
    status: str
    articles_found: int
    severity_counts: Dict[str, int]
    last_timestamp: str
    error: Optional[str] = None