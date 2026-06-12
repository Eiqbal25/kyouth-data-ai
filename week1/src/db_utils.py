from pathlib import Path


def load_sql(filename):
    """Load a .sql file from the project's queries/ folder."""
    path = Path(__file__).resolve().parent.parent / "queries" / filename
    with open(path, "r", encoding="utf-8") as f:
        return f.read()