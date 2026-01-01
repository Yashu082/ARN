# Resume Analyzer

## Overview
A web application that compares a resume PDF with a job description and reports a match score with a clear skill breakdown. It addresses the need for a simple, explainable check of how well a resume aligns with a target role. The approach uses deterministic role–skill mapping for primary scoring and semantic similarity as a secondary signal. The interface is intentionally minimal and manually reviewed.

## Features
- Upload resume (PDF)
- Select target role
- Deterministic skill matching
- Semantic text similarity scoring
- Clear output of matched and missing skills
- Robust error handling

## How It Works (High Level)
- Resume text extraction: PDF text is extracted server-side
- Role normalization: target role is inferred/normalized from the job description
- Skill matching using predefined role–skill data: deterministic lookup and coverage calculation
- Similarity scoring: sentence embeddings are compared to add a secondary signal
- Result presentation: overall score with category breakdown and suggestions

## Tech Stack
**Backend**
- Python
- Flask

**Frontend**
- HTML
- CSS (Tailwind via CDN)
- JavaScript (form submission only; no framework)

**Utilities**
- PDF processing: PyMuPDF (fitz)
- Embeddings: sentence-transformers
- Testing: pytest

## Setup Instructions

### Prerequisites
- **Python 3.10+** (3.11 recommended)
- **pip**
- **Internet connection** for the initial model download and any additional package downloads

### Installation (Windows PowerShell example)
1. Open PowerShell and change to the project root:
   - `cd "C:\Users\Yaswa\OneDrive\Desktop\AI Resume Analyzer"`
2. Create and activate a virtual environment:
   - `python -m venv venv`
   - `.\
env\Scripts\Activate.ps1`
   - If activation is blocked, run as current user:
     - `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force`
3. Upgrade pip:
   - `python -m pip install --upgrade pip`
4. Install dependencies:
   - `pip install -r requirements.txt`

> Note: `torch` can be platform-specific or large. If `pip install -r requirements.txt` fails on `torch`, visit https://pytorch.org/get-started/locally/ and run the recommended install command for your OS/CUDA configuration, then re-run `pip install -r requirements.txt` to satisfy remaining packages.

### Run locally
- Start the server:
  - `python app.py`
- Open the app in your browser at: `http://localhost:5000`

### Usage & constraints
- **Resume format:** PDF only (file extension `.pdf`).
- **Max file size:** 10 MB (enforced by the app).
- **Job description length:** Minimum 50 characters, maximum 5000 characters.
- **Model download:** The app uses `sentence-transformers` with model `stsb-roberta-large` which downloads on first run and may take several minutes and extra disk space.
- **Temporary uploads:** Uploaded resumes are saved temporarily to `static/uploads` and removed after analysis.

### Testing
- Run unit tests:
  - `pytest -q`
- Tests focus on role detection and skill-matching logic (`test_utils.py`).

### Troubleshooting
- **Model load failures:** Ensure you have an internet connection and `torch` is installed correctly for your platform (see PyTorch install guide).
- **Missing `role_skill_mapping.json`:** The application will exit on startup if the file is missing or invalid JSON. Ensure the file exists in the project root.
- **PowerShell activation errors:** If `Activate.ps1` is blocked, adjust execution policy as shown above.

If you'd like, I can add a short Troubleshooting FAQ or small example commands to the README — tell me which areas you'd like expanded.
## Design Decisions
- Why deterministic skill matching was chosen
  - Predictable behavior, explainable results, and easy maintenance by editing the curated role–skill data

- Why NER-based skill extraction was avoided
  - General NER tag sets do not capture technical skills reliably; domain mismatch and false positives increase post-processing and maintenance cost

- Why semantic similarity is secondary
  - Skill coverage is the primary signal for correctness and explainability; similarity helps when wording differs but is not the main driver of the score

- Why the UI is intentionally minimal
  - Reduce cognitive load, keep the flow clear (upload → role/description → results), and avoid distractions. A small surface area improves reliability and keeps focus on the analysis.