import json
import sqlite3
import hashlib
import logging
from pathlib import Path

from src.db_utils import load_sql


def compute_content_hash(job_title, company, description):
    """Hash based on job_title, company, description.
    Normalizes whitespace and casing so minor formatting changes don't trigger false positives.
    """
    normalized = f"{job_title}|{company}|{description}".strip().lower()
    normalized = " ".join(normalized.split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def load_all_jsons(input_dir, output_dir):
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)

    print("🥇 Gold: Loading JSON files...")

    if not input_dir.exists():
        logging.warning(f"Input directory does not exist: {input_dir}")
        print("\n📊 Gold Summary:")
        print("Total: 0 | Inserted: 0 | Skipped: 0")
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    db_path = output_dir / "jobs.db"

    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()

    cursor.execute(load_sql("create_jobs_table.sql"))
    cursor.execute(load_sql("create_quarantine_table.sql"))
    connection.commit()

    json_files = list(input_dir.glob("*.json"))

    if not json_files:
        logging.warning(f"No JSON files found in: {input_dir}")
        print("\n📊 Gold Summary:")
        print("Total: 0 | Inserted: 0 | Skipped: 0")
        connection.close()
        return

    total = len(json_files)
    inserted = 0
    skipped = 0

    insert_query = load_sql("insert_job.sql")
    get_hash_query = load_sql("get_content_hash.sql")
    update_query = load_sql("update_job.sql")

    for json_file in json_files:
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            content_hash = compute_content_hash(
                data["job_title"], data["company"], data["description"]
            )

            cursor.execute(
                insert_query,
                (data["source_id"], data["job_title"], data["company"], data["description"], content_hash),
            )

            if cursor.rowcount == 1:
                connection.commit()
                logging.info(f"Inserted: {data['job_title']}")
                inserted += 1
                continue

            # Already exists -> check if content changed
            cursor.execute(get_hash_query, (data["source_id"],))
            row = cursor.fetchone()
            existing_hash = row[0] if row else None

            if existing_hash != content_hash:
                cursor.execute(
                    update_query,
                    (data["job_title"], data["company"], data["description"], content_hash, data["source_id"]),
                )
                connection.commit()
                logging.info(f"Updated (content changed): {data['job_title']}")
                inserted += 1  # counted as a successful write
            else:
                logging.info(f"Skipped (duplicate): {json_file.name}")
                skipped += 1

        except Exception as e:
            logging.error(f"Failed to load {json_file.name} | Reason: {e}")
            skipped += 1

    connection.close()

    print(f"\n📊 Gold Summary:")
    print(f"Total: {total} | Inserted: {inserted} | Skipped: {skipped}")