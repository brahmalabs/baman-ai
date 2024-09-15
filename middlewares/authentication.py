from functools import wraps
from flask import request, jsonify, g
import jwt
import os
from models.teacher import Teacher
from models.student import Student

def token_required_teacher(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        # Get the token from the Authorization header
        if 'Authorization' in request.headers:
            token = request.headers['Authorization']
            if token.startswith('Bearer '):
                token = token[7:]

        if not token:
            return jsonify({'error': 'Token is missing!'}), 401

        try:
            # Decode the token
            data = jwt.decode(token, os.getenv('SECRET_KEY'), algorithms=['HS256'])
            # Optionally, you can add more checks here, such as checking user roles or permissions
            
            # Retrieve the user from the database
            user = Teacher.objects(google_id=data['sub']).first()
            if not user:
                return jsonify({'error': 'User not found!'}), 401
            # Store the user in the global object
            g.current_user = user
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token!'}), 401

        return f(*args, **kwargs)

    return decorated

def token_required_student(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            token = request.headers['Authorization']
            if token.startswith('Bearer '):
                token = token[7:]

        if not token:
            return jsonify({'error': 'Token is missing!'}), 401

        try:
            data = jwt.decode(token, os.getenv('SECRET_KEY'), algorithms=['HS256'])
            user = Student.objects(google_id=data['sub']).first()
            if not user:
                return jsonify({'error': 'User not found!'}), 401
            g.current_user = user
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token!'}), 401

        return f(*args, **kwargs)

    return decorated