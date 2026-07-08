"""Oraculo congelado del gate de perimetro (Contrato 28).

Fija el comportamiento de ``scripts/validate_perimeter.py`` — la herramienta
del PM que convierte el "Tocar SOLO" en verificacion de maquina: dado un task
contract (clave ``touch_only``) y la lista de archivos cambiados por el dev,
falla si algo cayo fuera del perimetro.

  API: ``def validate_perimeter(contract_path, changed_files) -> list`` con
  findings ``{'file','level','rule','msg'}`` ordenados por (file, rule, msg);
  ``file`` es la ruta posix del contrato; el archivo ofensor va en el msg.

  Semantica:
    - ``touch_only`` es la lista de patrones del contrato; matching ``fnmatch``
      sobre rutas repo-relativas estilo posix (un ``*`` cruza ``/``).
    - Los paths cambiados se normalizan antes de comparar: backslashes a ``/``
      y prefijo ``./`` removido. Lineas vacias se ignoran.
    - Lista de cambiados vacia -> sin findings (nada cambiado = dentro).

  Reglas (ERROR):
    FM_PARSE            contrato ilegible o frontmatter no parseable; las
                        demas reglas se omiten.
    TOUCH_ONLY_MISSING  el contrato no tiene ``touch_only`` valida (ausente,
                        no-lista, vacia o con items no-string/vacios): sin
                        perimetro declarado no se puede juzgar.
    TESTS_TOUCHED       un archivo cambiado ES el ``tests`` del contrato (el
                        oraculo congelado) y ``tests != target``; ese archivo
                        NO emite ademas OUT_OF_PERIMETER (una violacion, la
                        mas especifica). Si ``tests == target`` la regla no
                        aplica (el entregable es un test).
    OUT_OF_PERIMETER    un archivo cambiado no matchea ningun patron de
                        ``touch_only``; un finding por archivo, msg lo nombra.

  CLI: ``python scripts/validate_perimeter.py <contract.md> [--changed f1 ...]``
  — sin ``--changed`` lee los paths de stdin (uno por linea; el caller corre
  ``git diff --name-only`` y lo pipea). Imprime findings y
  ``Resumen: N error(es), M archivo(s) cambiados`` (M = cambiados tras
  normalizar, lo ESCANEADO). exit 0 sin ERRORs, 1 con >=1.

Este archivo es un ORACULO CONGELADO (tests_sha256): el implementador no lo
modifica. Ver knowledge/contracts/perimeter-gate.md.
"""

import contextlib
import io
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import validate_perimeter as vp  # noqa: E402


CONTRACT_TPL = """---
type: 'Task Contract'
task: demo
target: {target}
tests: "{tests}"
touch_only: {touch_only}
---

# Contract: demo
"""


class _Fixture(unittest.TestCase):
    def setUp(self):
        self.base = tempfile.mkdtemp(prefix="c28_")
        self.addCleanup(shutil.rmtree, self.base, ignore_errors=True)

    def _contract(self, touch_only="['src/hello.py']",
                  target="src/hello.py", tests="tests/test_sample.py",
                  raw=None):
        p = os.path.join(self.base, "demo.md")
        text = raw if raw is not None else CONTRACT_TPL.format(
            target=target, tests=tests, touch_only=touch_only)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(text)
        return p

    def _errors(self, findings):
        return [f for f in findings if f["level"] == "ERROR"]


class TestDentro(_Fixture):
    def test_cambios_dentro_del_perimetro(self):
        c = self._contract()
        self.assertEqual(vp.validate_perimeter(c, ["src/hello.py"]), [])

    def test_glob_cruza_directorios(self):
        c = self._contract(touch_only="['scripts/*']")
        self.assertEqual(
            vp.validate_perimeter(c, ["scripts/validate_x.py",
                                      "scripts/sub/dir/y.py"]), [])

    def test_lista_vacia_sin_findings(self):
        c = self._contract()
        self.assertEqual(vp.validate_perimeter(c, []), [])

    def test_normalizacion_de_paths(self):
        c = self._contract()
        self.assertEqual(
            vp.validate_perimeter(c, ["./src/hello.py", "src\\hello.py",
                                      "", "  "]), [])


class TestFuera(_Fixture):
    def test_fuera_del_perimetro_nombra_el_archivo(self):
        c = self._contract()
        findings = vp.validate_perimeter(c, ["src/hello.py", "README.md"])
        errs = self._errors(findings)
        self.assertEqual(len(errs), 1, errs)
        self.assertEqual(errs[0]["rule"], "OUT_OF_PERIMETER")
        self.assertIn("README.md", errs[0]["msg"])

    def test_un_finding_por_archivo_ordenados(self):
        c = self._contract()
        findings = vp.validate_perimeter(
            c, ["zeta.py", "alfa.py", "src/hello.py"])
        errs = self._errors(findings)
        self.assertEqual(len(errs), 2, errs)
        self.assertIn("alfa.py", errs[0]["msg"])
        self.assertIn("zeta.py", errs[1]["msg"])
        for f in findings:
            self.assertEqual(sorted(f.keys()),
                             ["file", "level", "msg", "rule"])
        keys = [(f["file"], f["rule"], f["msg"]) for f in findings]
        self.assertEqual(keys, sorted(keys))


class TestOraculoProtegido(_Fixture):
    def test_tocar_el_oraculo_es_tests_touched(self):
        c = self._contract()
        findings = vp.validate_perimeter(
            c, ["src/hello.py", "tests/test_sample.py"])
        errs = self._errors(findings)
        self.assertEqual([e["rule"] for e in errs], ["TESTS_TOUCHED"])
        self.assertIn("tests/test_sample.py", errs[0]["msg"])

    def test_tests_igual_a_target_no_dispara(self):
        c = self._contract(target="tests/test_sample.py",
                           tests="tests/test_sample.py",
                           touch_only="['tests/test_sample.py']")
        self.assertEqual(
            vp.validate_perimeter(c, ["tests/test_sample.py"]), [])


class TestContratoInvalido(_Fixture):
    def test_sin_touch_only(self):
        c = self._contract(raw="---\ntask: demo\ntarget: src/x.py\n"
                               "tests: \"tests/t.py\"\n---\n\n# c\n")
        findings = vp.validate_perimeter(c, ["src/x.py"])
        self.assertEqual([f["rule"] for f in findings],
                         ["TOUCH_ONLY_MISSING"])

    def test_touch_only_malformada(self):
        for raro in ("touch_only: src/x.py", "touch_only: []",
                     "touch_only: ['src/x.py', '']"):
            c = self._contract(raw="---\ntask: demo\n" + raro + "\n---\n\n# c\n")
            findings = vp.validate_perimeter(c, ["src/x.py"])
            self.assertEqual([f["rule"] for f in findings],
                             ["TOUCH_ONLY_MISSING"], raro)

    def test_contrato_sin_frontmatter(self):
        c = self._contract(raw="# sin frontmatter\n")
        findings = vp.validate_perimeter(c, ["x.py"])
        self.assertEqual([f["rule"] for f in findings], ["FM_PARSE"])

    def test_contrato_inexistente(self):
        findings = vp.validate_perimeter(
            os.path.join(self.base, "no-existe.md"), ["x.py"])
        self.assertEqual([f["rule"] for f in findings], ["FM_PARSE"])


class TestCli(_Fixture):
    def test_changed_ok_exit_0_resumen(self):
        c = self._contract()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = vp.main([c, "--changed", "src/hello.py"])
        self.assertEqual(code, 0)
        self.assertIn("0 error(es), 1 archivo(s)", out.getvalue())

    def test_changed_fuera_exit_1(self):
        c = self._contract()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = vp.main([c, "--changed", "README.md"])
        self.assertEqual(code, 1)
        self.assertIn("OUT_OF_PERIMETER", out.getvalue())

    def test_stdin_mode(self):
        c = self._contract()
        out = io.StringIO()
        stdin = io.StringIO("src/hello.py\nREADME.md\n")
        with contextlib.redirect_stdout(out):
            old = sys.stdin
            sys.stdin = stdin
            try:
                code = vp.main([c])
            finally:
                sys.stdin = old
        self.assertEqual(code, 1)
        self.assertIn("2 archivo(s)", out.getvalue())

    def test_determinismo(self):
        c = self._contract()
        args = ["b.py", "a.py", "src/hello.py"]
        self.assertEqual(vp.validate_perimeter(c, args),
                         vp.validate_perimeter(c, args))


if __name__ == "__main__":
    unittest.main()
