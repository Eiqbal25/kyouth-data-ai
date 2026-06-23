from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from pathlib import Path
from dotenv import load_dotenv
import os
import sqlite3

load_dotenv()

app = FastAPI()

templates = Jinja2Templates(directory=Path(__file__).resolve().parent / "templates")

DB_PATH = (
    Path("/data/jobs.db")
    if Path("/data/jobs.db").exists()
    else Path(__file__).resolve().parent.parent.parent.parent
    / "week_1"
    / "data"
    / "3_gold"
    / "jobs.db"
)


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.get("/")
async def index(request: Request):
    backend_url = os.getenv("BACKEND_URL", "http://localhost:8001")
    return templates.TemplateResponse(
        request, "chat_page.html", {"backend_url": backend_url}
    )


@app.get("/dashboard")
async def dashboard(request: Request):
    return templates.TemplateResponse(request, "dashboard.html", {})


@app.get("/api/quality-distribution")
async def quality_distribution():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT quality, COUNT(*) as count FROM jobs GROUP BY quality")
    rows = cur.fetchall()
    conn.close()
    return {row["quality"]: row["count"] for row in rows}


@app.get("/api/top-companies")
async def top_companies():
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT company, COUNT(*) as count FROM jobs GROUP BY company ORDER BY count DESC LIMIT 10"
    )
    rows = cur.fetchall()
    conn.close()
    return [{"company": row["company"], "count": row["count"]} for row in rows]


@app.get("/api/search")
async def search(q: str = ""):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT source_id, job_title, company, quality FROM jobs WHERE job_title LIKE ? OR company LIKE ? LIMIT 20",
        (f"%{q}%", f"%{q}%"),
    )
    rows = cur.fetchall()
    conn.close()
    return [
        {
            "source_id": row["source_id"],
            "job_title": row["job_title"],
            "company": row["company"],
            "quality": row["quality"],
        }
        for row in rows
    ]
