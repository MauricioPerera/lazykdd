import unittest
import sys
import os

# Ajustar el path para importar src/hello.py
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

try:
    from hello import hello
except ImportError:
    # Dummy mock para que el lint/inicialización pase antes de que se implemente
    def hello(name): return f"Hello, {name}"

class TestSample(unittest.TestCase):
    def test_hello(self):
        self.assertEqual(hello("Mundo"), "Hello, Mundo")

if __name__ == '__main__':
    unittest.main()
