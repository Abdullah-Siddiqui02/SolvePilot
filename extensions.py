"""
Shared extensions: database connection and Groq AI client.
Imported by route modules that need them.
"""

import mysql.connector
from groq import Groq
from config import Config


# ── Database ────────────────────────────────────────────
def get_db():
    """Create and return a MySQL connection and cursor."""
    db = mysql.connector.connect(
        host=Config.DB_HOST,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME,
    )
    return db, db.cursor(buffered=True)


db, cursor = get_db()


# ── AI Client ───────────────────────────────────────────
groq_client = Groq(api_key=Config.GROQ_API_KEY)
