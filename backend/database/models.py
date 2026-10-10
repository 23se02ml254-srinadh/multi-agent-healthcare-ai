from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text, Float, JSON, ForeignKey, Date, Time
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from database.db import db
import uuid

class BaseModel(db.Model):
    __abstract__ = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        for key, value in kwargs.items():
            setattr(self, key, value)

class User(BaseModel):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)
    first_name = Column(String(100))
    last_name = Column(String(100))
    google_id = Column(String(255), unique=True, nullable=True, index=True)
    avatar_url = Column(String(500), nullable=True)
    auth_provider = Column(String(50), default='local')
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")
    chat_messages = relationship("ChatMessage", back_populates="user", cascade="all, delete-orphan")
    symptom_analyses = relationship("SymptomAnalysis", back_populates="user", cascade="all, delete-orphan")
    predictions = relationship("DiseasePrediction", back_populates="user", cascade="all, delete-orphan")
    explanations = relationship("Explanation", back_populates="user", cascade="all, delete-orphan")
    reports = relationship("MedicalReport", back_populates="user", cascade="all, delete-orphan")
    recommendations = relationship("Recommendation", back_populates="user", cascade="all, delete-orphan")
    appointments = relationship("Appointment", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "email": self.email,
            "username": self.username,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": f"{self.first_name} {self.last_name}".strip(),
            "avatar_url": self.avatar_url,
            "auth_provider": self.auth_provider,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class ChatSession(BaseModel):
    __tablename__ = "chat_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title = Column(String(255), default='New Conversation')
    preview_text = Column(String(500), default='Start a new conversation...')
    is_pinned = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False)
    message_count = Column(Integer, default=0)
    last_message_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    user = relationship("User", back_populates="chat_sessions")
    messages = relationship("ChatMessage", backref="session", cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "user_id": str(self.user_id) if self.user_id else None,
            "title": self.title,
            "preview_text": self.preview_text,
            "is_pinned": self.is_pinned,
            "is_archived": self.is_archived,
            "message_count": self.message_count,
            "last_message_at": self.last_message_at.isoformat() if self.last_message_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

class ChatMessage(BaseModel):
    __tablename__ = "chat_messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    session_id = Column(String(100), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    agent_type = Column(String(50), nullable=True)
    agent_responses = Column(JSON, default=dict)
    merged_response = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    user = relationship("User", back_populates="chat_messages")
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "session_id": str(self.session_id),
            "role": self.role,
            "content": self.content,
            "agent_type": self.agent_type,
            "agent_responses": self.agent_responses,
            "merged_response": self.merged_response,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class SymptomAnalysis(BaseModel):
    __tablename__ = "symptom_analyses"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    session_id = Column(String(100), nullable=True)
    raw_text = Column(Text)
    extracted_symptoms = Column(JSON, default=list)
    severity_score = Column(Float, default=0.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    user = relationship("User", back_populates="symptom_analyses")
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "user_id": str(self.user_id) if self.user_id else None,
            "session_id": str(self.session_id) if self.session_id else None,
            "raw_text": self.raw_text,
            "extracted_symptoms": self.extracted_symptoms,
            "severity_score": self.severity_score,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class DiseasePrediction(BaseModel):
    __tablename__ = "disease_predictions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    session_id = Column(String(100), nullable=True)
    symptom_analysis_id = Column(String(100), nullable=True)
    symptoms = Column(JSON, nullable=False)
    predicted_disease = Column(String(255), nullable=False)
    confidence_score = Column(Float, nullable=False)
    probability_distribution = Column(JSON)
    explanation = Column(JSON)
    severity = Column(String(50))
    urgency_level = Column(String(50))
    suggested_specialist = Column(String(100), nullable=True)
    recommendations = Column(JSON, default=list)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    user = relationship("User", back_populates="predictions")
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "user_id": str(self.user_id) if self.user_id else None,
            "session_id": str(self.session_id) if self.session_id else None,
            "symptom_analysis_id": str(self.symptom_analysis_id) if self.symptom_analysis_id else None,
            "symptoms": self.symptoms,
            "predicted_disease": self.predicted_disease,
            "confidence_score": self.confidence_score,
            "probability_distribution": self.probability_distribution,
            "explanation": self.explanation,
            "severity": self.severity,
            "urgency_level": self.urgency_level,
            "suggested_specialist": self.suggested_specialist,
            "recommendations": self.recommendations,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class Explanation(BaseModel):
    __tablename__ = "explanations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    session_id = Column(String(100), nullable=True)
    prediction_id = Column(String(100), nullable=True)
    symptom_analysis_id = Column(String(100), nullable=True)
    explanation_text = Column(Text)
    symptom_contributions = Column(JSON, default=dict)
    confidence_explanation = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    user = relationship("User", back_populates="explanations")
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "user_id": str(self.user_id) if self.user_id else None,
            "session_id": str(self.session_id) if self.session_id else None,
            "prediction_id": str(self.prediction_id) if self.prediction_id else None,
            "symptom_analysis_id": str(self.symptom_analysis_id) if self.symptom_analysis_id else None,
            "explanation_text": self.explanation_text,
            "symptom_contributions": self.symptom_contributions,
            "confidence_explanation": self.confidence_explanation,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class MedicalReport(BaseModel):
    __tablename__ = "medical_reports"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer)
    file_type = Column(String(50))
    extracted_text = Column(Text)
    summary = Column(Text)
    key_findings = Column(JSON, default=list)
    abnormal_values = Column(JSON, default=list)
    medical_terms = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    user = relationship("User", back_populates="reports")
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "filename": self.filename,
            "file_path": self.file_path,
            "file_size": self.file_size,
            "file_type": self.file_type,
            "summary": self.summary,
            "key_findings": self.key_findings,
            "abnormal_values": self.abnormal_values,
            "medical_terms": self.medical_terms,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class Recommendation(BaseModel):
    __tablename__ = "recommendations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    type = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    priority = Column(String(20), default='medium')
    is_completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    user = relationship("User", back_populates="recommendations")
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "type": self.type,
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "is_completed": self.is_completed,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class Appointment(BaseModel):
    __tablename__ = "appointments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    doctor_name = Column(String(255), nullable=False)
    specialty = Column(String(100), nullable=False)
    appointment_date = Column(Date, nullable=False)
    appointment_time = Column(Time, nullable=False)
    reason = Column(Text)
    status = Column(String(50), default='pending')
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    user = relationship("User", back_populates="appointments")
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "doctor_name": self.doctor_name,
            "specialty": self.specialty,
            "appointment_date": self.appointment_date.isoformat() if self.appointment_date else None,
            "appointment_time": self.appointment_time.strftime("%H:%M") if self.appointment_time else None,
            "reason": self.reason,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class Notification(BaseModel):
    __tablename__ = "notifications"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String(50), nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    user = relationship("User", back_populates="notifications")
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "title": self.title,
            "message": self.message,
            "type": self.type,
            "is_read": self.is_read,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }