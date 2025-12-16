# Team CodeStorm — AI Loan Approval Simulation (Flask)

Hackathon project: a Flask web app that simulates an AI-assisted loan processing flow (KYC verification → underwriting decision → sanction letter PDF generation) with a simple web UI and agent-style conversation log. [web:456][web:471]

## Features
- Select an existing customer or add a new customer from the UI.
- Runs a simulated loan workflow:
  - Verification Agent (KYC details)
  - Underwriting Agent (rule-based eligibility checks)
  - Sanction Letter Generator (PDF)
- Generates a downloadable sanction letter PDF when approved.
- Stores customer records in SQLite created at runtime. [web:471]

## Tech Stack
- Python + Flask
- SQLite (local DB file created on first run)
- ReportLab (PDF generation)
- HTML/CSS + JavaScript (Fetch API) frontend

## Project Structure (key files/folders)
- `app1.py` → Flask server + business logic
- `generated_letters/` → runtime output folder for generated PDFs (ignored by git)
- `customers.db` → runtime SQLite DB file (ignored by git)

## Setup & Run (Local)

### 1) Clone repo
git clone https://github.com/Himanshu-Verma007/Team_CodeStorm.git
cd Team_CodeStorm

### 2) Create & activate virtual environment (recommended)

#### Windows (Git Bash)
python -m venv .venv
source .venv/Scripts/activate  # If this doesn't work: . .venv/Scripts/activate [web:473][web:476]

#### macOS / Linux
python3 -m venv .venv
source .venv/bin/activate

### 3) Install dependencies
pip install -r requirements.txt

If `requirements.txt` is not present, install manually:
pip install flask reportlab

### 4) Run the server
python app1.py

### 5) Open in browser
http://127.0.0.1:5001/

## How the Demo Works
1. Open the UI.
2. Select a customer and enter a loan amount.
3. Click “Start Simulation”.
4. If approved, click the “Download Your Sanction Letter” link to download the generated PDF.

## Notes
- `customers.db` is created automatically on startup and seeded with sample customers if empty.
- Generated PDFs are saved in `generated_letters/` and served via `/download/<filename>`.
- `customers.db` and `generated_letters/` are intentionally ignored in Git (via `.gitignore`) because they are runtime/generated files. [web:252][web:122]
