# CyberNova Sales Intelligence Dashboard

**Developer:** Mmopiemang Mmopiemang  
**Programme:** BSc in Business Intelligence & Data Analytics  
**Module:** CET333 Product Development  
**Delivery Date:** 15 May 2026

## System Requirements

- Python 3.13
- Windows 10/11 or Ubuntu 24
- 4GB RAM minimum (DoWhy causal pipeline uses ~1.5GB peak)
- Internet connection (Groq API, Google Fonts)

## Installation

```bash
# 1. Clone or extract the project
cd cyber_draft/dashboard

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
# Edit .env with your DB_PATH, SECRET_KEY, GROQ_API_KEY, SMTP credentials

# 4. Seed the initial systems manager account
python auth_test.py   # PRE-STEP only — seeds sysadmin

# 5. Load data (if database not already populated)
python etl_test.py
```

## Running the Application

Open two terminals from the `dashboard/` directory:

**Terminal 1 — API Server:**
```bash
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

**Terminal 2 — Frontend:**
```bash
python frontend/app.py
```

Open `http://127.0.0.1:8081` in any modern browser.

## Default Credentials

| Username | Password | Role |
|----------|----------|------|
| sysadmin | Admin1234! | Systems Manager |

New accounts must be registered via `/register` and approved by the systems manager.

## Architecture