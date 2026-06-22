import os
import tempfile
import asyncio
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Docker secrets override
secret_path = Path("/run/secrets/google_api_key")
if secret_path.exists():
    os.environ["GOOGLE_API_KEY"] = secret_path.read_text().strip()

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))

from week_2.find_skill_gaps import find_skill_gaps

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = str(
    Path(__file__).resolve().parent.parent.parent.parent
    / "week_1"
    / "data"
    / "3_gold"
    / "jobs.db"
)


class ChatRequest(BaseModel):
    message: str
    pdf_text: str = ""


@app.post("/chat")
async def chat(request: ChatRequest):
    resume_text = ""
    if request.pdf_text:
        resume_text = request.pdf_text
    elif request.message:
        resume_text = request.message

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(resume_text)
        tmp_path = tmp.name

    try:
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            result = await asyncio.get_event_loop().run_in_executor(
                pool, find_skill_gaps, tmp_path, DB_PATH
            )
            print("RESULT:", result)
            print("GAPS:", result.gaps)
            print("TOP:", result.top_missing_skills)
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    if not result.gaps:
        reply = "I couldn't detect any skill gaps. Please make sure your resume text is included."
    else:
        top = ", ".join(result.top_missing_skills) if result.top_missing_skills else "N/A"
        reply = (
            f"I found {len(result.gaps)} skill gaps in your resume.\n\n"
            f"Top missing skills: {top}\n\n"
            f"Full gap list: {', '.join(result.gaps[:20])}"
        )

    return JSONResponse({"reply": reply})