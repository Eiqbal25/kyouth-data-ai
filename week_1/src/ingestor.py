import email
import quopri
import logging
from pathlib import Path


def ingest_all_mhtml(input_dir, output_dir):
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)

    print("🥉 Bronze: Ingesting MHTML files...")

    if not input_dir.exists():
        logging.warning(f"Input directory does not exist: {input_dir}")
        print("\n📊 Bronze Summary:")
        print("Total: 0 | Extracted: 0 | Failed: 0")
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    mhtml_files = list(input_dir.glob("*.mhtml"))

    if not mhtml_files:
        logging.warning(f"No MHTML files found in: {input_dir}")
        print("\n📊 Bronze Summary:")
        print("Total: 0 | Extracted: 0 | Failed: 0")
        return

    total = len(mhtml_files)
    extracted = 0
    failed = 0

    for mhtml_file in mhtml_files:
        try:
            with open(mhtml_file, "rb") as f:
                msg = email.message_from_bytes(f.read())

            html_content = None

            for part in msg.walk():
                if part.get_content_type() == "text/html":
                    payload = part.get_payload()
                    encoding = part.get("Content-Transfer-Encoding", "").lower()

                    if encoding == "quoted-printable":
                        html_content = quopri.decodestring(payload.encode()).decode(
                            "utf-8", errors="replace"
                        )
                    else:
                        html_content = payload
                    break

            if not html_content:
                logging.warning(f"No HTML content found in: {mhtml_file.name}")
                failed += 1
                continue

            output_file = output_dir / (mhtml_file.stem + ".html")
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(html_content)

            logging.info(f"✅ Extracted: {mhtml_file.name}")
            extracted += 1

        except Exception as e:
            logging.error(f"Failed to extract {mhtml_file.name} | Reason: {e}")
            failed += 1

    print("\n📊 Bronze Summary:")
    print(f"Total: {total} | Extracted: {extracted} | Failed: {failed}")
