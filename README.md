# Delivery Web App

A polished food-delivery web app prototype with a FastAPI backend and a React/Vite frontend.

## Stack

- Backend: FastAPI + SQLite
- Frontend: React + Vite + plain CSS

## Run

Backend:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Frontend:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

