@echo off
echo === RTO Compliance Bot - Local Setup ===

if not exist .env (
    copy .env.example .env
    echo Created .env from .env.example - please fill in your OPENAI_API_KEY
)

python scripts\init_db.py
python scripts\seed_data.py
python tests\test_compliance.py

echo.
echo === Starting FastAPI server on http://localhost:8000 ===
echo Swagger UI: http://localhost:8000/docs
echo Chat UI:    http://localhost:8000/api/v1/chat
echo.
uvicorn app.api.main:app --reload --port 8000
