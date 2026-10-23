from flask import Flask, jsonify, request, redirect, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta
from config import Config
from database.db import db, init_db
from database.models import User, ChatMessage, DiseasePrediction, MedicalReport, Recommendation, Appointment, Notification
from agents.coordinator import CoordinatorAgent
import uuid
import logging
import os
import base64
import json
import secrets
import urllib.parse
import requests
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Locate frontend directory (supports both repo root and backend/ subfolder executions)
candidate_dirs = [
    os.path.abspath(os.path.join(os.path.dirname(__file__), 'frontend')),
    os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend')),
    os.path.abspath('frontend')
]
frontend_dir = next((d for d in candidate_dirs if os.path.isdir(d)), candidate_dirs[1])

# Create Flask app with frontend static assets enabled
app = Flask(__name__, static_folder=frontend_dir, static_url_path='')

# Initialize Multi-Agent Coordinator
coordinator = CoordinatorAgent()

# Load configuration
app.config.from_object(Config)

# FIX: Ensure DATABASE_URI is set
if not app.config.get('SQLALCHEMY_DATABASE_URI'):
    raise RuntimeError("SQLALCHEMY_DATABASE_URI must be set")

print(f"[OK] Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")

# Initialize extensions
CORS(app, origins=app.config.get('CORS_ORIGINS', ['*']), supports_credentials=True)  # type: ignore
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=7)
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)
jwt = JWTManager(app)

# Initialize database
db.init_app(app)

# Create tables and ensure OAuth columns exist safely
with app.app_context():
    db.create_all()
    try:
        db.session.execute(text("""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='users' AND column_name='google_id') THEN
                    ALTER TABLE users ADD COLUMN google_id VARCHAR(255) UNIQUE;
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='users' AND column_name='avatar_url') THEN
                    ALTER TABLE users ADD COLUMN avatar_url VARCHAR(500);
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='users' AND column_name='auth_provider') THEN
                    ALTER TABLE users ADD COLUMN auth_provider VARCHAR(50) DEFAULT 'local';
                END IF;
                ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL;
            END $$;
        """))
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.warning(f"OAuth columns verification notice: {e}")
    print("[OK] Database tables created and verified successfully")

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'database': 'connected',
        'service': 'Multi-Agent AI Healthcare',
        'database_name': 'multiagent_db'
    })

@app.route('/')
def index():
    return send_from_directory(frontend_dir, 'index.html')

@app.route('/login')
def login_page():
    return send_from_directory(frontend_dir, 'login.html')

@app.route('/register')
def register_page():
    return send_from_directory(frontend_dir, 'register.html')

@app.route('/dashboard')
def dashboard_page():
    return send_from_directory(frontend_dir, 'dashboard.html')

@app.route('/api')
def api_status():
    return jsonify({
        'name': 'Multi-Agent AI Healthcare Assistant',
        'version': '1.0.0',
        'status': 'operational',
        'database': 'multiagent_db',
        'endpoints': {
            'health': '/health',
            'register': '/api/auth/register',
            'login': '/api/auth/login',
            'google': '/api/auth/google',
            'google_client_id': '/api/auth/google/client-id',
            'me': '/api/auth/me',
            'chat': '/api/chat'
        }
    })

@app.route('/<path:filename>')
def serve_static(filename):
    if filename.startswith('api/') or filename == 'api':
        return jsonify({'error': 'Not found'}), 404
    file_path = os.path.join(frontend_dir, filename)
    if os.path.isfile(file_path):
        return send_from_directory(frontend_dir, filename)
    return send_from_directory(frontend_dir, 'index.html')

@app.route('/api/auth/google/client-id', methods=['GET'])
def get_google_client_id():
    """Returns the Google Client ID configured in the backend environment"""
    client_id = app.config.get('GOOGLE_CLIENT_ID', '')
    return jsonify({'client_id': client_id}), 200

def verify_google_id_token(token, client_id=None):
    """Verifies a Google ID token via google-auth if installed, or official Google tokeninfo API"""
    try:
        from google.oauth2 import id_token as g_id_token
        from google.auth.transport import requests as g_requests
        req = g_requests.Request()
        return g_id_token.verify_oauth2_token(token, req, client_id if client_id else None, clock_skew_in_seconds=10)
    except Exception:
        pass

    try:
        resp = requests.get(f"https://oauth2.googleapis.com/tokeninfo?id_token={token}", timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except Exception as err:
        logger.error(f"Google tokeninfo REST request error: {err}")
    return None

@app.route('/api/auth/google', methods=['POST'])
def google_auth():
    """Google OAuth 2.0 verification and user authentication/auto-registration"""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No authentication data provided'}), 400

    token = data.get('credential') or data.get('id_token')
    access_token = data.get('access_token')
    auth_code = data.get('code')

    if not token and not access_token and not auth_code:
        return jsonify({'error': 'Google token or credential is required'}), 400

    client_id = app.config.get('GOOGLE_CLIENT_ID', '')
    client_secret = app.config.get('GOOGLE_CLIENT_SECRET', '')
    google_user_info = None

    # 1. Verification via ID Token (JWT)
    if token:
        id_info = verify_google_id_token(token, client_id)
        if id_info:
            google_user_info = {
                'email': id_info.get('email'),
                'email_verified': id_info.get('email_verified') in [True, 'true', 'True'],
                'first_name': id_info.get('given_name', ''),
                'last_name': id_info.get('family_name', ''),
                'name': id_info.get('name', ''),
                'picture': id_info.get('picture', ''),
                'sub': id_info.get('sub')
            }

    # 2. Verification via Access Token (Userinfo endpoint)
    elif access_token:
        try:
            resp = requests.get(
                'https://www.googleapis.com/oauth2/v3/userinfo',
                headers={'Authorization': f'Bearer {access_token}'},
                timeout=10
            )
            if resp.status_code == 200:
                info = resp.json()
                google_user_info = {
                    'email': info.get('email'),
                    'email_verified': info.get('email_verified', True),
                    'first_name': info.get('given_name', ''),
                    'last_name': info.get('family_name', ''),
                    'name': info.get('name', ''),
                    'picture': info.get('picture', ''),
                    'sub': info.get('sub')
                }
            else:
                logger.error(f"Google userinfo endpoint error: {resp.text}")
        except Exception as e:
            logger.error(f"Failed to fetch userinfo from Google: {e}")

    # 3. Verification via Auth Code exchange
    elif auth_code:
        try:
            token_resp = requests.post('https://oauth2.googleapis.com/token', data={
                'code': auth_code,
                'client_id': client_id,
                'client_secret': client_secret,
                'redirect_uri': data.get('redirect_uri', 'postmessage'),
                'grant_type': 'authorization_code'
            }, timeout=10)
            if token_resp.status_code == 200:
                token_data = token_resp.json()
                id_tok = token_data.get('id_token')
                acc_tok = token_data.get('access_token')
                if id_tok:
                    id_info = verify_google_id_token(id_tok, client_id)
                    if id_info:
                        google_user_info = {
                            'email': id_info.get('email'),
                            'first_name': id_info.get('given_name', ''),
                            'last_name': id_info.get('family_name', ''),
                            'name': id_info.get('name', ''),
                            'picture': id_info.get('picture', ''),
                            'sub': id_info.get('sub')
                        }
                elif acc_tok:
                    info_resp = requests.get('https://www.googleapis.com/oauth2/v3/userinfo', headers={'Authorization': f'Bearer {acc_tok}'}, timeout=10)
                    if info_resp.status_code == 200:
                        info = info_resp.json()
                        google_user_info = {
                            'email': info.get('email'),
                            'first_name': info.get('given_name', ''),
                            'last_name': info.get('family_name', ''),
                            'name': info.get('name', ''),
                            'picture': info.get('picture', ''),
                            'sub': info.get('sub')
                        }
        except Exception as e:
            logger.error(f"Failed to exchange auth code with Google: {e}")

    if not google_user_info:
        return jsonify({'error': 'Invalid or unverified Google account information'}), 401

    raw_email = google_user_info.get('email')
    if not isinstance(raw_email, str) or not raw_email.strip():
        return jsonify({'error': 'Invalid or unverified Google account information'}), 401

    email = raw_email.strip().lower()
    sub_val = google_user_info.get('sub')
    sub = str(sub_val) if sub_val is not None else None
    pic_val = google_user_info.get('picture')
    picture = str(pic_val) if pic_val is not None else None
    first_name = str(google_user_info.get('first_name') or '')
    last_name = str(google_user_info.get('last_name') or '')
    name = str(google_user_info.get('name') or '')

    if not first_name and name:
        parts = name.split(' ')
        first_name = parts[0]
        last_name = ' '.join(parts[1:]) if len(parts) > 1 else ''

    try:
        # Check whether Google user already exists in PostgreSQL
        user = User.query.filter(User.email.ilike(email)).first()

        if user:
            # Existing user - check active status
            if not user.is_active:
                return jsonify({'error': 'This user account is deactivated. Please contact support.'}), 403

            # Update Google details if not already present
            changed = False
            if hasattr(user, 'google_id') and not user.google_id and sub:
                setattr(user, 'google_id', sub)
                changed = True
            if hasattr(user, 'avatar_url') and not user.avatar_url and picture:
                setattr(user, 'avatar_url', picture)
                changed = True
            if not user.first_name and first_name:
                user.first_name = first_name
                changed = True
            if not user.last_name and last_name:
                user.last_name = last_name
                changed = True

            if changed:
                try:
                    db.session.commit()
                except Exception as db_err:
                    db.session.rollback()
                    logger.warning(f"Could not update extra Google profile fields: {db_err}")

            logger.info(f"[OK] Existing user logged in via Google: {email}")
        else:
            # User does not exist - automatically create a new user account
            base_username = email.split('@')[0]
            username = base_username
            counter = 1
            while User.query.filter_by(username=username).first():
                username = f"{base_username}{counter}"
                counter += 1

            # Generate a secure random unguessable password hash (never storing raw password)
            random_hash = generate_password_hash(secrets.token_urlsafe(32))

            user = User(
                id=uuid.uuid4(),
                email=email,
                username=username,
                password_hash=random_hash,
                first_name=first_name,
                last_name=last_name,
                google_id=sub,
                avatar_url=picture,
                auth_provider='google',
                is_active=True
            )

            db.session.add(user)
            db.session.commit()
            logger.info(f"[OK] New user created automatically via Google: {email}")

        # Generate JWT access token for application session
        access_token = create_access_token(identity=str(user.id))

        return jsonify({
            'message': 'Google authentication successful',
            'access_token': access_token,
            'user': user.to_dict()
        }), 200

    except Exception as db_e:
        db.session.rollback()
        logger.error(f"Database error during Google auth: {db_e}", exc_info=True)
        return jsonify({'error': 'A database error occurred during authentication'}), 500

@app.route('/api/auth/google/login', methods=['GET'])
def google_oauth_login_redirect():
    """Generates and redirects directly to Google OAuth 2.0 consent page"""
    client_id = app.config.get('GOOGLE_CLIENT_ID', '')
    if not client_id:
        return jsonify({'error': 'GOOGLE_CLIENT_ID not configured in backend'}), 400

    frontend_redirect = request.args.get('frontend', 'http://localhost:5500/dashboard.html')
    backend_callback = request.args.get('redirect_uri') or app.config.get('GOOGLE_REDIRECT_URI') or f"{request.host_url.rstrip('/')}/api/auth/google/callback"
    
    state_data = json.dumps({'frontend': frontend_redirect, 'callback': backend_callback})
    state_encoded = base64.urlsafe_b64encode(state_data.encode()).decode()

    google_auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={urllib.parse.quote(client_id)}&"
        f"redirect_uri={urllib.parse.quote(backend_callback)}&"
        f"response_type=code&"
        f"scope={urllib.parse.quote('openid email profile')}&"
        f"access_type=offline&"
        f"prompt=select_account&"
        f"state={state_encoded}"
    )
    return redirect(google_auth_url)

@app.route('/api/auth/google/callback', methods=['GET'])
def google_oauth_callback():
    """Handles Google OAuth redirect callback, exchanges code, and redirects to frontend dashboard"""
    code = request.args.get('code')
    error = request.args.get('error')
    state = request.args.get('state')

    frontend_dest = 'http://localhost:5500/dashboard.html'
    backend_callback = app.config.get('GOOGLE_REDIRECT_URI') or f"{request.host_url.rstrip('/')}/api/auth/google/callback"
    
    if state:
        try:
            state_json = json.loads(base64.urlsafe_b64decode(state.encode()).decode())
            frontend_dest = state_json.get('frontend', frontend_dest)
            if state_json.get('callback'):
                backend_callback = state_json.get('callback')
        except Exception:
            pass

    login_fallback = frontend_dest.replace('dashboard.html', 'login.html')

    if error or not code:
        logger.warning(f"Google OAuth callback error: {error}")
        return redirect(f"{login_fallback}?error={urllib.parse.quote(error or 'access_denied')}")

    client_id = app.config.get('GOOGLE_CLIENT_ID', '')
    client_secret = app.config.get('GOOGLE_CLIENT_SECRET', '')

    try:
        token_resp = requests.post('https://oauth2.googleapis.com/token', data={
            'code': code,
            'client_id': client_id,
            'client_secret': client_secret,
            'redirect_uri': backend_callback,
            'grant_type': 'authorization_code'
        }, timeout=10)

        if token_resp.status_code != 200:
            logger.error(f"Google token exchange failed: {token_resp.text}")
            return redirect(f"{login_fallback}?error=token_exchange_failed")

        token_data = token_resp.json()
        id_token = token_data.get('id_token')
        access_token = token_data.get('access_token')

        google_user_info = None
        if id_token:
            google_user_info = verify_google_id_token(id_token, client_id)

        if not google_user_info and access_token:
            uinfo = requests.get('https://www.googleapis.com/oauth2/v3/userinfo', headers={'Authorization': f'Bearer {access_token}'}, timeout=10)
            if uinfo.status_code == 200:
                google_user_info = uinfo.json()

        if not google_user_info:
            return redirect(f"{login_fallback}?error=invalid_google_account")

        raw_email = google_user_info.get('email')
        if not isinstance(raw_email, str) or not raw_email.strip():
            return redirect(f"{login_fallback}?error=invalid_google_account")

        email = raw_email.strip().lower()
        sub_val = google_user_info.get('sub')
        sub = str(sub_val) if sub_val is not None else None
        pic_val = google_user_info.get('picture')
        picture = str(pic_val) if pic_val is not None else None
        first_name = str(google_user_info.get('given_name') or '')
        last_name = str(google_user_info.get('family_name') or '')
        name = str(google_user_info.get('name') or '')

        if not first_name and name:
            parts = name.split(' ')
            first_name = parts[0]
            last_name = ' '.join(parts[1:]) if len(parts) > 1 else ''

        user = User.query.filter(User.email.ilike(email)).first()
        if user:
            if not user.is_active:
                return redirect(f"{login_fallback}?error=account_deactivated")
            changed = False
            if hasattr(user, 'google_id') and not user.google_id and sub:
                setattr(user, 'google_id', sub)
                changed = True
            if hasattr(user, 'avatar_url') and not user.avatar_url and picture:
                setattr(user, 'avatar_url', picture)
                changed = True
            if not user.first_name and first_name:
                user.first_name = first_name
                changed = True
            if not user.last_name and last_name:
                user.last_name = last_name
                changed = True
            if changed:
                db.session.commit()
        else:
            base_username = email.split('@')[0]
            username = base_username
            counter = 1
            while User.query.filter_by(username=username).first():
                username = f"{base_username}{counter}"
                counter += 1

            random_hash = generate_password_hash(secrets.token_urlsafe(32))
            user = User(
                id=uuid.uuid4(),
                email=email,
                username=username,
                password_hash=random_hash,
                first_name=first_name,
                last_name=last_name,
                google_id=sub,
                avatar_url=picture,
                auth_provider='google',
                is_active=True
            )

            db.session.add(user)
            db.session.commit()

        app_jwt = create_access_token(identity=str(user.id))
        user_b64 = base64.urlsafe_b64encode(json.dumps(user.to_dict()).encode()).decode()

        # Redirect to dashboard with token and encoded user
        separator = '&' if '?' in frontend_dest else '?'
        return redirect(f"{frontend_dest}{separator}token={app_jwt}&user={user_b64}")

    except Exception as e:
        logger.error(f"Callback processing error: {e}", exc_info=True)
        return redirect(f"{login_fallback}?error=auth_failed")

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    logger.info(f"Registration request: {data.get('email') if data else 'No data'}")
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    email = data.get('email')
    password = data.get('password')
    first_name = data.get('first_name', '')
    last_name = data.get('last_name', '')
    username = data.get('username', email.split('@')[0] if email else 'user')
    
    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400
    
    # Check if user exists
    existing_user = User.query.filter((User.email == email) | (User.username == username)).first()
    if existing_user:
        return jsonify({'error': 'User already exists'}), 409
    
    # Create user
    user = User(
        id=uuid.uuid4(),
        email=email,
        username=username,
        password_hash=generate_password_hash(password),
        first_name=first_name,
        last_name=last_name
    )
    
    db.session.add(user)
    db.session.commit()
    
    logger.info(f"[OK] User registered: {email}")
    
    return jsonify({
        'message': 'User created successfully',
        'user': user.to_dict()
    }), 201

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    logger.info(f"Login request: {data.get('email') if data else 'No data'}")
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400
    
    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({'error': 'Invalid credentials'}), 401
    
    access_token = create_access_token(identity=str(user.id))
    
    logger.info(f"[OK] User logged in: {email}")
    
    return jsonify({
        'access_token': access_token,
        'user': user.to_dict()
    }), 200

@app.route('/api/auth/me', methods=['GET'])
@jwt_required()
def get_current_user():
    user_id = get_jwt_identity()
    user = User.query.filter_by(id=user_id).first()
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify(user.to_dict()), 200

@app.route('/api/chat', methods=['POST'])
@jwt_required()
def chat():
    data = request.get_json()
    user_id = get_jwt_identity()
    
    if not data or 'message' not in data:
        return jsonify({'error': 'Message required'}), 400
    
    message = data.get('message', '').strip()
    if not message:
        return jsonify({'error': 'Message cannot be empty'}), 400
        
    session_id = data.get('session_id')
    if not session_id or str(session_id).strip().lower() in ['none', 'null', 'undefined', '']:
        session_id = str(uuid.uuid4())
    else:
        session_id = str(session_id).strip()
    
    # Process message with the multi-agent coordinator
    try:
        agent_output = coordinator.process({'text': message})
        response = agent_output.get('response', "I couldn't process your request. Please try again.")
        agent_results = agent_output.get('agent_results', {})
    except Exception as e:
        logger.error(f"Error processing with agents: {str(e)}")
        response = f"I'm sorry, I encountered an internal error while processing your request: {str(e)}"
        agent_results = {}
        
    chat = ChatMessage(
        id=uuid.uuid4(),
        user_id=user_id,
        session_id=session_id,
        role='user',
        content=message
    )
    db.session.add(chat)
    
    chat_response = ChatMessage(
        id=uuid.uuid4(),
        user_id=user_id,
        session_id=session_id,
        role='assistant',
        content=response,
        agent_responses=agent_results,
        merged_response=response
    )
    db.session.add(chat_response)
    db.session.commit()
    
    return jsonify({
        'response': response,
        'session_id': session_id,
        'agent_results': agent_results
    }), 200

@app.route('/api/chat/history', methods=['GET'])
@jwt_required()
def get_chat_history():
    user_id = get_jwt_identity()
    session_id = request.args.get('session_id')
    
    query = ChatMessage.query.filter_by(user_id=user_id)
    if session_id and session_id.strip().lower() not in ['none', 'null', 'undefined', '']:
        query = query.filter_by(session_id=session_id.strip())
    
    messages = query.order_by(ChatMessage.created_at.asc()).all()
    return jsonify([msg.to_dict() for msg in messages]), 200

# Helper to extract text from PDF using PyMuPDF or pypdf fallback
def extract_text_from_pdf(file_path):
    text = ""
    try:
        fitz = __import__('fitz')
        doc = fitz.open(file_path)
        for page in doc:
            text += page.get_text() + "\n"
        if text.strip():
            return text.strip()
    except Exception as e:
        logger.error(f"Error extracting PDF text with PyMuPDF: {str(e)}")
    
    try:
        pypdf = __import__('pypdf')
        reader = pypdf.PdfReader(file_path)
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
        return text.strip()
    except Exception as e:
        logger.error(f"Error extracting PDF text with pypdf: {str(e)}")
        return text.strip()

# Helper to extract text from text files
def extract_text_from_txt(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error reading txt file: {str(e)}")
        return ""

# Helper to extract text from images using OCR (pytesseract) or inspect image metadata
def extract_text_from_image(file_path, filename):
    """Try OCR if available, inspect image properties, and return structured image context."""
    image_meta = {}
    try:
        pil_module = __import__('PIL.Image', fromlist=['Image'])
        Image = pil_module.Image if hasattr(pil_module, 'Image') else pil_module
        with Image.open(file_path) as img:
            image_meta['format'] = img.format
            image_meta['dimensions'] = f"{img.width}x{img.height}"
            image_meta['mode'] = img.mode
    except Exception as e:
        logger.error(f"Image inspection error on {filename}: {str(e)}")

    try:
        pytesseract = __import__('pytesseract')
        pil_module = __import__('PIL.Image', fromlist=['Image'])
        Image = pil_module.Image if hasattr(pil_module, 'Image') else pil_module
        img = Image.open(file_path)
        text = pytesseract.image_to_string(img)
        if text.strip():
            logger.info(f"OCR extracted {len(text)} chars from {filename}")
            return text.strip()
    except Exception:
        pass

    ext = os.path.splitext(filename)[1].lower()
    dims = image_meta.get('dimensions', 'High-resolution diagnostic')
    fmt = image_meta.get('format', ext.lstrip('.').upper())
    return f"[Medical Image Upload: {filename}]\nImage Format: {fmt}\nResolution: {dims}\nColor Mode: {image_meta.get('mode', 'RGB')}"

@app.route('/api/chat/sessions', methods=['GET'])
@jwt_required()
def get_chat_sessions():
    user_id = get_jwt_identity()
    
    # Query all user messages, ordered by creation time ascending
    messages = ChatMessage.query.filter_by(user_id=user_id).order_by(ChatMessage.created_at.asc()).all()
    
    sessions = {}
    for msg in messages:
        sid = str(msg.session_id).strip()
        if not sid or sid.lower() in ['none', 'null', 'undefined']:
            continue
            
        content_text = msg.content or ''
        # Clean up title for upload messages
        if '💬 **Inquiry:** ' in content_text:
            display_title = content_text.split('💬 **Inquiry:** ')[1].strip()
        elif content_text.startswith('🖼️ Uploaded') or content_text.startswith('📄 Uploaded'):
            display_title = content_text.replace('\n', ' ').strip()
        else:
            display_title = content_text.replace('\n', ' ').strip()

        if sid not in sessions:
            title = display_title
            if len(title) > 36:
                title = title[:36] + '...'
            sessions[sid] = {
                'session_id': sid,
                'title': title,
                'preview': title,
                'created_at': msg.created_at.isoformat() if msg.created_at else None,
                'updated_at': msg.created_at.isoformat() if msg.created_at else None
            }
        else:
            preview = display_title
            if len(preview) > 60:
                preview = preview[:60] + '...'
            sessions[sid]['preview'] = preview
            sessions[sid]['updated_at'] = msg.created_at.isoformat() if msg.created_at else None
            
    sorted_sessions = sorted(sessions.values(), key=lambda x: x['updated_at'] or '', reverse=True)
    return jsonify(sorted_sessions), 200

@app.route('/api/reports/upload', methods=['POST'])
@jwt_required()
def upload_report():
    user_id = get_jwt_identity()
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
        
    file = request.files['file']
    raw_session_id = request.form.get('session_id')
    user_message = request.form.get('message', '').strip()
    
    if not raw_session_id or raw_session_id.strip().lower() in ['none', 'null', 'undefined', '']:
        session_id = str(uuid.uuid4())
    else:
        session_id = raw_session_id.strip()
    
    if not file or not file.filename:
        return jsonify({'error': 'No selected file'}), 400
        
    try:
        from werkzeug.utils import secure_filename
        filename = secure_filename(file.filename) or f"upload_{uuid.uuid4().hex[:8]}.png"
        
        # Ensure UPLOAD_FOLDER exists
        upload_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, f"{uuid.uuid4()}_{filename}")
        file.save(file_path)
        
        ext = os.path.splitext(filename)[1].lower()
        extracted_text = ""

        # --- Determine file type and extract text/description ---
        IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.tif', '.dcm'}

        if ext == '.pdf':
            extracted_text = extract_text_from_pdf(file_path)
        elif ext in ['.txt', '.log', '.md', '.csv']:
            extracted_text = extract_text_from_txt(file_path)
        elif ext in IMAGE_EXTENSIONS:
            extracted_text = extract_text_from_image(file_path, filename)
        else:
            extracted_text = f"[Uploaded document: {filename}]"
            
        if not extracted_text.strip():
            extracted_text = f"[Uploaded document: {filename}]"

        # --- Build base64 preview for images (sent back to frontend) ---
        image_preview_b64 = None
        if ext in IMAGE_EXTENSIONS:
            try:
                with open(file_path, 'rb') as img_file:
                    img_bytes = img_file.read()
                    image_preview_b64 = f"data:image/{ext.lstrip('.')};base64," + base64.b64encode(img_bytes).decode('utf-8')
            except Exception as e:
                logger.error(f"Error encoding image preview: {str(e)}")
            
        file_size = os.path.getsize(file_path)
        
        # Analyze using ReportSummaryAgent from coordinator
        report_agent = coordinator.agents.get('report')
        if report_agent:
            try:
                agent_input = {
                    'text': extracted_text,
                    'user_query': user_message,
                    'file_name': filename,
                    'file_type': ext,
                    'image_path': file_path
                }
                report_results = report_agent.execute(agent_input)
                summary = report_results.get('response', 'Unable to summarize report.')
                findings = report_results.get('findings', [])
                abnormal_values = report_results.get('abnormal_values', [])
                medical_terms = report_results.get('medical_terms', {})
            except Exception as e:
                logger.error(f"Error running Report Summary Agent: {str(e)}")
                summary = f"Error analyzing report: {str(e)}"
                findings = []
                abnormal_values = []
                medical_terms = {}
                report_results = {}
        else:
            summary = "Report Summary Agent is not available."
            findings = []
            abnormal_values = []
            medical_terms = {}
            report_results = {}
            
        # Create database entry
        report = MedicalReport(
            id=uuid.uuid4(),
            user_id=user_id,
            filename=filename,
            file_path=file_path,
            file_size=file_size,
            file_type=ext,
            extracted_text=extracted_text,
            summary=summary,
            key_findings=findings,
            abnormal_values=abnormal_values,
            medical_terms=medical_terms
        )
        db.session.add(report)
        
        # If session_id is not set or empty, generate a new one
        if not session_id or session_id == 'null' or session_id == 'undefined':
            session_id = str(uuid.uuid4())

        # Build descriptive user message (include optional user question)
        if ext in IMAGE_EXTENSIONS:
            icon = "🖼️"
            type_label = "medical image"
        else:
            icon = "📄"
            type_label = "report"

        if user_message:
            user_content = f"{icon} Uploaded {type_label}: {filename}\n\n💬 **Inquiry:** {user_message}"
        else:
            user_content = f"{icon} Uploaded {type_label}: {filename}"
            
        # Add user and assistant messages
        user_msg = ChatMessage(
            id=uuid.uuid4(),
            user_id=user_id,
            session_id=session_id,
            role='user',
            content=user_content
        )
        db.session.add(user_msg)
        
        assistant_msg = ChatMessage(
            id=uuid.uuid4(),
            user_id=user_id,
            session_id=session_id,
            role='assistant',
            content=summary,
            agent_responses={'report': report_results},
            merged_response=summary
        )
        db.session.add(assistant_msg)
        db.session.commit()
        
        result = {
            'message': 'File uploaded and analyzed successfully',
            'session_id': session_id,
            'report': report.to_dict(),
            'chat_response': summary,
            'is_image': ext in IMAGE_EXTENSIONS,
            'filename': filename,
            'user_message': user_message
        }
        if image_preview_b64:
            result['image_preview'] = image_preview_b64

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Upload and analysis failed with error: {str(e)}", exc_info=True)
        return jsonify({'error': f'Failed to process file: {str(e)}'}), 500


@app.route('/api/chat/session/<session_id>', methods=['DELETE'])
@jwt_required()
def delete_chat_session(session_id):
    try:
        user_id = get_jwt_identity()
        clean_session_id = str(session_id).strip()
        
        # Delete all messages in this session for this user
        messages = ChatMessage.query.filter_by(
            user_id=user_id,
            session_id=clean_session_id
        ).all()
        
        if not messages:
            # Fallback search in case session_id had whitespace or partial formatting
            messages = ChatMessage.query.filter(
                ChatMessage.user_id == user_id,
                ChatMessage.session_id.ilike(f"%{clean_session_id}%")
            ).all()
        
        deleted_count = len(messages)
        for msg in messages:
            db.session.delete(msg)
            
        db.session.commit()
        
        return jsonify({
            'message': 'Session deleted successfully',
            'deleted_count': deleted_count
        }), 200
        
    except Exception as e:
        logger.error(f"Error deleting chat session {session_id}: {str(e)}", exc_info=True)
        return jsonify({'error': f'Failed to delete chat: {str(e)}'}), 500

@app.route('/api/users', methods=['GET'])
def get_users():
    users = User.query.all()
    return jsonify([user.to_dict() for user in users]), 200

if __name__ == '__main__':
    logger.info("Starting Multi-Agent AI Healthcare Backend...")
    logger.info("Server running on http://localhost:5000")
    logger.info("Database: multiagent_db")
    app.run(debug=True, host='0.0.0.0', port=5000)