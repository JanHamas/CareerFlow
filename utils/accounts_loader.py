from pathlib import Path
import json, asyncio
import logging
logger = logging.getLogger("spider")  # use shared logger

# Get the accounts dir
BAISE_DIR = Path(__file__).resolve().parent
ACCOUNTS_DIR = BAISE_DIR / "accounts"

async def load_accounts():
    accounts = []
    try:
        for account in ACCOUNTS_DIR.glob("*.json"):
            with open(account, "r") as f:
                account = json.load(f)   
                accounts.append(account)         
        logger.info(f"✔ Sucessfully {len(accounts)} indeed accounts load")
        return accounts
    except Exception as e:
        logger.critical(f"❌ Error accounts loading: \n {e}")



if __name__ == "__main__":
    asyncio.run(load_accounts())

