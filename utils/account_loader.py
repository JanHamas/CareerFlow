"""
load_accounts.py
----------------
This script asynchronously loads all Indeed account JSON files
from a specific configuration folder and returns them as a list
of Python dictionaries.

Features:
- Safe and robust directory handling using pathlib
- Detailed logging for debugging and visibility
- Graceful handling of missing folders and invalid JSON files
"""

from pathlib import Path
import json
import asyncio
import logging

logger = logging.getLogger("spider")


# Get the directory where this script is located
# __file__ == current_dir_path
# resolve == automaticaly resolve path issue
# parent.parent == outside 2 dirs current


import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

async def load_account(account_dir: Path):
    """
    Load a single Indeed account configuration stored as a JSON file.

    Expected Folder Structure:
        project_root/
        ├── config/
        │   └── indeed_account/
        │       └── account1.json

    Args:
        account_dir (Path): Path to the directory containing the account JSON file.

    Returns:
        dict | None: Account data loaded from the JSON file, or None if not found/invalid.
    """

    # ✅ Validate that the folder exists
    if not account_dir.exists():
        logger.critical(f"❌ Directory not found: {account_dir}")
        return None

    try:
        # ✅ Find the first JSON file in the directory
        json_files = list(account_dir.glob("*.json"))
        if not json_files:
            logger.warning(f"⚠️ No JSON account file found in {account_dir}")
            return None

        account_file = json_files[0]  # load the first file only

        # ✅ Read and parse the JSON file
        with open(account_file, "r", encoding="utf-8") as f:
            account_data = json.load(f)
            logger.info(f"✅ Loaded account file: {account_file.name}")
            return account_data

    except json.JSONDecodeError as e:
        logger.warning(f"⚠️ Invalid JSON format in {account_file.name}: {e}")
    except Exception as e:
        logger.critical(f"❌ Unexpected error while loading account:\n{e}")

    return None

# ---------------------------- #
# Entry Point
# ---------------------------- #
if __name__ == "__main__":
    asyncio.run(load_account())
