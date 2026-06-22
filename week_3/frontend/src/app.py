from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI()

templates = Jinja2Templates(directory=Path(__file__).resolve().parent / "templates")


@app.get("/")
async def index(request: Request):
    backend_url = os.getenv("BACKEND_URL", "http://localhost:8001")
    return templates.TemplateResponse(request, "chat_page.html", {"backend_url": backend_url})