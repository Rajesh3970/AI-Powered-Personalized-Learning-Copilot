from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Text, Float, Boolean, TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:jake@localhost:5432/learning_copilot")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# =============================================================================
# Database Schema - EXACTLY as per documentation
# =============================================================================

class StudentProfile(Base):
    """Student_Profile table from documentation"""
    __tablename__ = "student_profile"
    
    student_id = Column(Integer, primary_key=True, autoincrement=True)
    study_hours_per_week = Column(Integer, nullable=False)
    academic_goal = Column(Text)
    consent = Column(Boolean, default=True)
    
    # Additional fields for authentication
    email = Column(String, unique=True, index=True)
    name = Column(String)
    hashed_password = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    study_plans = relationship("StudyPlan", back_populates="student")
    mastery_tracker = relationship("MasteryTracker", back_populates="student")
    quiz_history = relationship("QuizHistory", back_populates="student")


class StudyPlan(Base):
    """Study_Plan table from documentation"""
    __tablename__ = "study_plan"
    
    plan_id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("student_profile.student_id"))
    week_number = Column(Integer)
    topics = Column(Text)
    allocated_hours = Column(Integer)
    
    # Additional metadata
    course_name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    student = relationship("StudentProfile", back_populates="study_plans")


class MasteryTracker(Base):
    """Mastery_Tracker table from documentation"""
    __tablename__ = "mastery_tracker"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("student_profile.student_id"))
    topic = Column(Text)
    mastery_score = Column(Float)  # 0.0 to 1.0
    attempts = Column(Integer, default=0)
    
    # Additional metadata
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    student = relationship("StudentProfile", back_populates="mastery_tracker")


class QuizHistory(Base):
    """Quiz_History table from documentation"""
    __tablename__ = "quiz_history"
    
    quiz_id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("student_profile.student_id"))
    topic = Column(Text)
    score = Column(Float)
    timestamp = Column(TIMESTAMP, default=datetime.utcnow)
    
    # Additional fields
    total_questions = Column(Integer)
    correct_answers = Column(Integer)
    
    # Relationships
    student = relationship("StudentProfile", back_populates="quiz_history")


# Course materials metadata (not in doc, but needed for file management)
class CourseMaterial(Base):
    __tablename__ = "course_material"
    
    material_id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("student_profile.student_id"))
    course_name = Column(String)
    file_name = Column(String)
    file_path = Column(String)
    uploaded_at = Column(DateTime, default=datetime.utcnow)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully")
