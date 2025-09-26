import os
import logging

# Logger
logger = logging.getLogger("spider")

# get the current dir path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # go one level up from utils
CONFIG_DIR = os.path.join(BASE_DIR, "config")
PROXIES_FILE = os.path.join(CONFIG_DIR, "proxies.txt")

async def load_proxies():
    try:
        proxies = []
        with open(PROXIES_FILE, "r") as f:
            for proxy in f:
                parts = proxy.strip().split(":")
                if len(parts) == 4:
                    ip, port, user, pwd = parts
                    proxies.append({
                        "server": f"http://{ip}:{port}",
                        "username": user,
                        "password": pwd
                    })
        if not proxies:
            logger.info("🛑 Check proxeis file we got 0")
        return proxies
    except Exception as e:
        logger.critical(f"❌ Error to load proxies \n {e}")
    
