import unittest
import sys
import os

# Ajustar el path para importar src/hello.py
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from hello import hello

class TestSample(unittest.TestCase):
    def test_hello(self):
        self.assertEqual(hello("Mundo"), "Hello, Mundo")

if __name__ == '__main__':
    unittest.main()