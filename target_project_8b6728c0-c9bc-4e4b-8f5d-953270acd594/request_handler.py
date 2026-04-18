import requests

class RequestHandler:
    def send_request(self, url):
        try:
            response = requests.get(url)
            return response.status_code
        except requests.exceptions.RequestException as e:
            print(f"Error occurred: {e}")
            return None
