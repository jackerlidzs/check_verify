"""
SQLAlchemy Models for K12 Verify
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class Teacher(Base):
    """Teacher information from K12 schools."""
    __tablename__ = "teachers"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Basic Info
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True)
    
    # School Info
    school_name = Column(String(255))
    district = Column(String(50), index=True)  # nyc_doe, miami_dade, springfield_high
    
    # Employee Info
    employee_id = Column(String(20))
    position = Column(String(255))
    department = Column(String(100))
    annual_salary = Column(Float)
    hire_date = Column(String(20))
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<Teacher {self.first_name} {self.last_name} ({self.district})>"


class Verification(Base):
    """Verification attempts log."""
    __tablename__ = "verifications"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Teacher reference
    teacher_id = Column(Integer, index=True)
    teacher_name = Column(String(200))
    teacher_email = Column(String(255))
    district = Column(String(50))
    
    # Verification details
    verification_id = Column(String(100))
    status = Column(String(20))  # pending, success, rejected, error
    document_type = Column(String(50))  # payslip, id_card, hr_system
    
    # Result
    redirect_url = Column(String(500))
    rejection_reason = Column(String(500))
    
    # Timing
    started_at = Column(DateTime, default=func.now())
    completed_at = Column(DateTime)
    duration_seconds = Column(Float)
    
    def __repr__(self):
        return f"<Verification {self.id} - {self.status}>"
