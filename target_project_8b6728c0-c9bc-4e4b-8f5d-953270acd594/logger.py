import logging

class Logger:
    def __init__(self):
        logging.basicConfig(level=logging.INFO)

    def log_status_code(self, status_code):
        if status_code:
            logging.info(f"Status Code: {status_code}")
