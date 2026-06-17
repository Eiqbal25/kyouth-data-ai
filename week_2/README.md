# Week 2 — AI Component

## Project Overview

Builds the AI layer of a skill gap detection pipeline on top of the Week 1 database. Uses large language models to tag job listings with their required tech stacks, then compares them against a candidate resume to detect missing skills.

## Setup Instructions

### Prerequisites

- Python 3.14
- `uv` (package and environment manager)
- Ollama 0.21.* with the following models installed: `llama3.1`, `phi3`, `deepseek-r1:1.5b`
- A Google AI API key from https://aistudio.google.com

### Install dependencies

```bash
cd week_2
uv sync
```

### Environment variables

Create a `.env` file inside `week_2/`:

```
GOOGLE_API_KEY=your_google_ai_api_key_here
```

Do not commit this file. It is already listed in `.gitignore`.

### Ollama setup

Install Ollama 0.21.* from https://ollama.com, then pull the required models:

```bash
ollama pull llama3.1
ollama pull phi3
ollama pull deepseek-r1:1.5b
```

Verify Ollama is running:

```bash
curl 127.0.0.1:11434
```

Expected response: `Ollama is running`

## Usage

Run all commands from inside the `week_2/` folder.

### Test a model

```bash
uv run prompt_model.py llama3.1 "tell me a joke"
uv run prompt_model.py gemini-2.5-flash "tell me a joke"
```

Expected output:

```
--- RESPONSE ---

Here's a joke for you: ...
```

### Tag job listings with tech stacks

Place the jobs database at `data/jobs_d1.db`, then run:

```bash
uv run tag_data.py
uv run tag_data.py data/jobs_d1.db
```

Expected output:

```
Analyzed Job 91397216: SQL, Python, R, Excel, Tableau, PowerBI, DataStudio
Analyzed Job 91347112: Java, Spring Framework, Spring Boot, Python, ...
...
Total tokens used: 3239, took 5797.405ms
```

Running a second time on an already-tagged database:

```
No data to tag
Total tokens used: 0, took 16.676ms
```

### Detect skill gaps from a resume

Place the resume at `data/resume_d3.txt` and the tagged database at `data/jobs_d1.db`, then run:

```bash
uv run find_skill_gaps.py
uv run find_skill_gaps.py data/resume_d3.txt data/jobs_d1.db
```

Expected output:

```
gaps=['alibaba cloud', 'aws', 'ci/cd', 'docker', ...] tokens=228 time=1092.0
```

## API / Function Reference

### `prompt_model.py`

**`prompt_model(model: str, prompt: str) -> str`**

Routes a prompt to either a local Ollama model or a Google Gemini model based on the model name. Returns the text response as a string. All errors are caught and returned as error strings, no crashes.

- Gemini models: `gemini-2.5-flash`, `gemini-2.5-flash-lite`, `gemini-3-flash-preview`
- Ollama models: `llama3.1`, `phi3`, `deepseek-r1:1.5b`, or any other locally installed model

### `tag_data.py`

**`tag_data(db_url: str) -> tuple[int, float]`**

Reads all rows from the `jobs` table where `tech_stack` is NULL or empty, sends them in batches to Gemini for tech stack extraction, and writes the results back to the database.

- Model: `gemini-2.5-flash-lite`
- Batch size: 5 — justified by the 10 RPM rate limit; one API call per batch stays within the limit
- Retry wait: 60 seconds — resets the RPM window before retrying
- Max retries: 3 — prevents infinite loops on persistent errors
- Returns: `(total_tokens, elapsed_ms)`

### `find_skill_gaps.py`

**`find_skill_gaps(input_file_path: str, db_url: str) -> SkillGapResult`**

Reads a resume text file and a tagged jobs database, extracts skills from both, and returns the gaps: skills present in the job market but missing from the resume.

- Model: `gemini-2.5-flash-lite`
- `temperature=0` and `seed=42` are set for deterministic resume skill extraction
- Skills separated by `/` are split into individual skills, except `a/b testing` and `ci/cd`
- All gaps are sorted and lowercase
- Returns a `SkillGapResult` Pydantic model

**`SkillGapResult`** fields:

| Field | Type | Description |
|---|---|---|
| `gaps` | `List[str]` | Sorted lowercase list of missing skills |
| `tokens` | `int` | Total tokens used |
| `time` | `float` | Elapsed time in milliseconds |

## Data / Assumptions

- Input database must have a `jobs` table with columns: `source_id`, `description`, `tech_stack`
- Input resume must be a plain `.txt` file
- `tech_stack` is populated by `tag_data.py` as a comma-separated string
- Certifications and non-technical skills are excluded from skill gap results
- Jobs with empty descriptions will be skipped during tagging with a warning

### Data flow

```
resume.txt ──► [Gemini LLM] ──► resume skills (set)
                                          │
                                          ▼
jobs_d1.db ──► tech_stack column ──► db skills (set)
                                          │
                                          ▼
                              gaps = db_skills - resume_skills
```

## Testing

Determinism in `find_skill_gaps.py` verified by running twice consecutively and confirming identical output:

```
Run 1: gaps=['alibaba cloud', 'aws', 'ci/cd', ...] tokens=228 time=1092.0
Run 2: gaps=['alibaba cloud', 'aws', 'ci/cd', ...] tokens=228 time=1394.0
```

## Limitations

- Gemini free tier has a 20 RPD limit. Large databases will exhaust the daily quota quickly.
- Gemini may return 503 errors during high demand. The retry logic (3 attempts, 60s wait) mitigates this but does not guarantee recovery.
- Only plain text `.txt` resumes are supported. PDF resumes require pre-extraction.
- Skill matching is exact string matching after normalization. Synonyms like `node.js` vs `nodejs` are treated as different skills.
- Jobs with no extractable tech stack are skipped and left untagged.

## Architecture Reflection

### Design Choices

LLMs are used only where they add genuine value: extracting unstructured tech stacks from job descriptions and parsing resume skills from free-form text. All deterministic logic — skill normalization, set difference, sorting — is handled in pure Python without LLM involvement. This keeps the pipeline predictable and fast.

### Trade-offs

Using `temperature=0` and `seed=42` sacrifices some creative interpretation for consistency across runs, which is the right trade-off for a deterministic skill gap tool. Batching in `tag_data.py` balances throughput against rate limits, accepting that large databases take longer to process.

### Improvements

Given more time: semantic skill matching using embeddings to handle synonyms, PDF resume support, caching LLM responses to avoid re-tagging unchanged jobs, and an automated test suite with known inputs and expected outputs.
