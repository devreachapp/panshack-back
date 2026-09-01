
from app.auth import bp as auth_bp


# ------------------------------------------------------------------
# Token Verification Decorator
# ------------------------------------------------------------------
import traceback
import functools
from datetime import datetime, timedelta, timezone
from flask import Blueprint, request, jsonify
import jwt
from app.models import db, User,Wallet

from flask import Blueprint, request, jsonify
from functools import wraps


from flask import Blueprint, request, jsonify


SECRET_KEY = "nobemistake9ice"
ALGORITHM = "HS256"

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get("Authorization", None)
        print("Authorization header:", auth_header)

        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
        print("Token received:", token)

        if not token:
            return jsonify({"message": "Token is missing"}), 401

        try:
            data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            print("Decoded JWT data:", data)
            current_user = User.query.get(data["id"])
            if not current_user:
                return jsonify({"message": "User not found"}), 404
        except jwt.ExpiredSignatureError:
            return jsonify({"message": "Token has expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"message": "Invalid token"}), 401
        except Exception as e:
            import traceback; traceback.print_exc()
            return jsonify({"message": "Token verification failed"}), 500

        return f(current_user, *args, **kwargs)
    return decorated


@auth_bp.route('/auth/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    
    # Validation
    required_fields = ['email', 'password', 'name', 'phone']
    if not all(field in data and data[field] for field in required_fields):
        return jsonify({"message": "All fields (name, email, phone, password) are required"}), 400

    if User.query.filter_by(email=data['email']).first():
        return jsonify({"message": "Email already exists"}), 400

    try:
        # Create user (mapping React's `name` to backend `full_name`)
        user = User(
            email=data['email'],
            full_name=data['name'],
            phone=data['phone']
        )
        user.set_password(data['password'])
        db.session.add(user)
        db.session.flush()  # Ensures user.id is generated before committing wallet

        # Provision Default Fiat NGN Wallet
        ngn_wallet = Wallet(user_id=user.id, currency='NGN', balance=0.0)
        db.session.add(ngn_wallet)
        
        db.session.commit()

        # Token generation using PyJWT matching token_required payload format
        token = jwt.encode(
            {
                "id": user.id,
                "exp": datetime.now(timezone.utc) + timedelta(hours=24)
            },
            SECRET_KEY,
            algorithm="HS256"
        )

        return jsonify({
            "message": "User created successfully",
            "token": token,
            "access_token": token,
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.full_name
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "An error occurred while creating your account"}), 500


@auth_bp.route('/auth/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"message": "Email and password are required"}), 400

    user = User.query.filter_by(email=email).first()
    
    if not user or not user.check_password(password):
        return jsonify({"message": "Invalid email or password"}), 401

    # Token generation using PyJWT matching token_required payload format
    token = jwt.encode(
        {
            "id": user.id,
            "exp": datetime.now(timezone.utc) + timedelta(hours=24)
        },
        SECRET_KEY,
        algorithm="HS256"
    )

    return jsonify({
        "message": "Login successful",
        "token": token,
        "access_token": token,
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.full_name
        }
    }), 200


@auth_bp.route('/auth/set-pin', methods=['POST'])
@token_required
def set_pin(current_user):
    data = request.get_json() or {}
    pin = data.get('pin')

    if not pin or len(str(pin)) < 4:
        return jsonify({"message": "A valid PIN is required"}), 400

    current_user.set_pin(pin)
    db.session.commit()
    
    return jsonify({"message": "PIN updated successfully"}), 200