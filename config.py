import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")

    # MySQL settings
    DB_HOST = "localhost"
    DB_USER = "root"
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    DB_NAME = "interview_prep1"


if not Config.SECRET_KEY:
    raise ValueError(
        "SECRET_KEY is not set. "
        "Add SECRET_KEY=your-secret-key to the .env file."
    )

