from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from database.db import db
from database.models import User
import uuid
import logging
import secrets
import requests
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests

bp = Blueprint('auth', __name__)
logger = logging.getLogger(__name__)

@bp.route('/google/client-id', methods=['GET'])
def get_google_client_id():
    """Returns the Google Client ID configured in current application environment"""
    client_id = current_app.config.get('GOOGLE_CLIENT_ID', '')
    return jsonify({'client_id': client_id}), 200

@bp.route('/google', methods=['POST'])
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

    client_id = current_app.config.get('GOOGLE_CLIENT_ID', '')
    client_secret = current_app.config.get('GOOGLE_CLIENT_SECRET', '')
    google_user_info = None

    # 1. Verification via ID Token (JWT)
    if token:
        try:
            request_adapter = google_requests.Request()
            id_info = google_id_token.verify_oauth2_token(
                token,
                request_adapter,
                client_id if client_id else None,
                clock_skew_in_seconds=10
            )
            google_user_info = {
                'email': id_info.get('email'),
                'email_verified': id_info.get('email_verified', True),
                'first_name': id_info.get('given_name', ''),
                'last_name': id_info.get('family_name', ''),
                'name': id_info.get('name', ''),
                'picture': id_info.get('picture', ''),
                'sub': id_info.get('sub')
            }
        except Exception as e:
            logger.warning(f"google-auth verify failed ({e}). Attempting tokeninfo fallback...")
            try:
                resp = requests.get(f"https://oauth2.googleapis.com/tokeninfo?id_token={token}", timeout=10)
                if resp.status_code == 200:
                    id_info = resp.json()
                    google_user_info = {
                        'email': id_info.get('email'),
                        'email_verified': id_info.get('email_verified') == 'true' or id_info.get('email_verified') is True,
                        'first_name': id_info.get('given_name', ''),
                        'last_name': id_info.get('family_name', ''),
                        'name': id_info.get('name', ''),
                        'picture': id_info.get('picture', ''),
                        'sub': id_info.get('sub')
                    }
                else:
                    logger.error(f"Google tokeninfo endpoint failed: {resp.text}")
            except Exception as net_err:
                logger.error(f"Google tokeninfo network error: {net_err}")

    # 2. Verification via Access Token
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
                    request_adapter = google_requests.Request()
                    id_info = google_id_token.verify_oauth2_token(id_tok, request_adapter, client_id if client_id else None)
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

    if not google_user_info or not google_user_info.get('email'):
        return jsonify({'error': 'Invalid or unverified Google account information'}), 401

    email = google_user_info['email'].strip().lower()
    sub = google_user_info.get('sub')
    picture = google_user_info.get('picture')
    first_name = google_user_info.get('first_name') or ''
    last_name = google_user_info.get('last_name') or ''
    name = google_user_info.get('name') or ''

    if not first_name and name:
        parts = name.split(' ')
        first_name = parts[0]
        last_name = ' '.join(parts[1:]) if len(parts) > 1 else ''

    try:
        user = User.query.filter(User.email.ilike(email)).first()

        if user:
            if not user.is_active:
                return jsonify({'error': 'This user account is deactivated. Please contact support.'}), 403

            changed = False
            if hasattr(user, 'google_id') and not user.google_id and sub:
                user.google_id = sub
                changed = True
            if hasattr(user, 'avatar_url') and not user.avatar_url and picture:
                user.avatar_url = picture
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
                    logger.warning(f"Could not update profile fields: {db_err}")

            logger.info(f"[OK] Existing user logged in via Google: {email}")
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
                is_active=True
            )
            if hasattr(user, 'google_id'):
                user.google_id = sub
            if hasattr(user, 'avatar_url'):
                user.avatar_url = picture
            if hasattr(user, 'auth_provider'):
                user.auth_provider = 'google'

            db.session.add(user)
            db.session.commit()
            logger.info(f"[OK] New user created automatically via Google: {email}")

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

@bp.route('/register', methods=['POST'])
def register():
    """Register a new user"""
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
    existing = User.query.filter((User.email == email) | (User.username == username)).first()
    if existing:
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

@bp.route('/login', methods=['POST'])
def login():
    """Login user"""
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
    
    return jsonify({
        'access_token': access_token,
        'user': user.to_dict()
    }), 200

@bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """Get current user"""
    user_id = get_jwt_identity()
    user = User.query.filter_by(id=user_id).first()
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify(user.to_dict()), 200