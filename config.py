import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    JUDGE0_API_KEY = os.getenv("JUDGE0_API_KEY")

    # MySQL settings
    DB_HOST = "localhost"
    DB_USER = "root"
    DB_PASSWORD = os.getenv("DB_PASSWORD", "Abdullah@#")
    DB_NAME = "interview_prep1"

