import os
import sqlite3

from fastmcp import FastMCP

mcp = FastMCP("SQLite-Service")

DB_PATH = os.getenv("DB_PATH", "data/jobs_d1.db")


@mcp.tool
def read_jobs(include_tagged: bool = False) -> list:
    """Read jobs from the jobs table. If include_tagged is False, only returns untagged jobs."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        if include_tagged:
            cursor.execute("SELECT source_id, description, tech_stack FROM jobs")
        else:
            cursor.execute(
                "SELECT source_id, description FROM jobs WHERE tech_stack IS NULL OR tech_stack = ''"
            )
        return cursor.fetchall()


@mcp.tool
def update_tech_stack(source_id: str, tech_stack: str) -> str:
    """Update the tech_stack column for a specific job."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE jobs SET tech_stack = ? WHERE source_id = ?",
            (tech_stack, source_id),
        )
        conn.commit()
        return f"Updated job {source_id}"


@mcp.tool
def get_all_tech_stacks() -> list:
    """Get all non-empty tech stacks from the jobs table."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT source_id, tech_stack FROM jobs WHERE tech_stack IS NOT NULL AND tech_stack != '' AND tech_stack != 'no tech stack extracted'"
        )
        return cursor.fetchall()


@mcp.tool
def get_job_count() -> dict:
    """Get total and tagged job counts."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM jobs")
        total = cursor.fetchone()[0]
        cursor.execute(
            "SELECT COUNT(*) FROM jobs WHERE tech_stack IS NOT NULL AND tech_stack != ''"
        )
        tagged = cursor.fetchone()[0]
        return {"total": total, "tagged": tagged}


if __name__ == "__main__":
    mcp.run()