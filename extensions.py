import secrets

import mysql.connector
from groq import Groq
from flask import session
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from config import Config


# Rate Limiter 
limiter = Limiter(key_func=get_remote_address, default_limits=[])


# CSRF helpers 
def generate_csrf_token():
    if "_csrf_token" not in session:
        session["_csrf_token"] = secrets.token_hex(32)
    return session["_csrf_token"]


def validate_csrf_token(token):
    stored = session.get("_csrf_token")
    if not stored or not secrets.compare_digest(stored, token):
        return False
    return True


# Database 
def get_db():
    """Create and return a MySQL connection and cursor."""
    db = mysql.connector.connect(
        host=Config.DB_HOST,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME,
    )
    return db, db.cursor(buffered=True)




# AI Client 
groq_client = Groq(api_key=Config.GROQ_API_KEY)
