import mysql.connector
from groq import Groq
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from config import Config


# Rate Limiter 
limiter = Limiter(key_func=get_remote_address, default_limits=[])


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
