import unittest
from unittest.mock import patch, MagicMock
import requests
from get_public_ip import get_external_ip, parse_ip

class TestGetPublicIP(unittest.TestCase):

    @patch('requests.get')
    def test_get_external_ip_success(self, mock_get):
        mock_response = mock_get.return_value
        mock_response.status_code = 200
        mock_response.json.return_value = {'ip': '123.45.67.89'}
        self.assertEqual(get_external_ip(), '123.45.67.89')

    @patch('requests.get')
    def test_get_external_ip_failure(self, mock_get):
        mock_get.side_effect = requests.RequestException('Simulated request failure')
        self.assertIsNone(get_external_ip())

    def test_parse_ip(self):
        data = {'ip': '123.45.67.89'}
        self.assertEqual(parse_ip(data), '123.45.67.89')

if __name__ == '__main__':
    unittest.main()