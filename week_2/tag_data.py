import os
import sqlite3
import sys
import time
from collections import Counter

from dotenv import load_dotenv
from google import genai

load_dotenv()

# Rate limit justification:
# gemini-2.5-flash-lite: 10 RPM, 20 RPD
# Batch size = 5 (one API call per batch, fits within 10 RPM)
# Retry wait = 60s (one minute, resets the RPM window)
# Max retries = 3 (avoid infinite loops on persistent errors)
MODEL = "gemini-2.5-flash-lite"
BATCH_SIZE = 5
RETRY_WAIT = 60
MAX_RETRIES = 3


def fetch_untagged_jobs(conn: sqlite3.Connection) -> list[tuple]:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT source_id, description FROM jobs WHERE tech_stack IS NULL OR tech_stack = ''"
    )
    return cursor.fetchall()


def fetch_all_tagged_jobs(conn: sqlite3.Connection) -> list[tuple]:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT source_id, tech_stack FROM jobs WHERE tech_stack IS NOT NULL AND tech_stack != ''"
    )
    return cursor.fetchall()


def fetch_total_jobs(conn: sqlite3.Connection) -> int:
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM jobs")
    return cursor.fetchone()[0]


def build_prompt(batch: list[tuple]) -> str:
    lines = []
    for source_id, description in batch:
        lines.append(f"JOB_ID: {source_id}\nDESCRIPTION: {description}")
    jobs_text = "\n\n".join(lines)
    return (
        "You are a technical recruiter. For each job below, extract only the technical stack "
        "(programming languages, frameworks, tools, platforms, and technical skills) "
        "as a comma-separated list. "
        "Respond ONLY in this exact format, one line per job, nothing else:\n"
        "JOB_ID: <id>, TECH_STACK: <comma separated tech stack>\n\n"
        f"{jobs_text}"
    )


def parse_response(response_text: str, batch: list[tuple]) -> dict[str, str]:
    results = {}
    for line in response_text.strip().splitlines():
        line = line.strip()
        if not line or "JOB_ID:" not in line or "TECH_STACK:" not in line:
            continue
        try:
            id_part, stack_part = line.split("TECH_STACK:")
            source_id = id_part.replace("JOB_ID:", "").replace(",", "").strip()
            tech_stack = stack_part.strip()
            results[source_id] = tech_stack
        except Exception:
            continue
    return results


def update_jobs(conn: sqlite3.Connection, results: dict[str, str]):
    cursor = conn.cursor()
    for source_id, tech_stack in results.items():
        if not tech_stack.strip():
            print(f"[Warning] No tech stack extracted for Job {source_id}, setting placeholder")
            tech_stack = "no tech stack extracted"
        cursor.execute(
            "UPDATE jobs SET tech_stack = ? WHERE source_id = ?",
            (tech_stack, source_id),
        )
        print(f"Analyzed Job {source_id}: {tech_stack}")
    conn.commit()


def measure_quality(conn: sqlite3.Connection, total_jobs: int):
    tagged = fetch_all_tagged_jobs(conn)
    tagged_count = len(tagged)

    # Direct match %: percentage of jobs that have a non-empty tech stack
    match_pct = (tagged_count / total_jobs * 100) if total_jobs > 0 else 0.0

    # Duplicate count: skills that appear in more than one job
    all_skills = []
    for _, tech_stack in tagged:
        skills = [s.strip().lower() for s in tech_stack.split(",") if s.strip()]
        all_skills.extend(skills)

    skill_counts = Counter(all_skills)
    duplicates = {skill: count for skill, count in skill_counts.items() if count > 1}

    print(f"\n--- Tagging Quality Report ---")
    print(f"Total jobs: {total_jobs}")
    print(f"Tagged jobs: {tagged_count}")
    print(f"Direct match %: {match_pct:.1f}%")
    print(f"Duplicate skills (appear in >1 job): {len(duplicates)}")
    if duplicates:
        top = sorted(duplicates.items(), key=lambda x: x[1], reverse=True)[:5]
        print(f"Top 5 most repeated skills:")
        for skill, count in top:
            print(f"  {skill}: {count} jobs")
    print(f"------------------------------\n")


def tag_data(db_url: str) -> tuple[int, float]:
    start_time = time.time()
    total_tokens = 0

    try:
        conn = sqlite3.connect(db_url)
    except Exception as e:
        print(f"[DB Error] Could not connect to database: {e}")
        return 0, 0.0

    try:
        total_jobs = fetch_total_jobs(conn)
        rows = fetch_untagged_jobs(conn)
    except Exception as e:
        print(f"[DB Error] Could not fetch jobs: {e}")
        conn.close()
        return 0, 0.0

    if not rows:
        print("No data to tag")
        measure_quality(conn, total_jobs)
        elapsed = (time.time() - start_time) * 1000
        print(f"Total tokens used: 0, took {elapsed:.3f}ms")
        conn.close()
        return 0, elapsed

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("[Config Error] GOOGLE_API_KEY not found in environment")
        conn.close()
        return 0, 0.0

    try:
        client = genai.Client(api_key=api_key)
    except Exception as e:
        print(f"[API Error] Could not initialize Gemini client: {e}")
        conn.close()
        return 0, 0.0

    batches = [rows[i : i + BATCH_SIZE] for i in range(0, len(rows), BATCH_SIZE)]

    for batch_index, batch in enumerate(batches):
        prompt = build_prompt(batch)
        success = False

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = client.models.generate_content(
                    model=MODEL,
                    contents=prompt,
                )
                response_text = response.text

                if response.usage_metadata:
                    total_tokens += response.usage_metadata.prompt_token_count or 0
                    total_tokens += response.usage_metadata.candidates_token_count or 0
                else:
                    word_count = len(prompt.split()) + len(response_text.split())
                    total_tokens += word_count * 4

                results = parse_response(response_text, batch)

                if len(results) != len(batch):
                    print(
                        f"[Batch {batch_index}] Attempt {attempt} failed: "
                        f"Mismatch between batch size and response"
                    )
                    if attempt < MAX_RETRIES:
                        time.sleep(RETRY_WAIT)
                    continue

                update_jobs(conn, results)
                success = True
                break

            except Exception as e:
                print(f"[Batch {batch_index}] Attempt {attempt} failed: {e}")
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_WAIT)

        if not success:
            print(
                f"[Batch {batch_index}] All {MAX_RETRIES} attempts failed, skipping batch"
            )

    measure_quality(conn, total_jobs)
    conn.close()
    elapsed = (time.time() - start_time) * 1000
    print(f"Total tokens used: {total_tokens}, took {elapsed:.3f}ms")
    return total_tokens, elapsed


def main():
    db_url = sys.argv[1] if len(sys.argv) > 1 else "data/jobs_d1.db"
    tag_data(db_url)


if __name__ == "__main__":
    main()