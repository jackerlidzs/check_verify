"""
Pydantic Schemas for API Request/Response
"""
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime


# ============ REQUEST SCHEMAS ============

class VerifyRequest(BaseModel):
    """Request to start verification."""
    cookies: str  # JSON string of cookies
    district: Optional[str] = None  # auto-select if not provided


class VerifyURLRequest(BaseModel):
    """Request to start verification using URL only."""
    url: str  # SheerID verification URL
    email: Optional[str] = None  # Custom email (optional)


class GenerateDocRequest(BaseModel):
    """Request to generate document."""
    teacher_id: int
    doc_type: str = "payslip"  # payslip, id_card, hr_system


# ============ RESPONSE SCHEMAS ============

class TeacherResponse(BaseModel):
    """Teacher information response."""
    id: int
    first_name: str
    last_name: str
    email: Optional[str]
    school_name: Optional[str]
    district: Optional[str]
    employee_id: Optional[str]
    position: Optional[str]
    
    class Config:
        from_attributes = True


class VerifyResponse(BaseModel):
    """Verification task response."""
    task_id: str
    status: str
    message: str


class StatusResponse(BaseModel):
    """Verification status response."""
    task_id: str
    step: int
    total_steps: int = 7
    status: str  # running, success, rejected, error
    current_action: Optional[str]
    logs: List[str] = []
    result: Optional[dict] = None


class StatsResponse(BaseModel):
    """Dashboard stats response."""
    total_teachers: int
    districts: dict
    recent_verifications: int
    success_rate: float
