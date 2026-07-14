"""Oraculo congelado del CLI de KDD (Contrato: kdd-gates-run-all-json).

Fija el comportamiento de ``scripts/kdd_cli.py`` -- la PRIMERA pieza de la
Piel 2 (CLI Python) del proyecto lazykdd. Cubre UNA sola funcion nueva:

    main(argv, stdout, run_all_fn=None) -> int

Reglas del contrato (nombres congelados):
- ``argv`` es la lista de argumentos SIN el nombre del programa.
- ``argv == ['gates', 'run-all', '--json']``:
  - ``fn = run_all_fn if run_all_fn is not None else
    mcp_gate_dispatch.run_all_level1`` (import como modulo hermano).
  - ``result = fn(repo_root='.')``.
  - escribe ``json.dumps(result)`` (una sola linea, sin pretty-print) en
    ``stdout`` via ``.write(...)``.
  - devuelve ``0`` si ``result['overall_ok']`` es ``True``, si no ``1``.
  - ``fn`` NUNCA se llama si ``argv`` no matchea exactamente ese patron.
- cualquier otro ``argv`` (vacio, --help, desconocido, subset/superset,
  orden roto, flag extra): escribe un mensaje de uso de UNA linea que
  empieza con ``usage:`` en ``stdout``, devuelve ``2``. Nunca lanza una
  excepcion no controlada por un ``argv`` malformado.

Los tests NUNCA invocan subprocess real ni tocan red: siempre inyectan un
``run_all_fn`` fake (lambda que devuelve un dict literal) para el caso
``--json``, y prueban el caso de ``argv`` invalido SIN pasar ``run_all_fn``
(o pasando uno del que se aserta que NUNCA se llama). El caso
``run_all_fn=None`` se ejercita monkeypatcheando ``mcp_gate_dispatch`` con
un fake -- tampoco corre los gates reales.
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
from kdd_cli import main  # noqa: E402

_JSON_OK = {"overall_ok": True, "results": {}}
_JSON_BAD = {"overall_ok": False, "results": {"x": {"exit_code": 1}}}


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


class TestDefaultFn(unittest.TestCase):
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


class TestInvalidArgv(unittest.TestCase):
    """Cualquier otro ``argv`` -> mensaje de uso (``usage:``) + exit 2."""

    def _assert_usage(self, argv, run_all_fn=None):
        out = io.StringIO()
        rc = main(argv, out, run_all_fn=run_all_fn)
        self.assertEqual(rc, 2, msg="argv={!r}".format(argv))
        self.assertTrue(out.getvalue().startswith("usage:"),
                        msg="argv={!r} -> {!r}".format(argv, out.getvalue()))

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


if __name__ == "__main__":
    unittest.main()