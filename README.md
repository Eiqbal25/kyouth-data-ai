# Kyouth Data AI — Weeks 1, 2 & 3

A three-week progressive data engineering and AI project built as part of the FX Digital Skills / kyouth program. Each week builds on the previous, culminating in a containerized full-stack chat application with AI-powered skill gap detection.

---

## Project Overview

This repository contains three interconnected projects:

**Week 1** builds a data pipeline that ingests raw Jobstreet job listing pages (`.mhtml` files) and processes them through a Medallion Architecture (Bronze, Silver, Gold) into a clean SQLite database.

**Week 2** builds an AI layer on top of Week 1, using Google Gemini to tag job listings with their required tech stacks and detect skill gaps between a candidate resume and the job market.

**Week 3** integrates Weeks 1 and 2 into a containerized full-stack chat application with a FastAPI frontend, FastAPI backend, Bootstrap UI, PDF upload support, and a Charts.js dashboard. Each service runs in its own Docker container orchestrated by Docker Compose.

---

## Repository Structure

```
kyouth-data-ai/
├── week_1/        # Medallion Architecture ETL pipeline
├── week_2/        # AI skill gap detection with Gemini
├── week_3/        # Full-stack containerized chat application
└── README.md
```

---

## Setup Instructions

### Prerequisites

- Python 3.14
- [uv](https://docs.astral.sh/uv/getting-started/installation/) (package manager)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (for Week 3)
- A Google Gemini API key (free tier at [https://aistudio.google.com](https://aistudio.google.com))
- Git

### Install uv

On Windows (PowerShell):

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

For other operating systems, see the [official uv install guide](https://docs.astral.sh/uv/getting-started/installation/).

### Clone the repository

```bash
git clone https://github.com/Eiqbal25/kyouth-data-ai.git
cd kyouth-data-ai
```

---

## Week 1 Setup and Usage

```bash
cd week_1
uv sync
```

Place `.mhtml` source files in `week_1/data/0_source/`, then run:

```bash
uv run python main.py all
```

Available commands:

| Command | Description |
|---|---|
| `uv run python main.py ingest` | Extract `.mhtml` files to Bronze layer |
| `uv run python main.py process` | Clean HTML to Silver layer JSON |
| `uv run python main.py load` | Load JSON into SQLite Gold database |
| `uv run python main.py profile` | Run data quality report |
| `uv run python main.py all` | Run all steps in sequence |

Output: `week_1/data/3_gold/jobs.db` with 83 valid job listings.

---

## Week 2 Setup and Usage

```bash
cd week_2
uv sync
```

Create `week_2/.env`:

```
GOOGLE_API_KEY=your_gemini_api_key_here
```

**Tag job listings with tech stacks:**

```bash
uv run python tag_data.py
uv run python tag_data.py ../week_1/data/3_gold/jobs.db
```

**Detect skill gaps from a resume:**

```bash
uv run python find_skill_gaps.py
uv run python find_skill_gaps.py data/resume.txt ../week_1/data/3_gold/jobs.db
```

**Test a model:**

```bash
uv run python prompt_model.py gemini-2.5-flash-lite "tell me a joke"
uv run python prompt_model.py llama3.1 "tell me a joke"
```

---

## Week 3 Setup and Usage

See [`week_3/README.md`](week_3/README.md) for the full setup and usage guide.

**Quick start:**

```bash
# 1. Create secrets directory and add your API key
mkdir week_3/secrets
echo "your_gemini_api_key_here" > week_3/secrets/google_api_key.txt

# 2. Copy and fill in env files
cp week_3/.env.example week_3/.env
# Edit week_3/.env and add your GOOGLE_API_KEY

# 3. Run with Docker Compose
cd week_3
docker compose up --build
```

Then open [http://localhost:8000](http://localhost:8000) in your browser.

---

## API / Function Reference

### Week 2: `prompt_model.py`

**`prompt_model(model: str, prompt: str) -> str`**

Routes a prompt to either a local Ollama model or a Google Gemini model based on the model name. Errors are caught and returned as strings.

- Gemini models: `gemini-2.5-flash`, `gemini-2.5-flash-lite`, `gemini-3-flash-preview`
- Ollama models: `llama3.1`, `phi3`, `deepseek-r1:1.5b`, or any locally installed model

### Week 2: `tag_data.py`

**`tag_data(db_url: str) -> tuple[int, float]`**

Reads untagged jobs from the database, sends them in batches of 5 to Gemini for tech stack extraction, and writes results back via MCP. Uses `gemini-2.5-flash-lite` with 60s retry waits (justified by the 10 RPM rate limit).

### Week 2: `find_skill_gaps.py`

**`find_skill_gaps(input_file_path: str, db_url: str) -> SkillGapResult`**

Reads a resume text file and compares the candidate's skills against the job market tech stacks using Gemini for extraction and MCP for database access. Returns a `SkillGapResult` with:

| Field | Type | Description |
|---|---|---|
| `gaps` | `List[str]` | Sorted lowercase list of missing skills |
| `top_missing_skills` | `List[str]` | Top 5 most in-demand missing skills |
| `tokens` | `int` | Total tokens used |
| `time` | `float` | Elapsed time in milliseconds |

### Week 2: `db_server.py`

MCP server that abstracts all SQLite access. Exposes four tools:

| Tool | Description |
|---|---|
| `read_jobs` | Returns untagged jobs (or all if `include_tagged=True`) |
| `update_tech_stack` | Updates the `tech_stack` column for a job |
| `get_all_tech_stacks` | Returns all non-empty tech stacks |
| `get_job_count` | Returns total and tagged job counts |

### Week 3: Backend `POST /chat`

**URL:** `http://localhost:8001/chat`

**Request:**
```json
{ "message": "I know Python and SQL", "pdf_text": "" }
```

**Response:**
```json
{ "reply": "I found 120 skill gaps...\n\nTop missing skills: aws, git, docker..." }
```

---

## Data / Assumptions

### Week 1

- Input: `.mhtml` files from Jobstreet in `week_1/data/0_source/`
- Output: SQLite database at `week_1/data/3_gold/jobs.db`
- Schema: `source_id`, `job_title`, `company`, `description`, `tech_stack`, `quality`, `content_hash`
- Records missing `job_title`, `company`, or `description` are skipped
- Records with descriptions under 50 characters are flagged as LOW quality and moved to `jobs_quarantine`

### Week 2

- Input database must have columns: `source_id`, `description`, `tech_stack`
- Resume input is plain text (`.txt` format)
- Skills are extracted using Gemini with `temperature=0` and `seed=42` for determinism
- Resumes are sanitized against prompt injection before being sent to the LLM
- Skills are split on `/` except for exceptions like `A/B testing` and `CI/CD`
- Jobs with no extractable tech stack receive the placeholder `no tech stack extracted` and are excluded from gap analysis

### Week 3

- PDF text is extracted entirely in the browser using pdf.js before being sent
- No PDF file is uploaded to the server
- User messages are treated as resume skill descriptions, not conversational queries
- No conversation history is maintained between messages
- The `jobs.db` database must be pre-populated and tech-stack tagged for meaningful results

### Data flow (Week 3)

```
User types message / uploads PDF
        |
        v
Browser (chat_page.html)
  - pdf.js extracts PDF text if uploaded
  - POST JSON to backend /chat
        |
        v
Backend (app.py) — port 8001
  - Writes resume text to temp file
  - Calls find_skill_gaps(tmp_path, db_path)
        |
        v
Week 2: find_skill_gaps.py
  - Gemini extracts resume skills
  - MCP reads tech stacks from jobs.db
  - Returns gaps = DB skills - resume skills
        |
        v
Backend returns JSON { "reply": "..." }
        |
        v
Browser renders reply as chat bubble
```

---

## Testing

### Week 1

- Pipeline tested end-to-end with 100 `.mhtml` source files
- 83 valid records loaded; 17 skipped due to missing fields
- 1 record flagged LOW quality and moved to `jobs_quarantine`
- Idempotency verified: running `main.py all` multiple times produces identical results

### Week 2

**`prompt_model.py`**: tested manually with all 5 supported models. Error handling verified by testing with an unavailable model name.

**`tag_data.py`**: tested on `jobs_d3_eval.db`. Quality report printed after each run. 100% of `jobs.db` records (83/83) successfully tagged after multiple runs.

**`find_skill_gaps.py`**: determinism verified by running twice and confirming identical output:
```
Run 1: gaps=[...] tokens=343 time=5291.0
Run 2: gaps=[...] tokens=343 time=5600.0
```
Eval accuracy: 100% match against evaluator-provided `d3_truth.json`.

**Prompt injection safety**: tested with a malicious resume containing `IGNORE ALL PREVIOUS INSTRUCTIONS`. The `sanitize_resume()` function redacted the injection successfully.

### Week 3

Test the backend directly:

```bash
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "I know Python, SQL, and pandas", "pdf_text": ""}'
```

Frontend test cases:

| Test | Expected result |
|---|---|
| Send text message | Bot replies with skill gaps |
| Upload PDF then send | PDF text extracted and sent |
| Empty message | No request sent |
| Dashboard page | Charts render with job data |
| Search bar | Results table appears |

---

## Limitations

### Week 1 & 2

- Gemini free tier: 20 requests per day per model. Large databases exhaust quota quickly.
- 503 UNAVAILABLE errors occur during Gemini peak hours. Retry logic (3 attempts, 60s wait) mitigates but does not guarantee recovery.
- Skill synonym matching uses exact strings. `node.js` and `nodejs` are treated as different skills.
- Only `.txt` resume format is supported in Week 2 standalone scripts.
- Local Ollama models require 8GB+ RAM and 10GB+ storage.

### Week 3

- No conversation memory across messages.
- No user authentication.
- Gemini rate limits apply to the chat endpoint.
- PDF extraction quality degrades with complex layouts (columns, tables, scanned images).
- No persistent chat history — refreshing clears all messages.

---

## Architecture Reflection

### Design Choices

All three weeks follow a modular design where each component has a single responsibility. Week 1 splits the pipeline into four independent stages so each can be run and debugged separately. Week 2 keeps the three scripts (`prompt_model.py`, `tag_data.py`, `find_skill_gaps.py`) separate so they can be reused independently. Week 3 separates the frontend and backend into distinct microservices because their responsibilities are different: one serves HTML and routes browser requests, the other runs AI computation.

Containerization with Docker ensures the app runs identically on any machine. Docker secrets are used for API keys instead of plain environment variables to prevent accidental exposure in logs or `docker inspect` output.

### Trade-offs

The main trade-off in Week 2 is accuracy versus determinism. Using `temperature=0` and `seed=42` ensures consistent resume parsing at the cost of some flexibility in skill recognition. Batch size 5 for `tag_data.py` was chosen directly from the RPM rate limit to maximize throughput without triggering errors.

In Week 3, Docker Compose was chosen over Kubernetes for simplicity. A single command starts the entire system, which is appropriate for a program evaluation context but would not scale to production load. Using Gemini free tier prioritizes output quality and zero hardware requirements over rate limit freedom.

### Improvements

- Semantic skill matching using embeddings to handle synonyms
- Streaming chat responses using server-sent events
- Persistent chat history stored in a database
- Cloud deployment (Railway, Render, or AWS ECS)
- User authentication and personal sessions
- Automated test suite with CI/CD pipeline
- Server-side PDF parsing supporting complex layouts
- Caching LLM responses to avoid re-tagging unchanged job descriptions

### Live Demo

- **Landing Page**: https://landing-production-bff4.up.railway.app/
- **Docker Hub**: https://hub.docker.com/r/eiqbal25/landing
