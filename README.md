# SmartEvent Backend

FastAPI backend for the SmartEvent event discovery and ticket booking system.

## Run
1. Create virtual environment:
   python -m venv .venv

2. Activate on Windows:
   .venv\Scripts\activate

3. Install:
   pip install -r requirements.txt

4. Start:
   uvicorn app.main:app --reload

5. Open:
   http://127.0.0.1:8000/docs

Default database is SQLite for easy setup. You can later replace DATABASE_URL with PostgreSQL.
