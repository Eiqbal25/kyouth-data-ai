import sqlite3
import re
import logging
from pathlib import Path

SUCCESS_ICON = "\u2705"

def load_sql(filename):
    """Load a .sql file from the project's queries/ folder."""
    path = Path(__file__).resolve().parent.parent / "queries" / filename
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def determine_quality(job_title, company, description):
    """LOW if missing key fields, too short, or too many special chars. Else HIGH."""
    if not job_title or not company or not description:
        return "LOW"

    if len(description) < 100:
        return "LOW"

    special_chars = len(re.findall(r"[^a-zA-Z0-9\s]", description))
    if len(description) > 0 and (special_chars / len(description)) > 0.3:
        return "LOW"

    return "HIGH"


def run_data_profile(db_path):
    db_path = Path(db_path)

    if not db_path.exists():
        print(f"❌ Database not found at {db_path}")
        return

    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()

    cursor.execute(load_sql("create_quarantine_table.sql"))
    connection.commit()

    # --- Quality labeling (runs first, no prints yet) ---
    cursor.execute(load_sql("select_all_jobs.sql"))
    rows = cursor.fetchall()

    update_quality_query = load_sql("update_quality.sql")

    high_count = 0
    low_count = 0

    for source_id, job_title, company, description in rows:
        quality = determine_quality(job_title, company, description)
        cursor.execute(update_quality_query, (quality, source_id))
        if quality == "LOW":
            logging.warning(f"Marked LOW quality: {source_id} | {job_title}")
            low_count += 1
        else:
            logging.info(f"{SUCCESS_ICON} Marked HIGH quality: {source_id} | {job_title}")
            high_count += 1

    connection.commit()

    cursor.execute(load_sql("move_to_quarantine.sql"))
    cursor.execute(load_sql("delete_low_quality.sql"))
    connection.commit()

    # --- Now print the report, last ---
    print()
    print("--- 🔍 DATA QUALITY REPORT ---")

    cursor.execute(load_sql("count_jobs.sql"))
    total_records = cursor.fetchone()[0]
    print(f"📈 Total Records: {total_records}")

    cursor.execute(load_sql("missing_values.sql"))
    missing_job_title, missing_company, missing_description = cursor.fetchone()
    print(
        f"❓ Missing Values -> job_title: {missing_job_title}, "
        f"company: {missing_company}, description: {missing_description}"
    )

    cursor.execute(load_sql("avg_description_length.sql"))
    avg_length = cursor.fetchone()[0]
    avg_length = round(avg_length) if avg_length is not None else 0
    print(f"📝 Avg Description Length: {avg_length} chars")

    cursor.execute(load_sql("shortest_description.sql"))
    shortest = cursor.fetchone()
    if shortest:
        source_id, job_title, length = shortest
        print(f"⚠️  Shortest Description: {length} chars")
        print(f"   ↳ source_id: {source_id} | job_title: {job_title}")

    cursor.execute(load_sql("longest_description.sql"))
    longest = cursor.fetchone()
    if longest:
        source_id, job_title, length = longest
        print(f"🚨 Longest Description: {length} chars")
        print(f"   ↳ source_id: {source_id} | job_title: {job_title}")

    print(f"\n📦 Quality Labeling -> HIGH: {high_count} | LOW: {low_count} (moved to jobs_quarantine)")

    connection.close()