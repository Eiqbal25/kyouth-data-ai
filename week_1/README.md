# Kyouth Data AI — Week 1 (Job Listings Pipeline)

## Project Description

This project is my Week 1 submission for the data engineering module. The goal was to build a small data pipeline that takes raw job listing web pages (saved as `.mhtml` files from Jobstreet) and turns them into clean, structured data stored in a database — ready to be used for analysis or AI tagging in future weeks.

I followed the **Medallion Architecture** pattern, which basically means organizing data into three "quality levels" as it moves through the pipeline:

- **Bronze** (`data/1_bronze/`) — the raw HTML, just unpacked from the original `.mhtml` files, nothing changed
- **Silver** (`data/2_silver/`) — cleaned up data, with only the important fields (job title, company, description, etc.) saved as JSON
- **Gold** (`data/3_gold/jobs.db`) — the final database where everything lives, ready for querying

By the end, I have a SQLite database (`jobs.db`) containing 84 valid job listings, each labeled as `HIGH` or `LOW` quality, plus a small report showing stats about the data.

---

## Setup Instructions

### What you need before starting

- **Python 3.14** — I used `uv` to manage this, so you don't need to install Python separately
- **`uv`** — a Python package/environment manager (faster alternative to pip + venv)
- **Git** — to clone this repo

### Step-by-step setup

1. **Clone this repository**
   ```bash
   git clone https://github.com/Eiqbal25/kyouth-data-ai.git
   cd kyouth-data-ai/week1
   ```

2. **Install `uv`**

   On Windows (PowerShell):
   ```bash
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```
   For other operating systems, check the [official uv install guide](https://docs.astral.sh/uv/getting-started/installation/).

3. **Set up Python and the virtual environment**
   ```bash
   uv python install
   uv venv
   ```

4. **Activate the virtual environment**

   On Windows:
   ```bash
   .venv\Scripts\activate
   ```
   On macOS/Linux:
   ```bash
   source .venv/bin/activate
   ```

5. **Install the required packages**
   ```bash
   uv add bs4 ruff pydantic
   ```

   Here's what each one does:
   - `beautifulsoup4` (bs4) — helps read and clean up messy HTML
   - `pydantic` — checks that our data has the right fields before saving it
   - `ruff` — keeps the code formatted nicely

### About the input files

The 100 sample `.mhtml` job listing files should already be inside `data/0_source/`. If that folder is empty, that's where the raw files need to go before running the pipeline.

### Environment Variables

None needed for this part of the project — everything runs locally with no API keys.

---

## How to Run It

Everything is controlled through `main.py`. Make sure your virtual environment is activated first. The script uses paths relative to its own location, so you can run it from inside `week1/` or by pointing to its full path from anywhere.

### Available commands

| Command | What it does |
|---|---|
| `python main.py ingest` | Step 1 — unpacks the `.mhtml` files into plain HTML (Bronze) |
| `python main.py process` | Step 2 — cleans the HTML and pulls out job info into JSON (Silver) |
| `python main.py load` | Step 3 — saves the JSON data into the SQLite database (Gold) |
| `python main.py profile` | Step 4 — checks the database and prints a quality report |
| `python main.py all` | Runs all 4 steps above, one after another |
| `python main.py` (nothing after) | Shows you the list of available commands |

### The easiest way — just run everything

```bash
python main.py all
```

### What you should expect to see

It will print out progress for each step, something like this (shortened):

```
🥉 Bronze: Ingesting MHTML files...
ℹ️ Extracted: <job title>.mhtml
...
📊 Bronze Summary:
Total: 100 | Extracted: 100 | Failed: 0

🥈 Silver: Processing HTML files...
✅ Processed: <job title>.html
⚠️ Missing job_title in: <some file>.html
...
📊 Silver Summary:
Total: 100 | Processed: 84 | Skipped: 16

🥇 Gold: Loading JSON files...
✅ Inserted: <job title>
...
📊 Gold Summary:
Total: 84 | Inserted: 84 | Skipped: 0

📈 Total Records: 84
❓ Missing Values -> job_title: 0, company: 0, description: 0
📝 Avg Description Length: 2644 chars
⚠️  Shortest Description: 32 chars
   ↳ source_id: 91647393 | job_title: Software Engineer
🚨 Longest Description: 6781 chars
   ↳ source_id: 91731564 | job_title: Automation Engineer

--- 🔍 DATA QUALITY REPORT ---
📦 Quality Labeling -> HIGH: 83 | LOW: 1 (moved to jobs_quarantine)
```

A quick note on the numbers: out of 100 raw files, 16 had something missing (like a blank job title or description) so they were skipped — this is expected and matches what was given in the assignment. The remaining 84 made it all the way to the database, and 1 of those was flagged as "low quality" because its description was way too short (only 32 characters), so it got moved to a separate `jobs_quarantine` table instead of staying in the main `jobs` table.

### Re-running the pipeline (idempotency check)

If you run `python main.py load` a second time on the same data, every record already exists, so instead of inserting, you'll see:

```
⏭️ Skipped (duplicate): <job title>
...
📊 Gold Summary:
Total: 84 | Inserted: 0 | Skipped: 84
```

This shows the pipeline can be safely re-run without creating duplicate rows.

### Bonus features I added

- **Logging** — instead of just plain `print()`, I used Python's `logging` module with a custom formatter that shows timestamps and emoji indicators (✅ success, ⚠️ warning, ❌ error, ⏭️ skipped duplicate, ℹ️ info) instead of plain INFO/WARNING/ERROR text. This makes it easier to scan the output and spot problems at a glance.
- **Content hashing** — each record gets a "fingerprint" (a hash) based on its title, company, and description. If the same job listing is processed again but the content changed, the database updates it instead of just ignoring it.
- **SQL files** — instead of writing SQL queries directly inside the Python files, I put them in a `queries/` folder as `.sql` files and load them when needed. Keeps things tidier.
- **Quality labels** — every record gets checked and labeled `HIGH` or `LOW` quality. `LOW` ones get moved into a separate `jobs_quarantine` table so they don't mess up the main data.

---

## Technical Reflections

### Day 1: The Extractor (Medallion & Lakehouses)

**Question:** Why is it useful to keep the original raw HTML files instead of directly inserting processed data into the database? What problems become easier to debug or recover from?
- **Answer:** Keeping the raw HTML files (Bronze layer) is basically like keeping a backup of the original "evidence." If something goes wrong later, say my cleaning script has a bug and extracts the wrong job title, I can go back to the raw HTML and check exactly what the page looked like, instead of trying to guess what happened. It also means if I improve my cleaning code later, I don't need to go re-download or re-collect the original 100 files again, I can just re-run the pipeline on the Bronze files I already saved. Without this raw copy, any mistake during processing would be permanent and hard to fix.

### Day 2: Treatment Plant (ETL vs ELT & Scale)

**Question:** Why do cloud systems prefer loading raw data first before cleaning it (ELT)? What problems happen when processing files sequentially, and how does distributed processing help?
- **Answer:** Cloud platforms like Snowflake or BigQuery have basically unlimited storage and very powerful computers, so it makes more sense to just dump all the raw data in first (load), and then clean/transform it later using the warehouse's own power (transform), that's "ELT" instead of "ETL". This way, the raw data is always available if you need to redo the cleaning with different logic, similar to why I kept my raw HTML files. As for processing files one at a time, in my project I used a simple for loop to go through 100 files, which worked fine, but if there were 1 million files instead of 100, this would take forever because each file waits for the previous one to finish. Distributed processing tools like Apache Spark fix this by splitting the files across many computers/cores so they all get processed at the same time, instead of one by one.

### Day 3: The Blueprint & The Vault (Storage & Contracts)

**Question:** What should happen if an important field like `job_title` disappears? Why fail early instead of silently inserting `nulls` into DB? How does `INSERT OR IGNORE` help prevent duplicate records?
- **Answer:** If job_title (or any required field) is missing from a record, my pipeline doesn't save it to the database at all, it gets skipped and a warning is printed instead. I think this is important because if we let records with missing fields into the database (as null), it could cause problems later, like a dashboard showing "null" as a job title, or an AI tagging script crashing because it expected text but got nothing. By catching the problem early (right when we're cleaning the data), it's much easier to fix and we know exactly which file caused it. As for INSERT OR IGNORE, this is a SQLite trick where if I try to insert a record with a source_id (the unique ID) that's already in the table, instead of crashing with an error, it just quietly skips that insert. This means I can run my loader script multiple times on the same data and it won't create duplicate rows, it just ignores the ones that are already there.

### Day 4: The QA Inspector & Orchestrator (Orchestration & DAGs)

**Question:** What happens if `processor.py` crashes halfway? How are automated orchestration tools more reliable than manual retries with Python scripts?
- **Answer:** If processor.py crashes partway through (say it processed 50 out of 100 files and then crashed), the 50 JSON files it already created stay saved in data/2_silver/, they don't disappear. Because my script processes and saves each file one at a time independently, I can just run python main.py process again and it will redo all 100 files (overwriting the 50 that were already done with the same result, and processing the other 50 for the first time). The downside is that I have to notice the crash happened and manually re-run it. A tool like Apache Airflow would be more reliable because it automatically tracks which steps succeeded or failed, can automatically retry failed steps a certain number of times, sends alerts if something fails repeatedly, and keeps a history log of every run, so nobody has to sit there watching the terminal and re-typing commands when something breaks.

---

## Project Structure

```
week_1/
├── data/
│   ├── 0_source/          # original .mhtml files (input)
│   ├── 1_bronze/          # raw extracted HTML
│   ├── 2_silver/          # cleaned JSON files
│   └── 3_gold/
│       └── jobs.db          # final SQLite database
├── queries/                  # SQL query files
├── src/
│   ├── ingestor.py          # Day 1 — extracts mhtml -> html
│   ├── processor.py         # Day 2 — html -> json
│   ├── loader.py            # Day 3 — json -> database
│   └── profiler.py          # Day 4 — quality report
├── main.py                   # the command-line entry point
├── pyproject.toml            # project dependencies
├── uv.lock
├── .python-version
├── .gitignore
└── README.md                 # this file
```

---

## A Note From Me

This was my first time building a full data pipeline like this, including working with SQLite, BeautifulSoup for HTML parsing, and Pydantic for data validation. I also learned a lot about idempotency (making sure re-running the program doesn't break things or create duplicates) and got more comfortable with Git — branching, pull requests, merging, and stashing — through the separate Git Workshop exercise. Thanks for reading through, and let me know if anything is unclear!
