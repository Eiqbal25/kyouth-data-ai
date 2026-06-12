import sys
import logging
from pathlib import Path
from src.ingestor import ingest_all_mhtml
from src.processor import process_all_html
from src.loader import load_all_jsons
from src.profiler import run_data_profile

class EmojiFormatter(logging.Formatter):
    EMOJIS = {
        "DEBUG": "🐛",
        "INFO": "ℹ️",
        "WARNING": "⚠️",
        "ERROR": "❌",
        "CRITICAL": "🔥",
    }

    def format(self, record):
        record.levelname = self.EMOJIS.get(record.levelname, record.levelname)
        return super().format(record)


handler = logging.StreamHandler()
handler.setFormatter(EmojiFormatter("%(asctime)s |%(levelname)s |%(message)s"))
logging.basicConfig(level=logging.INFO, handlers=[handler])


SOURCE_DIR = Path("data/0_source")
BRONZE_DIR = Path("data/1_bronze")
SILVER_DIR = Path("data/2_silver")
GOLD_DIR = Path("data/3_gold")
DB_NAME = "jobs.db"

def run_profiler():
    db_path = GOLD_DIR / DB_NAME
    run_data_profile(db_path)

def run_gold():
    load_all_jsons(SILVER_DIR, GOLD_DIR)

def run_silver():
    process_all_html(BRONZE_DIR, SILVER_DIR)

def run_bronze():
    ingest_all_mhtml(SOURCE_DIR, BRONZE_DIR)

def run_all():
    run_bronze()
    print()
    print()
    run_silver()
    print()
    print()
    run_gold()
    print()
    print()
    run_profiler()

commands = {
    "ingest": run_bronze,
    "process": run_silver,
    "load": run_gold,
    "profile": run_profiler,
    "all": run_all,
}

def main():
    if len(sys.argv) != 2 or sys.argv[1] not in commands:
        print("Usage: python main.py [ingest|process|load|profile|all]")
        return
    commands[sys.argv[1]]()

if __name__ == "__main__":
    main()