# Week 3: System Integration & Application

A containerized full-stack chat application that integrates the Week 1 job listings pipeline and Week 2 AI skill gap detection into a production-ready microservices system.

---

## Project Overview

This project combines a FastAPI frontend and FastAPI backend into a microservices architecture, each running in its own Docker container and communicating over a shared Docker network. Users interact with a chat interface to submit their resume text or upload a PDF. The backend extracts their skills using Gemini, compares them against real Malaysian tech job listings from the Week 1 database, and returns a list of skill gaps.

The frontend also includes a bonus dashboard with Charts.js visualizations (quality distribution pie chart, top companies bar chart, and a live job search bar) powered by the Week 1 SQLite database.

---

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) with Docker Compose
- A Google Gemini API key (free tier at [https://aistudio.google.com](https://aistudio.google.com))
- The Week 1 database must exist at `week_1/data/3_gold/jobs.db` and be tagged with tech stacks (run `week_2/tag_data.py` first if not done)

Optional (to run without Docker):
- Python 3.14
- [uv](https://docs.astral.sh/uv/getting-started/installation/)

---

## Setup Instructions

### 1. Clone the repository

```bash
git clone https://github.com/Eiqbal25/kyouth-data-ai.git
cd kyouth-data-ai
```

### 2. Configure environment variables

Copy the example file and add your Gemini API key:

```bash
cp week_3/.env.example week_3/.env
```

Edit `week_3/.env`:

```
GOOGLE_API_KEY=your_gemini_api_key_here
```

### 3. Create Docker secrets

Docker secrets are used instead of plain environment variables for security:

```bash
mkdir week_3/secrets
echo "your_gemini_api_key_here" > week_3/secrets/google_api_key.txt
```

On Windows (PowerShell):

```powershell
mkdir week_3\secrets
[System.IO.File]::WriteAllText("week_3\secrets\google_api_key.txt", "your_gemini_api_key_here")
```

### 4. Ensure the Week 1 database is populated

The backend reads from `week_1/data/3_gold/jobs.db`. If you have not run the Week 1 pipeline yet:

```bash
cd week_1
uv sync
uv run python main.py all
```

Then tag the jobs with tech stacks (requires Gemini API key in `week_2/.env`):

```bash
cd week_2
uv sync
uv run python tag_data.py ../week_1/data/3_gold/jobs.db
```

---

## Usage

### Run with Docker Compose (recommended)

```bash
cd week_3
docker compose up --build
```

- Frontend (chat + dashboard): [http://localhost:8000](http://localhost:8000)
- Backend API: [http://localhost:8001](http://localhost:8001)
- Dashboard: [http://localhost:8000/dashboard](http://localhost:8000/dashboard)

### Run locally without Docker

**Terminal 1 — Backend:**

```bash
cd week_3/backend
uv sync
uv run uvicorn --app-dir src app:app --port 8001
```

**Terminal 2 — Frontend:**

```bash
cd week_3/frontend
uv sync
uv run uvicorn --app-dir src app:app --port 8000
```

Create `week_3/frontend/.env` with:

```
BACKEND_URL=http://localhost:8001
```

Create `week_3/backend/.env` with:

```
GOOGLE_API_KEY=your_gemini_api_key_here
```

### Expected inputs and outputs

**Text input:**

Type your skills or paste resume text into the chat box and press Send.

Example input:
```
I have experience with Python, SQL, pandas, numpy, and data visualization.
```

Example output:
```
I found 120 skill gaps in your resume.

Top missing skills: aws, git, docker, azure, node.js

Full gap list: .net, agile, ai, airflow, angular, ...
```

**PDF upload:**

Click the upload icon, select a PDF resume, then send a message. The PDF text is extracted in the browser using pdf.js and sent alongside the message.

---

## Landing Page

A public landing page explaining the full AI pipeline is deployed at:

**https://landing-production-bff4.up.railway.app/**

It covers:
- What the project does
- How each week contributes to the pipeline
- How to set up and use the app
- The system architecture

### Run landing page locally

```bash
cd week_3/landing
uv sync
uv run uvicorn --app-dir src app:app --port 8080
```

### Run with Docker

```bash
docker pull eiqbal25/landing:1.0
docker run -p 8080:8080 eiqbal25/landing:1.0
```

Docker Hub: https://hub.docker.com/r/eiqbal25/landing

## API / Function Reference

### Backend: `POST /chat`

**URL:** `http://localhost:8001/chat`

**Request (JSON):**
```json
{
  "message": "I know Python, SQL, and pandas",
  "pdf_text": ""
}
```

If `pdf_text` is provided, it takes priority over `message` as the resume source.

**Response (JSON):**
```json
{
  "reply": "I found 120 skill gaps in your resume.\n\nTop missing skills: aws, git, docker, azure, node.js\n\nFull gap list: ..."
}
```

**How the backend processes a request:**
1. Receives the JSON payload from the frontend
2. Writes the resume text to a temporary `.txt` file
3. Calls `find_skill_gaps(tmp_path, DB_PATH)` from Week 2
4. `find_skill_gaps` calls Gemini to extract resume skills and reads job tech stacks via MCP
5. Returns the gap list as a JSON response
6. Deletes the temporary file

### Frontend API endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Serves the chat page |
| `/dashboard` | GET | Serves the dashboard page |
| `/api/quality-distribution` | GET | Returns HIGH/LOW job quality counts |
| `/api/top-companies` | GET | Returns top 10 companies by job count |
| `/api/search?q=<query>` | GET | Searches jobs by title or company |

### Key JavaScript functions (`chat_page.html`)

**`sendMessage()`** — reads the user input and optional PDF text, sends a POST request to `BACKEND_URL/chat`, appends the response to the chat history, and resets the input field.

**`appendMessage(text, sender)`** — creates a chat bubble element and appends it to the chat history div. Sender is either `"user"` or `"bot"`.

**PDF upload handler** — listens for file selection on the hidden file input, reads the PDF using `pdfjsLib`, extracts all page text, and stores it in the `pdfText` variable for the next send.

### Docker network communication

The frontend and backend run in separate containers on a shared bridge network called `app-network`. Inside Docker, the frontend's `BACKEND_URL` is set to `http://localhost:8001`. The browser makes requests directly to the backend container's exposed port, not through the Docker internal hostname.

---

## Data / Assumptions

### JSON message structure

Messages between the browser and backend follow this schema:

```json
{
  "message": "string — user typed text",
  "pdf_text": "string — extracted PDF content, empty string if no PDF"
}
```

### Data flow

```
User types message / uploads PDF
        |
        v
Browser (chat_page.html)
  - pdf.js extracts PDF text (if uploaded)
  - sendMessage() POSTs JSON to BACKEND_URL/chat
        |
        v
Backend (app.py) — port 8001
  - Writes resume text to temp file
  - Calls find_skill_gaps(tmp_path, db_path)
        |
        v
Week 2: find_skill_gaps.py
  - Gemini extracts resume skills
  - MCP (db_server.py) reads tech stacks from jobs.db
  - Returns gaps = DB skills - resume skills
        |
        v
Backend returns JSON { "reply": "..." }
        |
        v
Browser renders reply as bot chat bubble
```

### Assumptions

- PDF content is extracted entirely in the browser before being sent. No PDF file is uploaded to the server.
- Resume text is sanitized against prompt injection before being sent to Gemini.
- The `jobs.db` database must have tech stacks populated (non-NULL) for meaningful gap detection. Jobs with NULL tech stacks are excluded from comparison.
- User messages are treated as resume skill descriptions, not as conversational queries.
- No conversation history is maintained between messages.

### Constraints

- PDF file size is not explicitly limited but very large PDFs may cause slow extraction in the browser.
- The Gemini free tier allows 20 requests per day per model. High usage will exhaust the quota.
- The gap list is capped at 20 skills in the displayed response, though all gaps are computed.

---

## Testing

### Frontend testing

| Test case | How to reproduce | Expected result |
|---|---|---|
| Send a text message | Type skills in input, press Send | Bot replies with skill gaps |
| Send with Enter key | Type message, press Enter | Same as clicking Send |
| Upload a PDF | Click upload icon, select PDF, send message | PDF text extracted and sent with message |
| Empty message | Click Send with empty input | No request sent |
| Dashboard charts | Visit `/dashboard` | Pie chart and bar chart render |
| Dashboard search | Type in search bar | Job results table appears |

### Backend testing

Test the `/chat` endpoint directly using curl:

```bash
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "I know Python, SQL, and pandas", "pdf_text": ""}'
```

Expected response:
```json
{"reply": "I found X skill gaps in your resume.\n\nTop missing skills: ..."}
```

### Docker communication test

With both containers running via `docker compose up`, send a message from the frontend at `http://localhost:8000`. Check the Docker Compose logs — you should see both:

```
frontend-1 | POST /chat OPTIONS 200 OK
backend-1  | POST /chat 200 OK
```

This confirms the frontend browser is successfully reaching the backend container through the exposed port.

---

## Limitations

- **No conversation memory** — each message is processed independently. The chatbot does not remember previous turns.
- **No user authentication** — anyone with access to the URL can use the app.
- **Gemini rate limits** — the free tier allows 20 requests per day. The app will return an error after this quota is exhausted.
- **503 Gemini errors** — during peak hours, Gemini occasionally returns 503 UNAVAILABLE. The backend retries up to 3 times but may still fail.
- **Skill synonym matching** — gap detection uses exact string matching. `node.js` and `nodejs` are treated as different skills.
- **Database dependency** — the app requires the Week 1 `jobs.db` to be populated and tagged. It will not work without it.
- **PDF extraction quality** — complex PDF layouts (columns, tables, images) may produce garbled text when extracted by pdf.js.
- **No persistent chat history** — refreshing the page clears all messages.

---

## Architecture Reflection

### Design Choices

The frontend and backend are separated into two independent microservices for a clear reason: their responsibilities are different. The frontend is a presentation layer (serving HTML, routing requests) while the backend is a computation layer (calling LLMs, querying databases, processing logic). Keeping them separate means either can be updated, scaled, or replaced without touching the other.

Each service has its own Dockerfile and dependency set. This means the frontend image only contains FastAPI and Jinja2, while the backend image carries the full Week 2 AI stack. Containerization ensures the app runs identically on any machine regardless of the developer's local Python setup.

Docker secrets are used for the API key instead of plain environment variables. This prevents accidental exposure in logs, `docker inspect` output, or committed `.env` files, which matters even in development.

### Trade-offs

The main trade-off was simplicity of deployment versus production robustness. Docker Compose makes the entire system start with one command, which is ideal for a program evaluation context. A production system would use Kubernetes or a managed container platform instead.

The decision to use Gemini free tier over a local LLM prioritizes output quality and lower hardware requirements, at the cost of rate limits and internet dependency. The `asyncio.gather` pattern in `find_skill_gaps.py` runs resume extraction and database fetching in parallel, reducing response time by roughly 40%.

The dashboard is served from the frontend container and queries the database directly, rather than adding a third service or going through the backend. This keeps the architecture simple while still demonstrating database-driven visualization.

### Improvements

Given more time, the following would be worthwhile:

- **Persistent chat history** using a database (PostgreSQL or SQLite) so conversations are not lost on refresh
- **Streaming responses** using FastAPI's `StreamingResponse` and server-sent events so the user sees the reply appear token by token
- **Semantic skill matching** using embeddings to handle synonyms and related skills rather than exact string matching
- **Cloud deployment** on Railway or Render so the app is accessible without running Docker locally
- **Authentication** so users can have personal sessions and saved results
- **Resume parser** supporting PDF and Word formats on the server side rather than relying on client-side pdf.js
