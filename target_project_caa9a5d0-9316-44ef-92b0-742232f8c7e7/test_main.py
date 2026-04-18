import unittest
from unittest.mock import patch, MagicMock
import main_module

class TestMainModule(unittest.TestCase):

    @patch('main_module.requests.get')
    def test_get_public_ip_success(self, mock_get):
        # Mock the response from requests.get
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'ip': '123.45.67.89'}
        mock_get.return_value = mock_response

        ip = main_module.get_public_ip()
        self.assertEqual(ip, '123.45.67.89')

    @patch('main_module.requests.get')
    def test_get_public_ip_failure(self, mock_get):
        # Mock a failed response from requests.get
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        with self.assertRaises(Exception):
            main_module.get_public_ip()

if __name__ == '__main__':
    unittest.main()