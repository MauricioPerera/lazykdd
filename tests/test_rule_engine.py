"""Oraculo congelado del motor de reglas declarativo (Contrato 17).

Autorado por el orquestador ANTES de la delegacion. El implementador de
scripts/rule_engine.py NO escribe ni modifica este archivo: es el oraculo
independiente (CCDD canonico). Formato: knowledge/rule-contract-spec.md.

Contrato del motor:
    evaluate(ruleset: dict, record: dict, refs: dict) -> list
devuelve una lista de violaciones legibles (vacia = valido), ordenada
deterministamente. Cada violacion es un string que empieza con "<field>: ...";
`<field>` puede ser punteado (anidado), p. ej. "beneficiary.account".

Semantica por familia (cada una produce a lo sumo una violacion por campo):
- required: campo ausente, None, o string vacio "" -> violacion.
- type: kind number|string|dict; number excluye bool; se evalua solo si el
  valor esta presente (la ausencia la cubre required).
- bounds: gt/min/max/integer; se evalua solo si el valor es number.
- enums: valor en el conjunto `values` (igualdad de valor, `in`) -> ok, si no violacion.
- refs: el valor del campo debe ser clave en refs[collection]; se evalua si esta presente.
- keyed_bounds: max = refs[table][record[key]][max_path]; si el valor (number) > max -> violacion.
- keyed_enums: allowed = refs[table][record[key]][values_path]; si el valor no esta -> violacion.
  Las familias keyed se saltan (sin violacion) si la clave no resuelve en la tabla.
- each (cuantificacion sobre colecciones): {collection, where?, rules} — evalua el subset
  interno v1 (required/type/enums/bounds, misma semantica de arriba) sobre CADA elemento
  dict de record[collection] (lista), filtrado por where {field, equals} si esta. Toda
  violacion se emite con el prefijo del nombre de la coleccion ("<collection>: elemento
  <i>...": el campo top-level ES la coleccion). Coleccion ausente o no-lista -> se salta;
  elemento no-dict -> una violacion de la coleccion nombrando el indice.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts")))

from rule_engine import evaluate


def _fields(violations):
    """Conjunto de campos TOP-LEVEL con violacion (punteado -> raiz)."""
    return {v.split(":", 1)[0].strip().split(".")[0] for v in violations}


def _run(ruleset, record, refs=None):
    return evaluate(ruleset, record, refs or {})


class TestRequired(unittest.TestCase):
    RS = {"required": [{"field": "a"}, {"field": "nested.x"}]}

    def test_ausente_none_vacio(self):
        for rec in ({}, {"a": None}, {"a": ""}):
            self.assertIn("a", _fields(_run(self.RS, rec)))

    def test_presente_no_vacio_ok(self):
        self.assertNotIn("a", _fields(_run(self.RS, {"a": "x", "nested": {"x": 1}})))

    def test_nested_ausente(self):
        self.assertIn("nested", _fields(_run(self.RS, {"a": "x", "nested": {}})))


class TestType(unittest.TestCase):
    RS = {"type": [{"field": "n", "kind": "number"},
                   {"field": "s", "kind": "string"},
                   {"field": "d", "kind": "dict"}]}

    def test_number_excluye_bool(self):
        self.assertIn("n", _fields(_run(self.RS, {"n": True, "s": "x", "d": {}})))
        self.assertNotIn("n", _fields(_run(self.RS, {"n": 5, "s": "x", "d": {}})))

    def test_number_rechaza_string(self):
        self.assertIn("n", _fields(_run(self.RS, {"n": "5", "s": "x", "d": {}})))

    def test_string_y_dict(self):
        v = _fields(_run(self.RS, {"n": 1, "s": 7, "d": []}))
        self.assertIn("s", v)
        self.assertIn("d", v)

    def test_ausente_no_dispara_type(self):
        # type no exige presencia (eso es required)
        self.assertEqual(_fields(_run(self.RS, {})), set())


class TestBounds(unittest.TestCase):
    RS = {"bounds": [{"field": "amount", "gt": 0}]}

    def test_gt(self):
        self.assertIn("amount", _fields(_run(self.RS, {"amount": 0})))
        self.assertIn("amount", _fields(_run(self.RS, {"amount": -1})))
        self.assertNotIn("amount", _fields(_run(self.RS, {"amount": 1})))

    def test_min_max_integer(self):
        rs = {"bounds": [{"field": "x", "min": 5, "max": 120, "integer": True}]}
        self.assertIn("x", _fields(_run(rs, {"x": 4})))
        self.assertIn("x", _fields(_run(rs, {"x": 121})))
        self.assertIn("x", _fields(_run(rs, {"x": 10.5})))
        self.assertNotIn("x", _fields(_run(rs, {"x": 10})))

    def test_no_numerico_no_dispara_bounds(self):
        # bounds solo aplica a numbers (el tipo lo cubre type)
        self.assertEqual(_fields(_run(self.RS, {"amount": "x"})), set())


class TestEnums(unittest.TestCase):
    RS = {"enums": [{"field": "d", "values": ["easy", "hard"]}]}

    def test_dentro_fuera(self):
        self.assertNotIn("d", _fields(_run(self.RS, {"d": "easy"})))
        self.assertIn("d", _fields(_run(self.RS, {"d": "medium"})))

    def test_values_true_por_igualdad(self):
        # Documenta la frontera: por igualdad de valor, 1 pertenece a [True] (1 == True).
        rs = {"enums": [{"field": "v", "values": [True]}]}
        self.assertNotIn("v", _fields(_run(rs, {"v": True})))
        self.assertIn("v", _fields(_run(rs, {"v": False})))
        self.assertNotIn("v", _fields(_run(rs, {"v": 1})))  # frontera: 1 == True


class TestRefs(unittest.TestCase):
    RS = {"refs": [{"field": "country", "collection": "limits"}]}
    REFS = {"limits": {"AR": {}, "BR": {}}}

    def test_clave_existente_inexistente(self):
        self.assertNotIn("country", _fields(_run(self.RS, {"country": "AR"}, self.REFS)))
        self.assertIn("country", _fields(_run(self.RS, {"country": "XX"}, self.REFS)))


class TestKeyed(unittest.TestCase):
    REFS = {"limits": {"AR": {"max_amount": 500000, "allowed_currencies": ["USD", "ARS"]}}}
    RS = {
        "keyed_bounds": [{"field": "amount", "key": "country", "table": "limits", "max_path": "max_amount"}],
        "keyed_enums": [{"field": "currency", "key": "country", "table": "limits", "values_path": "allowed_currencies"}],
    }

    def test_keyed_bounds(self):
        base = {"country": "AR", "currency": "USD"}
        self.assertNotIn("amount", _fields(_run(self.RS, dict(base, amount=500000), self.REFS)))
        self.assertIn("amount", _fields(_run(self.RS, dict(base, amount=500001), self.REFS)))

    def test_keyed_enums(self):
        base = {"country": "AR", "amount": 1000}
        self.assertNotIn("currency", _fields(_run(self.RS, dict(base, currency="ARS"), self.REFS)))
        self.assertIn("currency", _fields(_run(self.RS, dict(base, currency="EUR"), self.REFS)))

    def test_keyed_se_salta_si_la_clave_no_resuelve(self):
        # country XX no esta en limits -> keyed no dispara (lo cubre refs sobre country)
        rec = {"country": "XX", "amount": 999999999, "currency": "EUR"}
        self.assertEqual(_fields(_run(self.RS, rec, self.REFS)), set())


class TestEach(unittest.TestCase):
    RS = {"each": [
        {"collection": "nodes",
         "where": {"field": "type", "equals": "httpRequest"},
         "rules": {"required": [{"field": "parameters.timeout"}]}},
        {"collection": "nodes",
         "rules": {"enums": [{"field": "credentials_inline", "values": [False]}]}},
    ]}

    def test_where_filtra_por_tipo(self):
        rec = {"nodes": [
            {"type": "httpRequest", "parameters": {}, "credentials_inline": False},
            {"type": "code", "parameters": {}, "credentials_inline": False},
        ]}
        v = _run(self.RS, rec)
        # el httpRequest sin timeout viola; el code sin timeout NO (where filtra)
        self.assertEqual(len(v), 1, v)
        self.assertTrue(v[0].startswith("nodes"), v[0])
        self.assertIn("timeout", v[0])

    def test_regla_sin_where_aplica_a_todos(self):
        rec = {"nodes": [
            {"type": "code", "parameters": {}, "credentials_inline": True},
            {"type": "set", "parameters": {}, "credentials_inline": False},
        ]}
        v = _run(self.RS, rec)
        self.assertEqual(len(v), 1, v)
        self.assertTrue(v[0].startswith("nodes"), v[0])

    def test_valido_sin_violaciones(self):
        rec = {"nodes": [
            {"type": "httpRequest", "parameters": {"timeout": 30}, "credentials_inline": False},
            {"type": "code", "parameters": {}, "credentials_inline": False},
        ]}
        self.assertEqual(_run(self.RS, rec), [])

    def test_bounds_y_type_internos(self):
        rs = {"each": [{"collection": "items",
                        "rules": {"type": [{"field": "qty", "kind": "number"}],
                                  "bounds": [{"field": "qty", "gt": 0}]}}]}
        v = _run(rs, {"items": [{"qty": -1}, {"qty": "x"}, {"qty": 2}]})
        self.assertEqual(len(v), 2, v)
        for viol in v:
            self.assertTrue(viol.startswith("items"), viol)

    def test_coleccion_ausente_o_no_lista_se_salta(self):
        self.assertEqual(_run(self.RS, {}), [])
        self.assertEqual(_run(self.RS, {"nodes": "no-lista"}), [])
        self.assertEqual(_run(self.RS, {"nodes": {"a": 1}}), [])

    def test_elemento_no_dict_es_violacion_de_la_coleccion(self):
        v = _run(self.RS, {"nodes": [5]})
        self.assertEqual(len(v), 1, v)
        self.assertTrue(v[0].startswith("nodes"), v[0])


class TestDeterminismoYOrden(unittest.TestCase):
    def test_orden_estable_y_lista(self):
        rs = {"required": [{"field": "b"}, {"field": "a"}]}
        r1 = _run(rs, {})
        r2 = _run(rs, {})
        self.assertIsInstance(r1, list)
        self.assertEqual(r1, r2)
        # ordenado por campo: 'a' antes que 'b'
        campos = [v.split(":", 1)[0].strip() for v in r1]
        self.assertEqual(campos, sorted(campos))

    def test_nunca_lanza_con_record_raro(self):
        rs = {"required": [{"field": "a"}], "type": [{"field": "a", "kind": "dict"}],
              "bounds": [{"field": "a", "gt": 0}]}
        for rec in ({"a": object()}, {"a": [1, 2]}, {}):
            out = _run(rs, rec)
            self.assertIsInstance(out, list)


if __name__ == "__main__":
    unittest.main()
