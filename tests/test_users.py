"""Tests congelados del contrato validate-user-record (Contrato 04, dogfood E2E).

Autorados por el orquestador ANTES de la delegación. El implementador de
src/users.py NO escribe ni modifica este archivo: es el oráculo independiente
(CCDD canónico). Reglas de dominio: knowledge/data_models/users_table.md.
"""

import os
import sys
import unittest

# Convención del repo (ver tests/test_sample.py): src/ al path, import plano.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from users import validate_user_record


def _valid_record(**overrides):
    rec = {
        "email": "ada@example.com",
        "username": "ada_lovelace",
        "password_hash": "x" * 60,
        "display_name": "Ada Lovelace",
    }
    rec.update(overrides)
    return rec


class TestRegistrosValidos(unittest.TestCase):
    def test_registro_completo_valido(self):
        self.assertEqual(validate_user_record(_valid_record()), [])

    def test_display_name_ausente_es_valido(self):
        rec = _valid_record()
        del rec["display_name"]
        self.assertEqual(validate_user_record(rec), [])

    def test_display_name_none_es_valido(self):
        self.assertEqual(validate_user_record(_valid_record(display_name=None)), [])

    def test_username_limites_del_patron(self):
        self.assertEqual(validate_user_record(_valid_record(username="abc")), [])
        self.assertEqual(validate_user_record(_valid_record(username="a" * 50)), [])
        self.assertEqual(validate_user_record(_valid_record(username="a_9")), [])


class TestCamposObligatorios(unittest.TestCase):
    def test_dict_vacio_reporta_los_tres_obligatorios(self):
        violaciones = validate_user_record({})
        self.assertEqual(len(violaciones), 3)
        texto = "\n".join(violaciones)
        for campo in ("email", "username", "password_hash"):
            self.assertIn(campo, texto, f"falta violación para {campo}")

    def test_obligatorio_no_string_es_violacion(self):
        violaciones = validate_user_record(_valid_record(email=42))
        self.assertEqual(len(violaciones), 1)
        self.assertIn("email", violaciones[0])


class TestUsername(unittest.TestCase):
    def _solo_username_invalido(self, valor):
        violaciones = validate_user_record(_valid_record(username=valor))
        self.assertEqual(len(violaciones), 1, f"username={valor!r}: {violaciones}")
        self.assertIn("username", violaciones[0])

    def test_corto(self):
        self._solo_username_invalido("ab")

    def test_largo(self):
        self._solo_username_invalido("a" * 51)

    def test_mayusculas(self):
        self._solo_username_invalido("Ada")

    def test_caracteres_fuera_del_charset(self):
        self._solo_username_invalido("ada-lovelace")
        self._solo_username_invalido("ada lovelace")


class TestEmail(unittest.TestCase):
    def _solo_email_invalido(self, valor):
        violaciones = validate_user_record(_valid_record(email=valor))
        self.assertEqual(len(violaciones), 1, f"email={valor!r}: {violaciones}")
        self.assertIn("email", violaciones[0])

    def test_sin_arroba(self):
        self._solo_email_invalido("ada.example.com")

    def test_dominio_sin_punto(self):
        self._solo_email_invalido("ada@example")

    def test_parte_local_vacia(self):
        self._solo_email_invalido("@example.com")

    def test_con_espacios(self):
        self._solo_email_invalido("ada lovelace@example.com")

    def test_tope_255(self):
        local = "a" * 250
        self._solo_email_invalido(local + "@ex.com")  # 257 chars


class TestPasswordHash(unittest.TestCase):
    def test_largo_distinto_de_60(self):
        for n in (59, 61):
            violaciones = validate_user_record(_valid_record(password_hash="x" * n))
            self.assertEqual(len(violaciones), 1, f"len={n}: {violaciones}")
            self.assertIn("password_hash", violaciones[0])


class TestDisplayName(unittest.TestCase):
    def test_tope_100(self):
        self.assertEqual(
            validate_user_record(_valid_record(display_name="d" * 100)), []
        )
        violaciones = validate_user_record(_valid_record(display_name="d" * 101))
        self.assertEqual(len(violaciones), 1)
        self.assertIn("display_name", violaciones[0])

    def test_no_string_es_violacion(self):
        violaciones = validate_user_record(_valid_record(display_name=7))
        self.assertEqual(len(violaciones), 1)
        self.assertIn("display_name", violaciones[0])


class TestAcumulacionYRobustez(unittest.TestCase):
    def test_acumula_todas_las_violaciones(self):
        violaciones = validate_user_record(
            _valid_record(username="AB", password_hash="corto")
        )
        self.assertEqual(len(violaciones), 2)

    def test_nunca_lanza_con_tipos_raros(self):
        raros = [
            {"email": 42, "username": None, "password_hash": ["x"]},
            {"email": b"bytes@x.com", "username": 3.14, "password_hash": {}},
        ]
        for rec in raros:
            resultado = validate_user_record(rec)  # no debe lanzar
            self.assertIsInstance(resultado, list)
            self.assertGreaterEqual(len(resultado), 3)


if __name__ == "__main__":
    unittest.main()
