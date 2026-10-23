from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from database.db import db
from database.models import ChatSession, ChatMessage, SymptomAnalysis, DiseasePrediction, Explanation, Recommendation
import uuid
from datetime import datetime, timezone

bp = Blueprint('chat', __name__)

# ============================================
# CHAT SESSIONS
# ============================================

@bp.route('/chat/sessions', methods=['GET'])
@jwt_required()
def get_sessions():
    """Get all chat sessions for current user"""
    user_id = get_jwt_identity()
    
    sessions = ChatSession.query.filter_by(
        user_id=user_id,
        is_archived=False
    ).order_by(
        ChatSession.is_pinned.desc(),
        ChatSession.updated_at.desc()
    ).all()
    
    return jsonify([s.to_dict() for s in sessions]), 200

@bp.route('/chat/sessions', methods=['POST'])
@jwt_required()
def create_session():
    """Create a new chat session"""
    user_id = get_jwt_identity()
    data = request.get_json()
    
    title = data.get('title', 'New Conversation')
    
    session = ChatSession(
        id=uuid.uuid4(),
        user_id=user_id,
        title=title,
        preview_text='Start a new conversation...',
        message_count=0,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    db.session.add(session)
    db.session.commit()
    
    return jsonify(session.to_dict()), 201

@bp.route('/chat/sessions/<session_id>', methods=['DELETE'])
@jwt_required()
def delete_session(session_id):
    """Delete a chat session"""
    user_id = get_jwt_identity()
    
    session = ChatSession.query.filter_by(
        id=session_id,
        user_id=user_id
    ).first()
    
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    
    db.session.delete(session)
    db.session.commit()
    
    return jsonify({'message': 'Session deleted'}), 200

@bp.route('/chat/sessions/<session_id>/pin', methods=['PUT'])
@jwt_required()
def toggle_pin(session_id):
    """Pin or unpin a chat session"""
    user_id = get_jwt_identity()
    data = request.get_json()
    
    session = ChatSession.query.filter_by(
        id=session_id,
        user_id=user_id
    ).first()
    
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    
    setattr(session, 'is_pinned', data.get('is_pinned', False))
    setattr(session, 'updated_at', datetime.now(timezone.utc))
    db.session.commit()
    
    return jsonify(session.to_dict()), 200

@bp.route('/chat/sessions/<session_id>/rename', methods=['PUT'])
@jwt_required()
def rename_session(session_id):
    """Rename a chat session"""
    user_id = get_jwt_identity()
    data = request.get_json()
    
    session = ChatSession.query.filter_by(
        id=session_id,
        user_id=user_id
    ).first()
    
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    
    new_title = data.get('title', 'New Conversation')
    setattr(session, 'title', new_title)
    setattr(session, 'updated_at', datetime.now(timezone.utc))
    db.session.commit()
    
    return jsonify(session.to_dict()), 200

# ============================================
# CHAT MESSAGES
# ============================================

@bp.route('/chat/messages/<session_id>', methods=['GET'])
@jwt_required()
def get_messages(session_id):
    """Get all messages for a session"""
    user_id = get_jwt_identity()
    
    session = ChatSession.query.filter_by(
        id=session_id,
        user_id=user_id
    ).first()
    
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    
    messages = ChatMessage.query.filter_by(
        session_id=session_id
    ).order_by(ChatMessage.created_at).all()
    
    return jsonify([m.to_dict() for m in messages]), 200

@bp.route('/chat/message', methods=['POST'])
@jwt_required()
def send_message():
    """Send a message and get AI response"""
    user_id = get_jwt_identity()
    data = request.get_json()
    
    message = data.get('message')
    session_id = data.get('session_id')
    
    if not message:
        return jsonify({'error': 'Message is required'}), 400
    
    # Create session if not provided
    if not session_id:
        session = ChatSession(
            id=uuid.uuid4(),
            user_id=user_id,
            title=message[:30] + '...' if len(message) > 30 else message,
            preview_text=message[:50],
            message_count=0,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.session.add(session)
        db.session.commit()
        session_id = session.id
    else:
        session = ChatSession.query.filter_by(
            id=session_id,
            user_id=user_id
        ).first()
        if not session:
            return jsonify({'error': 'Session not found'}), 404
    
    # Save user message
    user_msg = ChatMessage(
        id=uuid.uuid4(),
        session_id=session_id,
        role='user',
        content=message,
        created_at=datetime.now(timezone.utc)
    )
    db.session.add(user_msg)
    
    # Generate AI response
    response = generate_ai_response(message)
    
    # Save assistant message
    assistant_msg = ChatMessage(
        id=uuid.uuid4(),
        session_id=session_id,
        role='assistant',
        content=response,
        agent_type='Coordinator',
        created_at=datetime.now(timezone.utc)
    )
    db.session.add(assistant_msg)
    
    # Update session
    setattr(session, 'message_count', (getattr(session, 'message_count', 0) or 0) + 1)
    setattr(session, 'preview_text', message[:50])
    setattr(session, 'last_message_at', datetime.now(timezone.utc))
    setattr(session, 'updated_at', datetime.now(timezone.utc))
    db.session.commit()
    
    return jsonify({
        'response': response,
        'session_id': session_id,
        'agent_results': {'status': 'success'}
    }), 200

def generate_ai_response(message):
    """Generate AI response (placeholder - integrate with your agents)"""
    # This is a placeholder - integrate with your multi-agent system
    return f"Thank you for your message: '{message}'. I'm processing it with our multi-agent system. The Coordinator Agent is analyzing your input and will provide a comprehensive response."

# ============================================
# SYMPTOM ANALYSIS
# ============================================

@bp.route('/chat/symptoms', methods=['POST'])
@jwt_required()
def analyze_symptoms():
    """Analyze symptoms from chat"""
    user_id = get_jwt_identity()
    data = request.get_json()
    
    text = data.get('text', '')
    session_id = data.get('session_id')
    
    if not text:
        return jsonify({'error': 'Text is required'}), 400
    
    # Simple symptom extraction (placeholder)
    symptoms = extract_symptoms(text)
    
    symptom_analysis = SymptomAnalysis(
        id=uuid.uuid4(),
        user_id=user_id,
        session_id=session_id,
        raw_text=text,
        extracted_symptoms=symptoms,
        severity_score=calculate_severity(symptoms),
        created_at=datetime.now(timezone.utc)
    )
    db.session.add(symptom_analysis)
    db.session.commit()
    
    return jsonify(symptom_analysis.to_dict()), 201

def extract_symptoms(text):
    """Extract symptoms from text (placeholder)"""
    # Implement your symptom extraction logic
    common_symptoms = ['fever', 'cough', 'headache', 'fatigue', 'nausea', 'vomiting', 'pain']
    extracted = []
    for symptom in common_symptoms:
        if symptom in text.lower():
            extracted.append(symptom)
    return extracted

def calculate_severity(symptoms):
    """Calculate severity based on symptoms"""
    return min(100, len(symptoms) * 15)

# ============================================
# DISEASE PREDICTIONS
# ============================================

@bp.route('/chat/predict', methods=['POST'])
@jwt_required()
def predict_disease():
    """Predict disease from symptoms"""
    user_id = get_jwt_identity()
    data = request.get_json()
    
    symptoms = data.get('symptoms', [])
    session_id = data.get('session_id')
    symptom_analysis_id = data.get('symptom_analysis_id')
    
    if not symptoms:
        return jsonify({'error': 'Symptoms are required'}), 400
    
    # Placeholder prediction
    prediction = DiseasePrediction(
        id=uuid.uuid4(),
        user_id=user_id,
        session_id=session_id,
        symptom_analysis_id=symptom_analysis_id,
        symptoms=symptoms,
        predicted_disease='Influenza',
        confidence_score=0.85,
        severity='medium',
        urgency_level='medium',
        suggested_specialist='General Physician',
        created_at=datetime.now(timezone.utc)
    )
    db.session.add(prediction)
    db.session.commit()
    
    return jsonify(prediction.to_dict()), 201