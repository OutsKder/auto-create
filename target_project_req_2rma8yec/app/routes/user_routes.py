from flask import Blueprint, request, jsonify
from app.models import User
from app import db
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime
from functools import wraps

bp = Blueprint('user_routes', __name__, url_prefix='/api/v1/users')

# Helper function for token required
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.args.get('token')

        if not token:
            return jsonify({'message': 'Token is missing!'}), 403

        try:
            data = jwt.decode(token, 'secret_key', algorithms=['HS256'])
            current_user = User.query.filter_by(userId=data['userId']).first()
        except:
            return jsonify({'message': 'Token is invalid!'}), 403

        return f(current_user, *args, **kwargs)

    return decorated

@bp.route('/register', methods=['POST'])
def register_user():
    data = request.get_json()
    hashed_password = generate_password_hash(data['password'], method='sha256')
    new_user = User(username=data['username'], passwordHash=hashed_password, role=data['role'])
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'message': 'New user created!'}), 201

@bp.route('/login', methods=['POST'])
def login_user():
    auth = request.authorization

    if not auth or not auth.username or not auth.password:
        return jsonify({'message': 'Could not verify'}), 401, {'WWW-Authenticate': 'Basic realm="Login Required!"'}

    user = User.query.filter_by(username=auth.username).first()

    if not user:
        return jsonify({'message': 'Could not verify'}), 401, {'WWW-Authenticate': 'Basic realm="Login Required!"'}

    if check_password_hash(user.passwordHash, auth.password):
        token = jwt.encode({'userId': user.userId, 'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=30)}, 'secret_key', algorithm='HS256')
        return jsonify({'token': token})

    return jsonify({'message': 'Could not verify'}), 401, {'WWW-Authenticate': 'Basic realm="Login Required!"'}

@bp.route('/<int:userId>/password', methods=['PUT'])
@token_required
def update_password(current_user, userId):
    if current_user.userId != userId:
        return jsonify({'message': 'Cannot perform that function!'}), 403

    data = request.get_json()
    hashed_password = generate_password_hash(data['password'], method='sha256')
    current_user.passwordHash = hashed_password
    db.session.commit()
    return jsonify({'message': 'Password updated!'})