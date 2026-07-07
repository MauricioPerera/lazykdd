"""Stub del oraculo de versioning-plantilla (Contrato 14).

Sellado por el orquestador para que el task contract valide pre-delegacion;
el dev lo REEMPLAZA con la suite real de coherencia y re-sella tests_sha256
en knowledge/contracts/versioning-plantilla.md.
"""

import unittest


class TestStub(unittest.TestCase):
    def test_stub_pending_implementation(self):
        self.skipTest("stub: el dev de C14 reemplaza este archivo")


if __name__ == "__main__":
    unittest.main()
