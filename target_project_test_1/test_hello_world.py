import unittest
from hello_world import main

class TestHelloWorld(unittest.TestCase):
    def test_output(self):
        self.assertEqual(main(), 'Hello World')

if __name__ == '__main__':
    unittest.main()