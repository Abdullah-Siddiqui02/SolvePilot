import mysql.connector
from config import Config

def migrate_questions():
    try:
        db = mysql.connector.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
        )
        cursor = db.cursor()

        # Add description column if it doesn't exist
        try:
            cursor.execute("ALTER TABLE questions ADD COLUMN description TEXT;")
            print("Added 'description' column to 'questions' table.")
        except mysql.connector.Error as err:
            if err.errno == 1060: # Duplicate column name
                print("Column 'description' already exists.")
            else:
                print(f"Error adding description: {err}")

        # Add samples column if it doesn't exist
        try:
            cursor.execute("ALTER TABLE questions ADD COLUMN samples TEXT;")
            print("Added 'samples' column to 'questions' table.")
        except mysql.connector.Error as err:
            if err.errno == 1060:
                print("Column 'samples' already exists.")
            else:
                print(f"Error adding samples: {err}")

        db.commit()
        cursor.close()
        db.close()
        print("Migration complete.")

    except Exception as e:
        print(f"Connection error: {e}")

if __name__ == "__main__":
    migrate_questions()
