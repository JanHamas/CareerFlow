# utils/logger_setup.py
import logging, os

def setup_logger(log_dir="logs", log_file="spider.log"):
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, log_file)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_path, mode="w", encoding="utf-8"),  # overwrite each run
            logging.StreamHandler()  # also print to console
        ]
    )
    return logging.getLogger("spider")
