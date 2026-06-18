# Kyouth Data AI — Week 1 & Week 2

## Project Overview

This repository contains two progressive data engineering projects built as part of the FX Digital Skills / kyouth program.

**Week 1** builds a data pipeline that ingests raw job listing web pages (`.mhtml` files from Jobstreet) and processes them through a Medallion Architecture (Bronze, Silver, Gold) into a clean SQLite database.

**Week 2** builds an AI component on top of Week 1, using large language models to tag job listings with their required tech stacks and detect skill gaps between a candidate resume and the job market.

---

## Setup Instructions

### Prerequisites

- Python 3.14
- `uv` (package and environment manager)
- Git
- Ollama 0.21.* (for local LLM models)
- A Google AI API key (for Gemini models)

### Install uv

On Windows (PowerShell):

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

For other operating systems, refer to the [official uv install guide](https://docs.astral.sh/uv/getting-started/installation/).

### Clone the repository

```bash
git clone https://github.com/Eiqbal25/kyouth-data-ai.git
cd kyouth-data-ai
```

### Week 1 setup

```bash
cd week_1
uv sync
```

### Week 2 setup

```bash
cd week_2
uv sync
```

### Environment variables (Week 2)

Create a `.env` file inside `week_2/`:

```
GOOGLE_API_KEY=your_google_ai_api_key_here
```

Do not commit this file. It is already listed in `.gitignore`.

### Ollama setup (Week 2)

Install Ollama 0.21.* from https://ollama.com, then pull the required models:

```bash
ollama pull llama3.1
ollama pull phi3
ollama pull deepseek-r1:1.5b
```

Start the Ollama server before running any local model commands:

```bash
ollama serve
```

---

## Usage

### Week 1

Run from inside the `week_1/` folder:

```bash
uv run main.py all
```

Available commands:

| Command | Description |
|---|---|
| `uv run main.py ingest` | Extract `.mhtml` files to Bronze layer |
| `uv run main.py process` | Clean HTML to Silver layer JSON |
| `uv run main.py load` | Load JSON into SQLite Gold database |
| `uv run main.py profile` | Run data quality report |
| `uv run main.py all` | Run all steps in sequence |

Place `.mhtml` source files in `week_1/data/0_source/` before running.

### Week 2

Run from inside the `week_2/` folder.

**Test a model:**

```bash
uv run prompt_model.py llama3.1 "tell me a joke"
uv run prompt_model.py gemini-2.5-flash "tell me a joke"
```

**Tag job listings with tech stacks:**

```bash
uv run tag_data.py
uv run tag_data.py data/jobs_d1.db
```

**Detect skill gaps from a resume:**

```bash
uv run find_skill_gaps.py
uv run find_skill_gaps.py data/resume_d3.txt data/jobs_d1.db
```

Expected output example:

```
gaps=['aws', 'docker', 'java', ...] top_missing_skills=['aws', 'docker', 'gcp', 'git', 'postgresql'] tokens=343 time=5291.0
```

---

## API / Function Reference

### Week 2: `prompt_model.py`

**`prompt_model(model: str, prompt: str) -> str`**

Routes a prompt to either a local Ollama model or a Google Gemini model based on the model name. Returns the text response as a string. Errors are caught and returned as strings, no crashes.

- Gemini models: `gemini-2.5-flash`, `gemini-2.5-flash-lite`, `gemini-3-flash-preview`
- Ollama models: `llama3.1`, `phi3`, `deepseek-r1:1.5b`, or any other locally installed model

### Week 2: `tag_data.py`

**`tag_data(db_url: str) -> tuple[int, float]`**

Reads all rows from the `jobs` table where `tech_stack` is NULL or empty, sends them in batches to Gemini for tech stack extraction, and writes the results back via MCP.

- Model: `gemini-2.5-flash-lite`
- Batch size: 5 (justified by 10 RPM rate limit on `gemini-2.5-flash-lite`)
- Retry wait: 60 seconds per retry, up to 3 attempts per batch
- Database access: via MCP server (`db_server.py`)
- Returns: total tokens used and elapsed time in milliseconds
- Also prints a tagging quality report showing match %, duplicate skills, and top repeated skills

### Week 2: `find_skill_gaps.py`

**`find_skill_gaps(input_file_path: str, db_url: str) -> SkillGapResult`**

Reads a resume text file and a tagged jobs database, then returns the skill gaps: skills demanded by the job market that are not present in the resume.

- Model: `gemini-2.5-flash-lite`
- Uses Gemini with `temperature=0` and `seed=42` for deterministic resume skill extraction
- Resume is sanitized against prompt injection before being sent to the LLM
- Splits skills on `/` except for `A/B testing` and `CI/CD`
- All output is sorted and lowercase
- Database access: via MCP server (`db_server.py`)

**`SkillGapResult`** (Pydantic model):

| Field | Type | Description |
|---|---|---|
| `gaps` | `List[str]` | Sorted lowercase list of missing skills |
| `top_missing_skills` | `List[str]` | Top 5 most in-demand missing skills by job count |
| `tokens` | `int` | Total tokens used |
| `time` | `float` | Elapsed time in milliseconds |

### Week 2: `db_server.py`

MCP server that abstracts all SQLite database access. Exposes four tools:

| Tool | Description |
|---|---|
| `read_jobs` | Returns untagged jobs (or all jobs if `include_tagged=True`) |
| `update_tech_stack` | Updates the `tech_stack` column for a specific job |
| `get_all_tech_stacks` | Returns all non-empty tech stacks |
| `get_job_count` | Returns total and tagged job counts |

---

## Data / Assumptions

### Week 1

- Input: `.mhtml` files from Jobstreet saved locally in `data/0_source/`
- Output: SQLite database at `data/3_gold/jobs.db` with a `jobs` table and a `jobs_quarantine` table for low quality records
- Schema: `source_id`, `job_title`, `company`, `description`, `quality_label`, `content_hash`
- Assumptions: source files are valid Jobstreet `.mhtml` exports; records missing `job_title`, `company`, or `description` are skipped

### Week 2

- Input database: `data/jobs_d1.db` (provided) or `jobs.db` from Week 1
- Input resume: plain text file (`.txt`)
- The `jobs` table must have columns: `source_id`, `description`, `tech_stack`
- `tech_stack` values are comma-separated strings written by `tag_data.py`
- Jobs with no extractable tech stack receive the placeholder `no tech stack extracted` and are excluded from skill gap analysis
- Certifications and non-technical skills are intentionally excluded from skill gap results

### Data flow

```
resume.txt --> [sanitize] --> [Gemini LLM] --> resume skills (set)
                                                        |
                                                        v
jobs_d1.db --> [MCP server] --> tech_stack column --> DB skills (set)
                                                        |
                                                        v
                                            gaps = DB skills - resume skills
                                            (sorted, lowercase)
```

---

## Testing

### Week 1

- Pipeline tested end-to-end with 100 `.mhtml` source files
- 84 valid records loaded into `jobs.db`; 16 skipped due to missing fields
- 1 record flagged as LOW quality and moved to `jobs_quarantine`
- Idempotency verified: running `uv run main.py all` multiple times produces the same database state

### Week 2

**`prompt_model.py`**: tested manually with all 5 supported models. Error handling verified by testing with an unavailable model — returns `[Gemini Error]` or `[Ollama Error]` prefix without crashing.

**`tag_data.py`**: tested on `jobs_d1.db` (8 rows). 6 rows successfully tagged, 2 rows with empty descriptions received placeholder. Quality report verified after each run.

**`find_skill_gaps.py`**: determinism verified by running twice consecutively and confirming identical output:

```
Run 1: gaps=['alibaba cloud', 'api integration', 'aws', ...] tokens=343 time=5291.0
Run 2: gaps=['alibaba cloud', 'api integration', 'aws', ...] tokens=343 time=5600.0
```

Eval accuracy verified: tested against evaluator-provided `jobs_d3_eval.db` and `resume_d3_eval.txt`. Output matches `d3_truth.json` exactly — 100% correct gaps, nothing missing, nothing extra.

**Jailbreak safety**: tested with a malicious resume containing prompt injection (`IGNORE ALL PREVIOUS INSTRUCTIONS...`). The `sanitize_resume()` function redacted the injection and the hardened prompt ensured only legitimate skills were extracted.

**Prompt optimization**: baseline prompt used 453 tokens across 3 runs. Optimized prompt reduced this to 343 tokens — a 24.3% reduction — with identical output.

---

## Limitations

- **API rate limits**: Gemini free tier allows only 20 requests per day per model. Running `tag_data.py` on large databases will exhaust the daily quota quickly.
- **503 errors**: Gemini models occasionally return 503 UNAVAILABLE during high demand. The retry logic (3 attempts, 60s wait) mitigates this but does not guarantee recovery.
- **Tagging accuracy**: LLM-generated tech stacks may vary in granularity. Some job descriptions are too vague for meaningful extraction.
- **Skill matching**: Gap detection uses exact string matching after normalization. Synonyms like `node.js` vs `nodejs` are treated as different skills.
- **Resume parsing**: Only plain text `.txt` resumes are supported. PDF or Word formats are not handled.
- **Local models**: Ollama models require sufficient RAM (8GB minimum) and storage (10GB minimum). First load may be slow.

---

## Architecture Reflection

### Design Choices

Both weeks follow a modular design where each function has a single responsibility. In Week 1, the pipeline is split into four independent stages (ingest, process, load, profile) so each can be run and debugged independently. In Week 2, the three scripts (`prompt_model.py`, `tag_data.py`, `find_skill_gaps.py`) are kept separate so they can be developed, tested, and reused independently.

LLMs are used only where they add genuine value: extracting unstructured tech stacks from job descriptions and parsing resume skills from free-form text. All deterministic logic (skill normalization, set difference, sorting) is handled in pure Python. Database access is abstracted through an MCP server (`db_server.py`), decoupling storage from business logic.

### Trade-offs

The main trade-off in Week 2 is accuracy vs determinism. Using `temperature=0` and `seed=42` ensures consistent resume parsing across runs at the cost of some flexibility. Batch processing in `tag_data.py` balances API rate limits against throughput, using a batch size derived directly from the RPM limit. The optimized prompt trades verbosity for token efficiency without sacrificing output quality.

### Improvements

Given more time, the following improvements would be valuable:

- Semantic skill matching using embeddings to handle synonyms like `node.js` vs `nodejs`
- PDF and Word resume format support
- Caching LLM responses to avoid re-tagging unchanged job descriptions
- Automated test suite with assertions rather than manual verification
- Parallel batch processing with proper rate limit tracking to speed up large database tagging
