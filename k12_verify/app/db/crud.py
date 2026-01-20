"""
CRUD Operations for Database
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_

from .models import Teacher, Verification


# ============ TEACHER CRUD ============

def get_teacher(db: Session, teacher_id: int) -> Optional[Teacher]:
    """Get teacher by ID."""
    return db.query(Teacher).filter(Teacher.id == teacher_id).first()


def get_teacher_by_email(db: Session, email: str) -> Optional[Teacher]:
    """Get teacher by email."""
    return db.query(Teacher).filter(Teacher.email == email).first()


def get_teachers(
    db: Session, 
    district: str = None, 
    skip: int = 0, 
    limit: int = 50
) -> List[Teacher]:
    """Get teachers with optional district filter."""
    query = db.query(Teacher)
    if district:
        query = query.filter(Teacher.district == district)
    return query.offset(skip).limit(limit).all()


def get_random_teacher(db: Session, district: str = None) -> Optional[Teacher]:
    """Get random teacher for verification."""
    from sqlalchemy.sql.expression import func
    query = db.query(Teacher)
    if district:
        query = query.filter(Teacher.district == district)
    return query.order_by(func.random()).first()


def create_teacher(db: Session, **kwargs) -> Teacher:
    """Create new teacher."""
    teacher = Teacher(**kwargs)
    db.add(teacher)
    db.commit()
    db.refresh(teacher)
    return teacher


def count_teachers(db: Session, district: str = None) -> int:
    """Count teachers."""
    query = db.query(Teacher)
    if district:
        query = query.filter(Teacher.district == district)
    return query.count()


# ============ VERIFICATION CRUD ============

def create_verification(db: Session, **kwargs) -> Verification:
    """Create new verification record."""
    verification = Verification(**kwargs)
    db.add(verification)
    db.commit()
    db.refresh(verification)
    return verification


def update_verification(
    db: Session, 
    verification_id: int, 
    **kwargs
) -> Optional[Verification]:
    """Update verification record."""
    verification = db.query(Verification).filter(
        Verification.id == verification_id
    ).first()
    if verification:
        for key, value in kwargs.items():
            setattr(verification, key, value)
        db.commit()
        db.refresh(verification)
    return verification


def get_recent_verifications(
    db: Session, 
    limit: int = 20
) -> List[Verification]:
    """Get recent verifications."""
    return db.query(Verification).order_by(
        Verification.started_at.desc()
    ).limit(limit).all()
