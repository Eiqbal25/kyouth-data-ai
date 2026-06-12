import json
import re
import logging
from pathlib import Path

from bs4 import BeautifulSoup
from pydantic import BaseModel, field_validator, ValidationError


class JobListing(BaseModel):
    source_id: str
    job_title: str
    company: str
    description: str

    @field_validator("source_id", "job_title", "company", "description")
    @classmethod
    def not_empty(cls, value, info):
        if not value or not value.strip():
            raise ValueError(f"{info.field_name} is empty")
        return value


def process_all_html(input_dir, output_dir):
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)

    print("🥈 Silver: Processing HTML files...")

    if not input_dir.exists():
        logging.warning(f"Input directory does not exist: {input_dir}")
        print("\n📊 Silver Summary:")
        print("Total: 0 | Processed: 0 | Skipped: 0")
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    html_files = list(input_dir.glob("*.html"))

    if not html_files:
        logging.warning(f"No HTML files found in: {input_dir}")
        print("\n📊 Silver Summary:")
        print("Total: 0 | Processed: 0 | Skipped: 0")
        return

    total = len(html_files)
    processed = 0
    skipped = 0

    for html_file in html_files:
        try:
            with open(html_file, "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f.read(), "html.parser")

            source_id = None
            og_url_tag = soup.find("meta", property="og:url")
            if og_url_tag and og_url_tag.get("content"):
                url = og_url_tag["content"].rstrip("/")
                source_id = url.split("/")[-1]

            job_title = None
            title_tag = soup.find(attrs={"data-automation": "job-detail-title"})
            if title_tag:
                job_title = title_tag.get_text(separator=" ", strip=True)

            company = None
            company_tag = soup.find(attrs={"data-automation": "advertiser-name"})
            if company_tag:
                company = company_tag.get_text(separator=" ", strip=True)

            description = None
            desc_tag = soup.find(attrs={"data-automation": "jobAdDetails"})
            if desc_tag:
                description = desc_tag.get_text(separator=" ", strip=True)
                description = re.sub(r"\s+", " ", description).strip()

            try:
                job = JobListing(
                    source_id=source_id,
                    job_title=job_title,
                    company=company,
                    description=description,
                )
            except ValidationError as e:
                for err in e.errors():
                    field = err["loc"][0]
                    logging.warning(f"Missing {field} in: {html_file.name}")
                skipped += 1
                continue

            output_file = output_dir / f"{job.source_id}.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(job.model_dump(), f, ensure_ascii=False, indent=2)

            logging.info(f"Processed: {job.job_title}")
            processed += 1

        except Exception as e:
            logging.error(f"Failed to process {html_file.name} | Reason: {e}")
            skipped += 1

    print(f"\n📊 Silver Summary:")
    print(f"Total: {total} | Processed: {processed} | Skipped: {skipped}")