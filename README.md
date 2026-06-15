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
```

Or with a custom database path:

```bash
uv run tag_data.py data/jobs_d1.db
```

**Detect skill gaps from a resume:**

```bash
uv run find_skill_gaps.py
```

Or with custom paths:

```bash
uv run find_skill_gaps.py data/resume_d3.txt data/jobs_d1.db
```

Expected output example:

```
gaps=['aws', 'docker', 'java', 'kubernetes', ...] tokens=228 time=3147.0
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

Reads all rows from the `jobs` table where `tech_stack` is NULL or empty, sends them in batches to Gemini for tech stack extraction, and writes the results back to the database.

- Batch size: 5 (justified by 5 RPM rate limit on `gemini-2.5-flash`)
- Retry wait: 60 seconds per retry, up to 3 attempts per batch
- Returns: total tokens used and elapsed time in milliseconds

### Week 2: `find_skill_gaps.py`

**`find_skill_gaps(input_file_path: str, db_url: str) -> SkillGapResult`**

Reads a resume text file and a tagged jobs database, then returns the skill gaps: skills demanded by the job market that are not present in the resume.

- Uses Gemini with `temperature=0` and `seed=42` for deterministic resume skill extraction
- Splits skills on `/` except for `A/B testing` and `CI/CD`
- All output is sorted and lowercase

**`SkillGapResult`** (Pydantic model):

| Field | Type | Description |
|---|---|---|
| `gaps` | `List[str]` | Sorted lowercase list of missing skills |
| `tokens` | `int` | Total tokens used |
| `time` | `float` | Elapsed time in milliseconds |

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
- Certifications and non-technical skills are intentionally excluded from skill gap results
- Job 91574477 in `jobs_d1.db` has an empty description and is correctly skipped

### Data flow

```
resume.txt --> [Gemini LLM] --> resume skills (set)
jobs_d1.db --> tech_stack column --> parsed DB skills (set)
DB skills - resume skills = gaps (sorted, lowercase)
```

---

## Testing

### Week 1

- Pipeline tested end-to-end with 100 `.mhtml` source files
- 84 valid records loaded into `jobs.db`; 16 skipped due to missing fields
- 1 record flagged as LOW quality and moved to `jobs_quarantine`
- Idempotency verified: running `uv run main.py all` multiple times produces the same database state

### Week 2

**`prompt_model.py`**: tested manually with all 5 supported models (llama3.1, phi3, deepseek-r1:1.5b, gemini-2.5-flash, gemini-2.5-flash-lite). Error handling verified by testing with an unavailable model.

**`tag_data.py`**: tested on `jobs_d1.db` (7 rows). All rows with non-empty descriptions were tagged. Empty description rows are skipped with a warning rather than writing blank values.

**`find_skill_gaps.py`**: determinism verified by running twice consecutively and confirming identical output:

```
Run 1: gaps=['a/b testing', 'ai', 'aws', ...] tokens=228 time=3516.0
Run 2: gaps=['a/b testing', 'ai', 'aws', ...] tokens=228 time=3147.0
```

---

## Limitations

- **API rate limits**: Gemini free tier allows only 20 requests per day. Running `tag_data.py` on large databases (84+ rows) will exhaust the daily quota quickly. Test with the small sample database first.
- **503 errors**: Gemini models occasionally return 503 UNAVAILABLE during high demand periods. The retry logic (3 attempts, 60s wait) mitigates this but does not guarantee success.
- **Tagging accuracy**: LLM-generated tech stacks may vary in granularity. Some job descriptions are too vague for meaningful extraction.
- **Skill matching**: Gap detection uses exact string matching after normalization. Synonyms (e.g. `node.js` vs `nodejs`) are treated as different skills.
- **Resume parsing**: Only plain text `.txt` resumes are supported. PDF or Word formats are not handled.
- **Local models**: Ollama models require sufficient RAM (8GB minimum) and storage (10GB minimum). First load may be slow.

---

## Architecture Reflection

### Design Choices

Both weeks follow a modular design where each function has a single responsibility. In Week 1, the pipeline is split into four independent stages (ingest, process, load, profile) so each can be run and debugged independently. In Week 2, the three scripts (`prompt_model.py`, `tag_data.py`, `find_skill_gaps.py`) are kept separate so they can be developed, tested, and reused independently.

LLMs are used only where they add genuine value: extracting unstructured tech stacks from job descriptions and parsing resume skills from free-form text. All deterministic logic (skill normalization, set difference, sorting) is handled in pure Python without LLM involvement.

### Trade-offs

The main trade-off in Week 2 is accuracy vs determinism. Using `temperature=0` and `seed=42` for Gemini ensures consistent resume parsing across runs, at the cost of some flexibility in how skills are expressed. Batch processing in `tag_data.py` balances API rate limits against throughput, using a batch size derived directly from the RPM limit.

SQL is run directly rather than through MCP for simplicity, since the database interactions are straightforward read/write operations that do not benefit from the additional abstraction layer in this context.

### Improvements

Given more time, the following improvements would be valuable:

- Implement semantic skill matching (e.g. using embeddings) to handle synonyms like `node.js` vs `nodejs`
- Add support for PDF and Word resume formats
- Cache LLM responses to avoid re-tagging unchanged job descriptions
- Add a proper test suite with automated assertions rather than manual verification
- Integrate MCP for database access to decouple the SQL layer from application logic
- Implement parallel batch processing with proper rate limit tracking to speed up large database tagging
