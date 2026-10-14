
import sqlite3

DB_NAME = "smartevent.db"

connection = sqlite3.connect(DB_NAME)
cursor = connection.cursor()

try:
    # Add role column if it does not already exist.
    user_columns = {
        row[1] for row in cursor.execute(
            "PRAGMA table_info(users)"
        ).fetchall()
    }

    if "role" not in user_columns:
        cursor.execute("""
            ALTER TABLE users
            ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'USER'
        """)
        print("Added role column to users.")

    # Add organizer_id column if it does not already exist.
    event_columns = {
        row[1] for row in cursor.execute(
            "PRAGMA table_info(events)"
        ).fetchall()
    }

    if "organizer_id" not in event_columns:
        cursor.execute("""
            ALTER TABLE events
            ADD COLUMN organizer_id INTEGER REFERENCES users(id)
        """)
        print("Added organizer_id column to events.")

    connection.commit()
    print("Module 21 database migration completed.")

except Exception:
    connection.rollback()
    raise

finally:
    connection.close()
