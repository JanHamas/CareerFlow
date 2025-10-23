import os, csv
import asyncio
import logging


# Logger
logger = logging.getLogger("spider")


# === 2. Append new job entries to corresponding CSVs ===
def _append_jobs(cs_applies, c_applies):
    def append_to_csv(file_name, rows):
        if not rows:
            return
        path = os.path.join("output", file_name)
        with open(path, mode="a", newline='', encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(rows)

    append_to_csv("CS_applies.csv", cs_applies)
    append_to_csv("Confirmation_applies.csv", c_applies)
    logger.info("✔ Saved in CSV files.")


# === 3. Async wrappe cs and confirmation applies ===
async def jobs_append_to_csv(cs_applies, c_applies):
    print(f"\nCS: {len(cs_applies)}, C: {len(c_applies)}")
    loop = asyncio.get_event_loop()
    try:
        await loop.run_in_executor(None, lambda: _append_jobs(cs_applies, c_applies))
    except Exception as e:
        logger.error(f"❌ Error saving to CSV: {e}")
