import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any # type: ignore
import os
import sqlite3 # type: ignore
from jose import jwt, JWTError # type: ignore
from bi_engine import ai_generate_dashboard, ai_generate_insights, generate_admin_insight
from fastapi import FastAPI, HTTPException, Depends, status, Header # type: ignore
from fastapi.middleware.cors import CORSMiddleware # type: ignore
from pydantic import BaseModel, EmailStr # type: ignore
from sqlalchemy import create_engine, Column, String, Text, DateTime, JSON, ForeignKey, Integer, Float, text # type: ignore
from sqlalchemy.orm import declarative_base, sessionmaker, Session # type: ignore
from passlib.context import CryptContext # type: ignore

# --- Configuration ---
DATABASE_URL = "sqlite:///./humana.db"
SECRET_KEY = "your-super-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# --- Database Setup ---
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- Security ---
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# --- SQLAlchemy Models ---
class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class Business(Base):
    __tablename__ = "businesses"
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), unique=True)
    business_name = Column(String)
    business_url = Column(String, nullable=True)
    industry = Column(String)
    plan = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class Avatar(Base):
    __tablename__ = "avatars"
    id = Column(String, primary_key=True, index=True)
    business_id = Column(String, ForeignKey("businesses.id"), unique=True)
    name = Column(String)
    voice_model = Column(String)
    brand_color = Column(String)
    welcome_message = Column(Text)
    system_prompt = Column(Text, nullable=True)
    language = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class KnowledgeSource(Base):
    __tablename__ = "knowledge_sources"
    id = Column(String, primary_key=True, index=True)
    avatar_id = Column(String, index=True, nullable=False)
    type = Column(String)  # 'file', 'faq', 'url'
    content = Column(Text)
    metadata_json = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

# --- BI & Analytics Models ---
class Event(Base):
    __tablename__ = "events"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    business_id = Column(String, index=True, nullable=False)
    event_type = Column(String, index=True)
    amount = Column(Float, nullable=True) # Optional numerical value
    data_json = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

class Metric(Base):
    __tablename__ = "metrics"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    business_id = Column(String, index=True, nullable=False)
    metric_name = Column(String, index=True)
    metric_value = Column(Float)
    date_recorded = Column(DateTime, default=datetime.utcnow, index=True)

class Dashboard(Base):
    __tablename__ = "dashboards"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    business_id = Column(String, index=True, nullable=False)
    blueprint_json = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

class Insight(Base):
    __tablename__ = "insights"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    business_id = Column(String, index=True, nullable=False)
    type = Column(String) # opportunity, anomaly, recommendation
    severity = Column(String) # high, medium, low
    message = Column(Text)
    causes_json = Column(JSON, nullable=True) # e.g. ["Traffic decreased", "Conversion dropped"]
    confidence = Column(Float, default=1.0)
    created_at = Column(DateTime, default=datetime.utcnow)

class BusinessMemory(Base):
    __tablename__ = "business_memories"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    business_id = Column(String, index=True, nullable=False)
    memory_type = Column(String) # metric_history, event, behavior, insight
    content_json = Column(JSON)
    confidence = Column(Float, default=1.0)
    created_at = Column(DateTime, default=datetime.utcnow)

# Create tables
Base.metadata.create_all(bind=engine)

# --- Pydantic Schemas ---
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    created_at: datetime

class Token(BaseModel):
    access_token: str
    token_type: str

class BusinessCreate(BaseModel):
    business_name: str
    business_url: Optional[str] = None
    industry: str
    plan: str = "Starter"

class BusinessResponse(BaseModel):
    id: str
    user_id: str
    business_name: str
    business_url: Optional[str]
    industry: str
    plan: str
    created_at: datetime

class AvatarCreate(BaseModel):
    name: str
    voice_model: str = "nova"
    brand_color: str = "#f59e0b"
    welcome_message: str
    system_prompt: Optional[str] = None
    language: str = "en"

class AvatarResponse(BaseModel):
    id: str
    business_id: str
    name: str
    voice_model: str
    brand_color: str
    welcome_message: str
    system_prompt: Optional[str]
    language: str
    created_at: datetime

class WizardData(BaseModel):
    business_name: str
    business_url: Optional[str]
    industry: str
    plan: str
    avatar_name: str
    voice_id: str
    welcome_message: str
    primary_color: str

class AdminProxyRequest(BaseModel):
    prompt: str

class EventCreate(BaseModel):
    business_id: str
    event_type: str
    amount: Optional[float] = None
    data_json: Optional[Dict[str, Any]] = None

class DashboardCreateRequest(BaseModel):
    business_id: str
    prompt: str

class InsightResponse(BaseModel):
    id: str
    type: str
    severity: str
    message: str
    causes_json: Optional[List[str]] = None
    confidence: float

# --- Helper functions ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def get_current_user(authorization: str = Header(None), db: Session = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user

# --- FastAPI app ---
app = FastAPI(title="HUMANA API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health / stats endpoints
@app.get("/api/health")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "error"
    return {
        "status": "ok",
        "db_status": db_status,
        "llm_provider": "OpenAI",
        "llm_model": "gpt-4o",
        "active_sessions": 0,
    }

@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    total_businesses = db.query(Business).count()
    return {
        "total_businesses": total_businesses,
        "active_sessions": 0,
        "llm_provider": "OpenAI",
        "llm_model": "gpt-4o",
    }

# Auth endpoints
@app.post("/api/auth/signup", response_model=Token)
def signup(user_data: UserCreate, db: Session = Depends(get_db)):
    # Check if user exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    user_id = str(uuid.uuid4())
    user = User( # type: ignore
        id=user_id,
        email=user_data.email, # type: ignore
        hashed_password=get_password_hash(user_data.password), # type: ignore
        full_name=user_data.full_name # type: ignore
    )
    db.add(user)
    db.commit()
    
    # Create access token
    access_token = create_access_token(data={"sub": user_id})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/auth/login", response_model=Token)
def login(login_data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == login_data.email).first()
    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token(data={"sub": user.id})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/auth/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user

# Business endpoints
@app.post("/api/business", response_model=BusinessResponse)
def create_business(
    business_data: BusinessCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check if user already has a business
    existing = db.query(Business).filter(Business.user_id == current_user.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="User already has a business")
    
    business_id = str(uuid.uuid4())
    business = Business( # type: ignore
        id=business_id,
        user_id=current_user.id, # type: ignore
        business_name=business_data.business_name, # type: ignore
        business_url=business_data.business_url, # type: ignore
        industry=business_data.industry, # type: ignore
        plan=business_data.plan # type: ignore
    )
    db.add(business)
    db.commit()
    db.refresh(business)
    return business

@app.get("/api/business", response_model=Optional[BusinessResponse])
def get_business(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    business = db.query(Business).filter(Business.user_id == current_user.id).first()
    return business

# Avatar endpoints
@app.post("/api/avatars", response_model=AvatarResponse)
def create_avatar(
    avatar_data: AvatarCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Get user's business
    business = db.query(Business).filter(Business.user_id == current_user.id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found. Complete wizard first.")
    
    # Check if avatar already exists
    existing = db.query(Avatar).filter(Avatar.business_id == business.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Avatar already exists for this business")
    
    avatar_id = str(uuid.uuid4())
    avatar = Avatar( # type: ignore
        id=avatar_id,
        business_id=business.id, # type: ignore
        name=avatar_data.name, # type: ignore
        voice_model=avatar_data.voice_model, # type: ignore
        brand_color=avatar_data.brand_color, # type: ignore
        welcome_message=avatar_data.welcome_message, # type: ignore
        system_prompt=avatar_data.system_prompt, # type: ignore
        language=avatar_data.language # type: ignore
    )
    db.add(avatar)
    db.commit()
    db.refresh(avatar)
    return avatar

@app.get("/api/avatars", response_model=Optional[AvatarResponse])
def get_avatar(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    business = db.query(Business).filter(Business.user_id == current_user.id).first()
    if not business:
        return None
    avatar = db.query(Avatar).filter(Avatar.business_id == business.id).first()
    return avatar

# Wizard endpoint - creates everything in one go
@app.post("/api/wizard/complete")
def complete_wizard(
    wizard_data: WizardData,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check if user already has business
    existing_business = db.query(Business).filter(Business.user_id == current_user.id).first()
    if existing_business:
        raise HTTPException(status_code=400, detail="Wizard already completed")
    
    # Create business
    business_id = str(uuid.uuid4())
    business = Business( # type: ignore
        id=business_id,
        user_id=current_user.id, # type: ignore
        business_name=wizard_data.business_name, # type: ignore
        business_url=wizard_data.business_url, # type: ignore
        industry=wizard_data.industry, # type: ignore
        plan=wizard_data.plan # type: ignore
    )
    db.add(business)
    
    # Create avatar
    avatar_id = str(uuid.uuid4())
    avatar = Avatar( # type: ignore
        id=avatar_id,
        business_id=business_id, # type: ignore
        name=wizard_data.avatar_name, # type: ignore
        voice_model=wizard_data.voice_id, # type: ignore
        brand_color=wizard_data.primary_color, # type: ignore
        welcome_message=wizard_data.welcome_message, # type: ignore
        system_prompt=f"You are {wizard_data.avatar_name}, a helpful AI assistant for {wizard_data.business_name}. Be friendly and professional.", # type: ignore
        language="en" # type: ignore
    )
    db.add(avatar)
    db.commit()
    
    return {
        "business": business,
        "avatar": avatar,
        "message": "Wizard completed successfully"
    }

@app.get("/api/dashboard/data")
def get_dashboard_data(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    business = db.query(Business).filter(Business.user_id == current_user.id).first()
    if not business:
        return {"has_business": False}
    
    avatar = db.query(Avatar).filter(Avatar.business_id == business.id).first()
    
    return {
        "has_business": True,
        "business": business,
        "avatar": avatar
    }

# --- Business Intelligence Endpoints ---

@app.post("/api/events")
def create_event(event_in: EventCreate, db: Session = Depends(get_db)):
    db_event = Event(
        business_id=event_in.business_id,
        event_type=event_in.event_type,
        amount=event_in.amount,
        data_json=event_in.data_json
    )
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return {"message": "Event recorded", "id": db_event.id}

@app.get("/api/metrics/{business_id}")
def get_metrics(business_id: str, db: Session = Depends(get_db)):
    # Very basic metrics generation synchronously to start (Phase 1)
    today = datetime.utcnow().date()
    conversations = db.query(Event).filter(Event.business_id == business_id, Event.event_type == "conversation_started").count()
    handoffs = db.query(Event).filter(Event.business_id == business_id, Event.event_type == "handoff_human").count()
    revenue = db.query(Event).filter(Event.business_id == business_id, Event.event_type == "order_completed").all()
    total_rev = sum(e.amount for e in revenue if e.amount)
    
    # Calculate a mock resolution rate safely
    resolution_rate = 1.0
    if conversations > 0:
        resolution_rate = (conversations - handoffs) / conversations
        
    metrics = {
        "conversations_today": conversations, # Changed from conversations_total to match the AI template examples
        "handoffs": handoffs,
        "revenue_today": total_rev,
        "resolution_rate": round(resolution_rate, 2),
        "daily_conversations": [
            {"date": str(today), "count": conversations}
        ]
    }
    return metrics

@app.post("/api/dashboard/create")
def create_ai_dashboard(req: DashboardCreateRequest, db: Session = Depends(get_db)):
    # 1. Ask AI to generate blueprint
    blueprint = ai_generate_dashboard(req.prompt)
    
    # 2. Save or update the dashboard record
    existing = db.query(Dashboard).filter(Dashboard.business_id == req.business_id).first()
    if existing:
        existing.blueprint_json = blueprint
        existing.created_at = datetime.utcnow()
    else:
        new_dash = Dashboard(business_id=req.business_id, blueprint_json=blueprint)
        db.add(new_dash)
    db.commit()
    return blueprint

@app.get("/api/dashboard/config/{business_id}")
def get_dashboard_config(business_id: str, db: Session = Depends(get_db)):
    dash = db.query(Dashboard).filter(Dashboard.business_id == business_id).order_by(Dashboard.created_at.desc()).first()
    if not dash:
        return {"components": [], "layout": {"columns": 12}}
    return dash.blueprint_json

@app.get("/api/insights/{business_id}")
def get_insights(business_id: str, db: Session = Depends(get_db)):
    # Generate insights dynamically based on metrics
    metrics = get_metrics(business_id, db)
    metrics_str = str(metrics)
    raw_insights = ai_generate_insights(metrics_str)
    
    # Save insights to database
    saved = []
    for item in raw_insights:
        insight = Insight(
            business_id=business_id,
            type=item.get("type", "recommendation"),
            severity=item.get("severity", "medium"),
            message=item.get("message", ""),
            causes_json=item.get("causes", []),
            confidence=item.get("confidence", 0.5)
        )
        db.add(insight)
        saved.append(insight)
    db.commit()
    
    return [{"id": i.id, "type": i.type, "message": i.message, "severity": i.severity, "causes_json": i.causes_json} for i in saved]

@app.post("/api/admin/llm-proxy")
def admin_llm_proxy(req: AdminProxyRequest, current_user: User = Depends(get_current_user)):
    # Authenticated user check passed.
    # In a prod environment, verify user has admin roles here.
    return {"content": generate_admin_insight(req.prompt)}


if __name__ == "__main__":
    import uvicorn # type: ignore
    uvicorn.run("backend:app", host="0.0.0.0", port=8000, reload=True)
