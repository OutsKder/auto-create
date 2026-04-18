from request_handler import RequestHandler
from logger import Logger
from config_manager import ConfigManager

class Main:
    def run(self):
        config_manager = ConfigManager()
        request_handler = RequestHandler()
        logger = Logger()

        url = config_manager.get_target_url()
        status_code = request_handler.send_request(url)
        logger.log_status_code(status_code)

if __name__ == "__main__":
    main = Main()
    main.run()
