from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime

# Authentication
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    name: str
    study_hours_per_week: int = 10
    academic_goal: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(BaseModel):
    student_id: int
    email: str
    name: str
    study_hours_per_week: int
    academic_goal: Optional[str]

class Token(BaseModel):
    access_token: str
    token_type: str
    user: User

# Course Material Upload
class MaterialUploadResponse(BaseModel):
    message: str
    course_name: str
    files_processed: int

# Study Plan
class WeeklyPlan(BaseModel):
    week_number: int
    topics: str
    allocated_hours: int

class StudyPlanResponse(BaseModel):
    plan_id: int
    course_name: str
    weeks: List[WeeklyPlan]

class PlanGenerateRequest(BaseModel):
    course_name: str
    syllabus_content: Optional[str] = None
    exam_timeline: Optional[str] = None

# RAG Question Answering
class QuestionRequest(BaseModel):
    course_name: str
    question: str

class AnswerResponse(BaseModel):
    answer: str
    sources: List[str]
    relevant_chunks: int

# Quiz Generation
class QuizQuestion(BaseModel):
    question: str
    options: List[str]
    correct_index: int

class QuizResponse(BaseModel):
    topic: str
    questions: List[QuizQuestion]
    difficulty_level: str

class QuizGenerateRequest(BaseModel):
    course_name: str
    topic: str
    difficulty: Optional[str] = "adaptive"  # adaptive, easy, medium, hard

class QuizSubmitRequest(BaseModel):
    quiz_topic: str
    answers: List[int]
    correct_answers: List[int]

# Mastery Tracking
class MasteryUpdate(BaseModel):
    topic: str
    mastery_score: float
    attempts: int

class MasteryResponse(BaseModel):
    topic: str
    mastery_score: float
    attempts: int
    recommendation: str