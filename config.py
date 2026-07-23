import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")

    DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"

    # MySQL settings
    DB_HOST = os.getenv("MYSQLHOST", "localhost")
    DB_PORT = int(os.getenv("MYSQLPORT", "3306"))
    DB_NAME = os.getenv("MYSQLDATABASE", "interview_prep1")
    DB_USER = os.getenv("MYSQLUSER", "root")
    DB_PASSWORD = os.getenv("MYSQLPASSWORD", "")

    # Session cookies
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("FLASK_ENV") == "production"


if not Config.SECRET_KEY:
    raise ValueError(
        "SECRET_KEY is not set. "
        "Add SECRET_KEY=your-secret-key to the .env file."
    )

