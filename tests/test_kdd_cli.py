"""Oraculo congelado del CLI de KDD (Contrato: kdd-contracts-list-json).

Fija el comportamiento de ``scripts/kdd_cli.py`` -- la Piel 2 (CLI Python)
del proyecto lazykdd. Cubre DOS subcomandos despachados por UNA sola
funcion:

    main(argv, stdout, run_all_fn=None, list_contracts_fn=None) -> int

Reglas del contrato (nombres congelados):
- ``argv`` es la lista de argumentos SIN el nombre del programa.
- ``argv == ['gates', 'run-all', '--json']``:
  - ``fn = run_all_fn if run_all_fn is not None else
    mcp_gate_dispatch.run_all_level1`` (import como modulo hermano).
  - ``result = fn(repo_root='.')``.
  - escribe ``json.dumps(result)`` (una sola linea, sin pretty-print) en
    ``stdout`` via ``.write(...)``.
  - devuelve ``0`` si ``result['overall_ok']`` es ``True``, si no ``1``.
  - ``fn`` (run_all_fn) NUNCA se llama si ``argv`` no matchea exactamente.
- ``argv == ['contracts', 'list', '--json']``:
  - ``fn = list_contracts_fn if list_contracts_fn is not None else
    list_contracts_json`` (default del mismo modulo).
  - ``result = fn(contracts_dir='knowledge/contracts')``.
  - si ``result`` es una lista (incluida vacia): escribe
    ``json.dumps(result)`` (una sola linea, sin pretty-print), devuelve
    ``0``. Una lista vacia es exito, NO error.
  - si ``result`` es un dict con clave ``'error'``: escribe
    ``json.dumps(result)``, devuelve ``1``.
  - ``list_contracts_fn`` NUNCA se llama si ``argv`` no matchea exactamente.
- cualquier otro ``argv`` (vacio, --help, desconocido, subset/superset,
  orden roto, flag extra): escribe un mensaje de uso de UNA linea que
  empieza con ``usage:`` y menciona AMBOS subcomandos (``gates run-all
  --json`` y ``contracts list --json``) en ``stdout``, devuelve ``2``.
  NINGUN ``fn`` se llama. Nunca lanza una excepcion no controlada por un
  ``argv`` malformado.

Los tests NUNCA invocan subprocess real ni tocan red: siempre inyectan un
``run_all_fn``/``list_contracts_fn`` fake (lambda que devuelve un literal)
para los casos validos; el caso ``None`` se ejercita monkeypatcheando el
modulo (``mcp_gate_dispatch`` / ``kdd_cli``) con un fake -- tampoco corre
los gates reales ni lee el filesystem real del repo dentro de un test.
"""

import io
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import mcp_gate_dispatch  # noqa: E402
import kdd_cli  # noqa: E402
from kdd_cli import main  # noqa: E402

_JSON_OK = {"overall_ok": True, "results": {}}
_JSON_BAD = {"overall_ok": False, "results": {"x": {"exit_code": 1}}}
_LIST_ERR = {"error": "contracts dir not found: knowledge/contracts"}
_ONE = [{"task": "a", "title": "A", "intent": "do a", "target": "a.py"}]
_TWO = [
    {"task": "a", "title": "A", "intent": "do a", "target": "a.py"},
    {"task": "b", "title": "B", "intent": "do b", "target": "b.py"},
]


def _list_fn(payload):
    """Construye un list_contracts_fn fake que ignora su argumento."""
    return lambda contracts_dir="knowledge/contracts": payload


class TestGatesRunAllJson(unittest.TestCase):
    """Caso valido: ``['gates', 'run-all', '--json']`` con fn inyectado."""

    def test_overall_ok_true_returns_0(self):
        out = io.StringIO()
        rc = main(["gates", "run-all", "--json"], out,
                  run_all_fn=lambda repo_root=".": _JSON_OK)
        self.assertEqual(rc, 0)

    def test_overall_ok_true_writes_exact_json(self):
        out = io.StringIO()
        main(["gates", "run-all", "--json"], out,
             run_all_fn=lambda repo_root=".": _JSON_OK)
        self.assertEqual(json.loads(out.getvalue()), _JSON_OK)

    def test_output_is_single_line_no_pretty_print(self):
        out = io.StringIO()
        main(["gates", "run-all", "--json"], out,
             run_all_fn=lambda repo_root=".": _JSON_OK)
        self.assertNotIn("\n", out.getvalue())

    def test_overall_ok_false_returns_1(self):
        out = io.StringIO()
        rc = main(["gates", "run-all", "--json"], out,
                  run_all_fn=lambda repo_root=".": _JSON_BAD)
        self.assertEqual(rc, 1)

    def test_overall_ok_false_writes_json(self):
        out = io.StringIO()
        main(["gates", "run-all", "--json"], out,
             run_all_fn=lambda repo_root=".": _JSON_BAD)
        self.assertFalse(json.loads(out.getvalue())["overall_ok"])

    def test_fn_called_with_default_repo_root(self):
        calls = []

        def fake(repo_root="."):
            calls.append(repo_root)
            return _JSON_OK

        out = io.StringIO()
        main(["gates", "run-all", "--json"], out, run_all_fn=fake)
        self.assertEqual(calls, ["."])

    def test_fn_result_round_trips_as_json(self):
        out = io.StringIO()
        payload = {"overall_ok": True, "results": {"g": {"exit_code": 0,
                                   "stdout": "x", "stderr": ""}}}
        main(["gates", "run-all", "--json"], out,
             run_all_fn=lambda repo_root=".": payload)
        self.assertEqual(json.loads(out.getvalue()), payload)


class TestDefaultRunAllFn(unittest.TestCase):
    """``run_all_fn=None`` resuelve a ``mcp_gate_dispatch.run_all_level1``."""

    def test_none_fn_uses_module_dispatch(self):
        original = mcp_gate_dispatch.run_all_level1

        def fake(repo_root="."):
            return _JSON_OK

        mcp_gate_dispatch.run_all_level1 = fake
        try:
            out = io.StringIO()
            rc = main(["gates", "run-all", "--json"], out, run_all_fn=None)
            self.assertEqual(rc, 0)
            self.assertEqual(json.loads(out.getvalue()), _JSON_OK)
        finally:
            mcp_gate_dispatch.run_all_level1 = original


class TestContractsListJson(unittest.TestCase):
    """Caso valido: ``['contracts', 'list', '--json']`` con fn inyectado."""

    def test_list_returns_0(self):
        out = io.StringIO()
        rc = main(["contracts", "list", "--json"], out,
                  list_contracts_fn=_list_fn([]))
        self.assertEqual(rc, 0)

    def test_list_empty_writes_empty_list_json(self):
        out = io.StringIO()
        main(["contracts", "list", "--json"], out,
             list_contracts_fn=_list_fn([]))
        self.assertEqual(json.loads(out.getvalue()), [])

    def test_list_empty_writes_literal_brackets(self):
        out = io.StringIO()
        main(["contracts", "list", "--json"], out,
             list_contracts_fn=_list_fn([]))
        self.assertEqual(out.getvalue(), "[]")

    def test_list_empty_is_success_not_error(self):
        out = io.StringIO()
        rc = main(["contracts", "list", "--json"], out,
                  list_contracts_fn=_list_fn([]))
        self.assertEqual(rc, 0)

    def test_list_writes_json_array(self):
        out = io.StringIO()
        main(["contracts", "list", "--json"], out,
             list_contracts_fn=_list_fn(_ONE))
        self.assertEqual(json.loads(out.getvalue()), _ONE)

    def test_list_single_line_no_pretty_print(self):
        out = io.StringIO()
        main(["contracts", "list", "--json"], out,
             list_contracts_fn=_list_fn(_TWO))
        self.assertNotIn("\n", out.getvalue())

    def test_list_fn_called_with_default_contracts_dir(self):
        calls = []

        def fake(contracts_dir="knowledge/contracts"):
            calls.append(contracts_dir)
            return []

        out = io.StringIO()
        main(["contracts", "list", "--json"], out, list_contracts_fn=fake)
        self.assertEqual(calls, ["knowledge/contracts"])

    def test_list_two_items_round_trips(self):
        out = io.StringIO()
        main(["contracts", "list", "--json"], out,
             list_contracts_fn=_list_fn(_TWO))
        self.assertEqual(json.loads(out.getvalue()), _TWO)

    def test_list_error_dict_returns_1(self):
        out = io.StringIO()
        rc = main(["contracts", "list", "--json"], out,
                  list_contracts_fn=_list_fn(_LIST_ERR))
        self.assertEqual(rc, 1)

    def test_list_error_dict_writes_json(self):
        out = io.StringIO()
        main(["contracts", "list", "--json"], out,
             list_contracts_fn=_list_fn(_LIST_ERR))
        self.assertEqual(json.loads(out.getvalue()), _LIST_ERR)

    def test_list_error_dict_not_swallowed_as_list(self):
        out = io.StringIO()
        rc = main(["contracts", "list", "--json"], out,
                  list_contracts_fn=_list_fn(_LIST_ERR))
        self.assertNotEqual(rc, 0)


class TestDefaultListFn(unittest.TestCase):
    """``list_contracts_fn=None`` resuelve a ``kdd_cli.list_contracts_json``."""

    def test_none_fn_uses_module_list_contracts_json(self):
        original = kdd_cli.list_contracts_json

        def fake(contracts_dir="knowledge/contracts"):
            return _ONE

        kdd_cli.list_contracts_json = fake
        try:
            out = io.StringIO()
            rc = main(["contracts", "list", "--json"], out,
                      list_contracts_fn=None)
            self.assertEqual(rc, 0)
            self.assertEqual(json.loads(out.getvalue()), _ONE)
        finally:
            kdd_cli.list_contracts_json = original


class TestInvalidArgv(unittest.TestCase):
    """Cualquier otro ``argv`` -> mensaje de uso (``usage:``) + exit 2.

    El mensaje debe mencionar AMBOS subcomandos disponibles.
    """

    def _assert_usage(self, argv, run_all_fn=None, list_contracts_fn=None):
        out = io.StringIO()
        rc = main(argv, out, run_all_fn=run_all_fn,
                  list_contracts_fn=list_contracts_fn)
        self.assertEqual(rc, 2, msg="argv={!r}".format(argv))
        msg = out.getvalue()
        self.assertTrue(msg.startswith("usage:"),
                        msg="argv={!r} -> {!r}".format(argv, msg))
        self.assertIn("gates run-all --json", msg,
                      msg="argv={!r} -> {!r}".format(argv, msg))
        self.assertIn("contracts list --json", msg,
                      msg="argv={!r} -> {!r}".format(argv, msg))

    def test_empty(self):
        self._assert_usage([])

    def test_help(self):
        self._assert_usage(["--help"])

    def test_help_short(self):
        self._assert_usage(["-h"])

    def test_unknown_command(self):
        self._assert_usage(["frobnicate"])

    def test_subset_one_word(self):
        self._assert_usage(["gates"])

    def test_subset_two_words(self):
        self._assert_usage(["gates", "run-all"])

    def test_missing_json_flag(self):
        self._assert_usage(["gates", "run-all"])

    def test_wrong_flag(self):
        self._assert_usage(["gates", "run-all", "--yaml"])

    def test_superset_extra_arg(self):
        self._assert_usage(["gates", "run-all", "--json", "extra"])

    def test_superset_extra_flag(self):
        self._assert_usage(["gates", "run-all", "--json", "--verbose"])

    def test_wrong_order(self):
        self._assert_usage(["run-all", "gates", "--json"])

    def test_trailing_space_does_not_match(self):
        self._assert_usage(["gates ", "run-all", "--json"])

    def test_empty_string_element(self):
        self._assert_usage([""])

    def test_weird_string_element(self):
        self._assert_usage(["\x00", "weird"])

    def test_contracts_subset_one_word(self):
        self._assert_usage(["contracts"])

    def test_contracts_subset_two_words(self):
        self._assert_usage(["contracts", "list"])

    def test_contracts_missing_json_flag(self):
        self._assert_usage(["contracts", "list"])

    def test_contracts_wrong_flag(self):
        self._assert_usage(["contracts", "list", "--yaml"])

    def test_contracts_superset_extra_arg(self):
        self._assert_usage(["contracts", "list", "--json", "extra"])

    def test_contracts_wrong_order(self):
        self._assert_usage(["list", "contracts", "--json"])

    def test_fn_never_called_on_invalid_argv(self):
        called = []

        def fake(repo_root="."):
            called.append(True)
            return _JSON_OK

        self._assert_usage([], run_all_fn=fake)
        self.assertEqual(called, [])

    def test_fn_never_called_on_superset(self):
        called = []

        def fake(repo_root="."):
            called.append(True)
            return _JSON_OK

        self._assert_usage(["gates", "run-all", "--json", "extra"],
                           run_all_fn=fake)
        self.assertEqual(called, [])

    def test_list_fn_never_called_on_invalid_argv(self):
        called = []

        def fake(contracts_dir="knowledge/contracts"):
            called.append(True)
            return []

        self._assert_usage([], list_contracts_fn=fake)
        self.assertEqual(called, [])

    def test_neither_fn_called_on_invalid_argv(self):
        run_called = []
        list_called = []

        def rf(repo_root="."):
            run_called.append(True)
            return _JSON_OK

        def lf(contracts_dir="knowledge/contracts"):
            list_called.append(True)
            return []

        self._assert_usage(["frobnicate"], run_all_fn=rf,
                           list_contracts_fn=lf)
        self.assertEqual(run_called, [])
        self.assertEqual(list_called, [])


if __name__ == "__main__":
    unittest.main()