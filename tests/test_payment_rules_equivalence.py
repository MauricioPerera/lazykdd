"""Prueba de equivalencia del Contrato 17 (experimento falsable).

Sobre cada caso del golden set congelado, corre DOS validadores independientes:
  1. el codigo (src/payment_limit.py, C16), y
  2. el motor declarativo (scripts/rule_engine.py sobre el rule-set de datos),
y exige que ambos reproduzcan el ground-truth del golden, salvo las reglas
marcadas `code_only` (que el declarativo no alcanza, por diseño y documentado).

Es el corazon de C17: mide hasta donde las reglas de compliance caben como DATOS.
El golden fue verificado contra el codigo de C16 al autorarse (ground-truth solido).
"""

import json
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

RULES = os.path.join(ROOT, "examples", "rules", "payment-compliance.rules.json")
GOLDEN = os.path.join(ROOT, "examples", "rules", "payment-golden.json")


def _top_fields(violations):
    return {v.split(":", 1)[0].strip().split(".")[0] for v in violations}


@unittest.skipUnless(
    os.path.isfile(RULES) and os.path.isfile(GOLDEN)
    and os.path.isfile(os.path.join(ROOT, "src", "payment_limit.py")),
    "ejemplo de reglas removido por init")
class TestPaymentRulesEquivalence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from payment_limit import validate_payment_limit
        from rule_engine import evaluate
        cls.code = staticmethod(validate_payment_limit)
        cls.evaluate = staticmethod(evaluate)
        with open(RULES, encoding="utf-8") as fh:
            cls.ruleset = json.load(fh)
        with open(GOLDEN, encoding="utf-8") as fh:
            g = json.load(fh)
        cls.refs = g["refs"]
        cls.cases = g["cases"]

    def test_codigo_reproduce_el_golden(self):
        # Cross-check: el validador de codigo (C16) coincide con el ground-truth.
        for c in self.cases:
            got = _top_fields(self.code(c["record"], self.refs["limits"]))
            self.assertEqual(got, set(c["violations"]), c["name"])

    def test_declarativo_igual_al_codigo_salvo_code_only(self):
        # El motor declarativo reproduce el golden MENOS los campos code_only_miss.
        for c in self.cases:
            decl = _top_fields(self.evaluate(self.ruleset, c["record"], self.refs))
            expected = set(c["violations"]) - set(c["code_only_miss"])
            self.assertEqual(decl, expected, c["name"])

    def test_la_frontera_esta_documentada(self):
        # Toda regla code_only del rule-set tiene razon documentada.
        for co in self.ruleset.get("code_only", []):
            self.assertTrue(co.get("reason"), co)
        # Y hay al menos un caso del golden que ejercita la frontera.
        self.assertTrue(any(c["code_only_miss"] for c in self.cases),
                        "ningun caso ejercita la frontera code_only")


if __name__ == "__main__":
    unittest.main()
