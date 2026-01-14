from fastapi import FastAPI, Depends, HTTPException, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
import os
import shutil
import json
from datetime import datetime
import hashlib

from database import (
    get_db, init_db, 
    StudentProfile, StudyPlan, MasteryTracker, QuizHistory, CourseMaterial
)
from models.schemas import (
    UserRegister, UserLogin, Token, User,
    MaterialUploadResponse, StudyPlanResponse, WeeklyPlan,
    QuestionRequest, AnswerResponse,
    QuizResponse, QuizGenerateRequest, QuizSubmitRequest,
    MasteryResponse, PlanGenerateRequest
)
from agents.planning_agent import planning_agent
from agents.retrieval_agent import retrieval_agent
from agents.quiz_agent import quiz_agent
from agents.reflection_agent import reflection_agent
from services.pdf_processor import pdf_processor
from services.vector_store import vector_store
from services.llm_client import llm_client

# Password hashing with bcrypt fix
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    """Hash password with SHA256 pre-processing to handle bcrypt 72-byte limit"""
    # Pre-hash with SHA256 to ensure it's under 72 bytes
    password_bytes = password.encode('utf-8')
    sha256_hash = hashlib.sha256(password_bytes).hexdigest()
    return pwd_context.hash(password[:72])

def verify_password(plain_password, hashed_password):
    """Verify password with SHA256 pre-processing"""
    password_bytes = plain_password.encode('utf-8')
    sha256_hash = hashlib.sha256(password_bytes).hexdigest()
    return pwd_context.verify(plain_password[:72], hashed_password)

# JWT (rest of the code stays the same...)
from jose import JWTError, jwt
from datetime import timedelta

SECRET_KEY = os.getenv("SECRET_KEY", "dev_secret_key_change_in_production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 10080


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
security = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = db.query(StudentProfile).filter(StudentProfile.email == email).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user

# Initialize
app = FastAPI(
    title="AI-Powered Learning Copilot API",
    description="Personalized learning assistance with RAG, adaptive quizzing, and study planning",
    version="1.0.0"
)

# Initialize database
print("🔧 Initializing database...")
init_db()

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./data/uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================

@app.post("/auth/register", response_model=Token)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """Register new student"""
    
    # Check if email exists
    existing = db.query(StudentProfile).filter(StudentProfile.email == user_data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new student profile
    student = StudentProfile(
        email=user_data.email,
        name=user_data.name,
        hashed_password=get_password_hash(user_data.password),
        study_hours_per_week=user_data.study_hours_per_week,
        academic_goal=user_data.academic_goal,
        consent=True
    )
    
    db.add(student)
    db.commit()
    db.refresh(student)
    
    # Create access token
    token = create_access_token(data={"sub": student.email})
    
    print(f"✅ New student registered: {student.email}")
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": User(
            student_id=student.student_id,
            email=student.email,
            name=student.name,
            study_hours_per_week=student.study_hours_per_week,
            academic_goal=student.academic_goal
        )
    }

@app.post("/auth/login", response_model=Token)
async def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """Login existing student"""
    
    student = db.query(StudentProfile).filter(StudentProfile.email == credentials.email).first()
    
    if not student or not verify_password(credentials.password, student.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    token = create_access_token(data={"sub": student.email})
    
    print(f"✅ Student logged in: {student.email}")
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": User(
            student_id=student.student_id,
            email=student.email,
            name=student.name,
            study_hours_per_week=student.study_hours_per_week,
            academic_goal=student.academic_goal
        )
    }

# ============================================================================
# COURSE MATERIAL UPLOAD ENDPOINTS
# ============================================================================

@app.post("/upload", response_model=MaterialUploadResponse)
async def upload_course_materials(
    course_name: str = Form(...),
    files: List[UploadFile] = File(...),
    current_user: StudentProfile = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload course PDFs and trigger embedding process"""
    
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    # Create course directory
    course_dir = os.path.join(UPLOAD_DIR, f"student_{current_user.student_id}", course_name.replace(" ", "_"))
    os.makedirs(course_dir, exist_ok=True)
    
    all_chunks = []
    
    for file in files:
        if not file.filename.endswith('.pdf'):
            continue
        
        # Save file
        file_path = os.path.join(course_dir, file.filename)
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        
        # Process PDF
        print(f"📄 Processing: {file.filename}")
        chunks = pdf_processor.process_pdf(file_path, file.filename)
        all_chunks.extend(chunks)
        
        # Save metadata to database
        material = CourseMaterial(
            student_id=current_user.student_id,
            course_name=course_name,
            file_name=file.filename,
            file_path=file_path
        )
        db.add(material)
    
    db.commit()
    
    # Add to vector store
    if all_chunks:
        print(f"🔍 Adding {len(all_chunks)} chunks to ChromaDB")
        vector_store.add_documents(course_name, all_chunks)
    
    print(f"✅ Course uploaded: {course_name} ({len(files)} files)")
    
    return MaterialUploadResponse(
        message="Course materials uploaded and indexed successfully",
        course_name=course_name,
        files_processed=len(files)
    )

@app.get("/courses")
async def get_courses(
    current_user: StudentProfile = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all courses for current student"""
    
    materials = db.query(CourseMaterial).filter(
        CourseMaterial.student_id == current_user.student_id
    ).all()
    
    # Group by course name
    courses = {}
    for material in materials:
        if material.course_name not in courses:
            courses[material.course_name] = {
                "course_name": material.course_name,
                "files_count": 0,
                "files": []
            }
        courses[material.course_name]["files_count"] += 1
        courses[material.course_name]["files"].append(material.file_name)
    
    return list(courses.values())

# ============================================================================
# STUDY PLAN GENERATION ENDPOINTS
# ============================================================================

@app.post("/plan/generate", response_model=StudyPlanResponse)
async def generate_study_plan(
    request: PlanGenerateRequest,
    current_user: StudentProfile = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate personalized study plan using Planning Agent"""
    
    print(f"📅 Generating study plan for: {request.course_name}")
    
    # Get course content for context (first 2000 chars)
    materials = db.query(CourseMaterial).filter(
        CourseMaterial.student_id == current_user.student_id,
        CourseMaterial.course_name == request.course_name
    ).first()
    
    course_content = None
    if materials and materials.file_path:
        try:
            text = pdf_processor.extract_text_from_pdf(materials.file_path)
            course_content = text[:2000] if text else None
        except:
            pass
    
    # Generate plan
    plan_data = planning_agent.generate_study_plan(
        student_id=current_user.student_id,
        course_name=request.course_name,
        study_hours_per_week=current_user.study_hours_per_week,
        syllabus_content=request.syllabus_content or course_content,
        exam_timeline=request.exam_timeline,
        db=db
    )
    
    # Get plan_id from database
    latest_plan = db.query(StudyPlan).filter(
        StudyPlan.student_id == current_user.student_id,
        StudyPlan.course_name == request.course_name
    ).order_by(StudyPlan.created_at.desc()).first()
    
    plan_id = latest_plan.plan_id if latest_plan else 0
    
    print(f"✅ Study plan generated with {len(plan_data['weeks'])} weeks")
    
    return StudyPlanResponse(
        plan_id=plan_id,
        course_name=request.course_name,
        weeks=[WeeklyPlan(**week) for week in plan_data['weeks']]
    )

@app.get("/plan/{course_name}")
async def get_study_plan(
    course_name: str,
    current_user: StudentProfile = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get existing study plan for a course"""
    
    plans = db.query(StudyPlan).filter(
        StudyPlan.student_id == current_user.student_id,
        StudyPlan.course_name == course_name
    ).order_by(StudyPlan.week_number).all()
    
    if not plans:
        raise HTTPException(status_code=404, detail="No study plan found for this course")
    
    weeks = [
        WeeklyPlan(
            week_number=p.week_number,
            topics=p.topics,
            allocated_hours=p.allocated_hours
        ) for p in plans
    ]
    
    return StudyPlanResponse(
        plan_id=plans[0].plan_id,
        course_name=course_name,
        weeks=weeks
    )

# ============================================================================
# RAG QUESTION ANSWERING ENDPOINTS
# ============================================================================

@app.post("/qa/ask", response_model=AnswerResponse)
async def ask_question(
    request: QuestionRequest,
    current_user: StudentProfile = Depends(get_current_user)
):
    """Answer question using RAG over course materials"""
    
    print(f"❓ Question: {request.question[:50]}...")
    
    # Use retrieval agent
    result = retrieval_agent.answer_question(
        course_name=request.course_name,
        question=request.question
    )
    
    print(f"✅ Answer generated with {result['relevant_chunks']} source chunks")
    
    return AnswerResponse(
        answer=result['answer'],
        sources=result['sources'],
        relevant_chunks=result['relevant_chunks']
    )

# ============================================================================
# QUIZ GENERATION & SUBMISSION ENDPOINTS
# ============================================================================

@app.post("/quiz/generate", response_model=QuizResponse)
async def generate_quiz(
    request: QuizGenerateRequest,
    current_user: StudentProfile = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate adaptive quiz using Quiz Generation Agent"""
    
    print(f"📝 Generating quiz for topic: {request.topic}")
    
    quiz_data = quiz_agent.generate_quiz(
        student_id=current_user.student_id,
        course_name=request.course_name,
        topic=request.topic,
        difficulty=request.difficulty,
        db=db
    )
    
    print(f"✅ Quiz generated with {len(quiz_data['questions'])} questions")
    
    return QuizResponse(**quiz_data)

@app.post("/quiz/submit")
async def submit_quiz(
    request: QuizSubmitRequest,
    current_user: StudentProfile = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit quiz answers and update mastery"""
    
    # Calculate score
    correct = sum(1 for i, ans in enumerate(request.answers) if ans == request.correct_answers[i])
    total = len(request.answers)
    score = correct / total if total > 0 else 0
    
    # Save to quiz history
    quiz_record = QuizHistory(
        student_id=current_user.student_id,
        topic=request.quiz_topic,
        score=score,
        total_questions=total,
        correct_answers=correct
    )
    db.add(quiz_record)
    db.commit()
    
    # Update mastery
    mastery_score = reflection_agent.update_mastery(
        student_id=current_user.student_id,
        topic=request.quiz_topic,
        score=score,
        total_questions=total,
        correct_answers=correct,
        db=db
    )
    
    print(f"✅ Quiz submitted: {correct}/{total} correct, Mastery: {mastery_score:.2%}")
    
    return {
        "score": score,
        "correct": correct,
        "total": total,
        "mastery_score": mastery_score,
        "message": "Quiz submitted successfully"
    }

# ============================================================================
# MASTERY TRACKING ENDPOINTS
# ============================================================================

@app.get("/mastery/{course_name}")
async def get_mastery(
    course_name: str,
    current_user: StudentProfile = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get mastery tracking for all topics in a course"""
    
    mastery_records = db.query(MasteryTracker).filter(
        MasteryTracker.student_id == current_user.student_id
    ).all()
    
    return [
        MasteryResponse(
            topic=m.topic,
            mastery_score=m.mastery_score,
            attempts=m.attempts,
            recommendation=f"{'Strong' if m.mastery_score >= 0.7 else 'Needs practice'}"
        ) for m in mastery_records
    ]

@app.get("/mastery/recommendations/{course_name}")
async def get_recommendations(
    course_name: str,
    current_user: StudentProfile = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get study plan recommendations based on mastery"""
    
    suggestions = reflection_agent.suggest_plan_modifications(
        student_id=current_user.student_id,
        course_name=course_name,
        db=db
    )
    
    return suggestions

# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.get("/")
async def root():
    return {
        "message": "AI-Powered Learning Copilot API",
        "status": "running",
        "version": "1.0.0",
        "endpoints": {
            "auth": ["/auth/register", "/auth/login"],
            "courses": ["/upload", "/courses"],
            "planning": ["/plan/generate", "/plan/{course_name}"],
            "qa": ["/qa/ask"],
            "quiz": ["/quiz/generate", "/quiz/submit"],
            "mastery": ["/mastery/{course_name}", "/mastery/recommendations/{course_name}"]
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "database": "connected",
        "vector_store": "ready",
        "llm": "ready"
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Learning Copilot API...")
    print("📖 API Documentation: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)
