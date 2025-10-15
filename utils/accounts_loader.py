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



logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("spider")



# Get the directory where this script is located
# __file__ == current_dir_path
# resolve == automaticaly resolve path issue
# parent.parent == outside 2 dirs current

BAISE_DIR = Path(__file__).resolve().parent.parent

# Adjust this path according to your actual project structure
ACCOUNTS_DIR = BAISE_DIR / "config/indeed_account"

async def load_accounts():
    """
    Load all Indeed account configurations stored as JSON files.

    Expected Folder Structure:
        project_root/
        ├── config/
        │   └── indeed_account/
        │       ├── account1.json
        │       ├── account2.json
        │       └── ...

    Returns:
        list: A list of account dictionaries loaded from JSON files.
    """
    
    # Validate that the folder exists
    if not ACCOUNTS_DIR.exists():
        logger.critical(f"❌ Directory not found: {ACCOUNTS_DIR}")
        return []

    accounts = []

    # Iterate through all .json files in the directory
    try:
        for file in ACCOUNTS_DIR.glob("*.json"):
            try:
                # Read and parse each JSON file
                with open(file, "r") as f:
                    account_data = json.load(f)
                    accounts.append(account_data)
                    logger.info(f"✔ Loaded account file: {file.name}")

            except json.JSONDecodeError as e:
                logger.warning(f"⚠️ Invalid JSON format in {file.name}: {e}")
            except Exception as e:
                logger.warning(f"⚠️ Error reading file {file.name}: {e}")

        # Log the final count of loaded accounts
        logger.info(f"✅ Successfully loaded {len(accounts)} Indeed account(s).")
        print(len(accounts))
        return accounts

    except Exception as e:
        logger.critical(f"❌ Unexpected error while loading accounts:\n{e}")
        return []


# ---------------------------- #
# Entry Point
# ---------------------------- #
if __name__ == "__main__":
    asyncio.run(load_accounts())
