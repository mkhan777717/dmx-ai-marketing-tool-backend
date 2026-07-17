# AI Marketing Suite - Backend

Backend service for the AI Marketing Suite.

## Tech Stack

- FastAPI
- Python 3.13
- PostgreSQL (planned)
- Modular Monolith Architecture

## Setup

### Create Virtual Environment

```bash
py -m venv .venv
```

### Activate

Windows

```bash
.venv\Scripts\Activate.ps1
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run

```bash
uvicorn app.main:app --reload
```

### Swagger

```
http://127.0.0.1:8000/docs
```