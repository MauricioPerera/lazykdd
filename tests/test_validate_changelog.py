"""Oraculo congelado del gate de coherencia CHANGELOG<->reportes (Contrato 27).

Evidencia: incidente real del ciclo v1.2.0 — tres entradas del CHANGELOG se
perdieron por un str.replace que no matcheo y fallo en silencio. Este gate
convierte la regla operativa ("verificar con grep antes de commitear") en
maquina.

Fija el comportamiento de ``scripts/validate_changelog.py``:

  API: ``def validate_changelog(changelog_path, reports_dir) -> list`` con
  findings ``{'file','level','rule','msg'}`` ordenados por (file, rule, msg);
  rutas posix.

  Universo: reportes = archivos de ``reports_dir`` con patron EXACTO
  ``CONTRACT-<digitos>-REPORT.md`` (otros, p. ej. TEMPLATE-REPORT.md, se
  ignoran). Entradas = lineas del changelog que EMPIEZAN con
  ``**Contract <digitos>``. El NN se compara como string tal cual aparece
  (zero-padded en ambos lados en este repo).

  Reglas (todas ERROR, file = ruta del changelog salvo indicacion):
    ENTRY_MISSING   reporte CONTRACT-NN-REPORT.md sin entrada **Contract NN;
                    el msg nombra NN y el archivo del reporte.
    REPORT_MISSING  entrada **Contract NN sin reporte en disco; msg nombra NN.
    LINK_MISSING    entrada **Contract NN cuya linea NO contiene el link
                    ``(docs/reports/CONTRACT-NN-REPORT.md)``; msg nombra NN.
    ENTRY_DUP       mas de una entrada para el mismo NN; un finding por
                    ocurrencia extra; msg nombra NN.

  Capa opcional (INFO, no error): changelog ausente -> rule CHANGELOG_MISSING;
  reports_dir ausente o sin reportes CONTRACT-* -> rule REPORTS_MISSING.
  Con cualquiera de las dos, las reglas ERROR no aplican.

  CLI: ``python scripts/validate_changelog.py [changelog] [reports_dir]``
  (defaults ``CHANGELOG.md`` y ``docs/reports``). ``main(argv) -> int``:
  imprime findings y ``Resumen: N error(es), M contrato(s) verificados`` donde
  M = cantidad de NN DISTINTOS vistos entre reportes y entradas (lo escaneado,
  nunca derivado solo de los findings). exit 0 sin ERRORs, 1 con >=1.

Este archivo es un ORACULO CONGELADO (tests_sha256): el implementador no lo
modifica. Ver knowledge/contracts/changelog-gate.md.
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

import validate_changelog as vc  # noqa: E402


ENTRY = ("**Contract {nn} — Demo {nn}** "
         "([C{nn}-REPORT](docs/reports/CONTRACT-{nn}-REPORT.md))\n")


class _Fixture(unittest.TestCase):
    def setUp(self):
        self.base = tempfile.mkdtemp(prefix="c27_")
        self.addCleanup(shutil.rmtree, self.base, ignore_errors=True)
        self.reports = os.path.join(self.base, "docs", "reports")
        os.makedirs(self.reports)
        self.changelog = os.path.join(self.base, "CHANGELOG.md")

    def _report(self, nn):
        p = os.path.join(self.reports, "CONTRACT-{}-REPORT.md".format(nn))
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("# CONTRACT-{} REPORT\n".format(nn))
        return p

    def _write_changelog(self, entries, extra=""):
        with open(self.changelog, "w", encoding="utf-8") as fh:
            fh.write("# Changelog\n\n## v9.9.9 — 2026-01-01\n\n")
            for nn in entries:
                fh.write(ENTRY.format(nn=nn) + "- detalle.\n\n")
            fh.write(extra)

    def _run(self):
        return vc.validate_changelog(self.changelog, self.reports)

    def _errors(self):
        return [f for f in self._run() if f["level"] == "ERROR"]


class TestCoherente(_Fixture):
    def test_par_coherente_sin_findings(self):
        for nn in ("01", "02", "10"):
            self._report(nn)
        self._write_changelog(["01", "02", "10"])
        self.assertEqual(self._run(), [])

    def test_template_report_ignorado(self):
        self._report("01")
        with open(os.path.join(self.reports, "TEMPLATE-REPORT.md"), "w",
                  encoding="utf-8") as fh:
            fh.write("# template\n")
        self._write_changelog(["01"])
        self.assertEqual(self._run(), [])

    def test_finding_shape_y_orden(self):
        self._report("01")
        self._report("02")
        self._write_changelog([])
        findings = self._run()
        self.assertTrue(findings)
        for f in findings:
            self.assertEqual(sorted(f.keys()),
                             ["file", "level", "msg", "rule"])
        keys = [(f["file"], f["rule"], f["msg"]) for f in findings]
        self.assertEqual(keys, sorted(keys))


class TestIncidente(_Fixture):
    def test_reporte_sin_entrada_es_entry_missing(self):
        # LA clase del incidente v1.2.0: el reporte existe, la entrada no.
        self._report("20")
        self._report("21")
        self._write_changelog(["20"])
        errs = self._errors()
        self.assertEqual(len(errs), 1, errs)
        self.assertEqual(errs[0]["rule"], "ENTRY_MISSING")
        self.assertIn("21", errs[0]["msg"])
        self.assertIn("CONTRACT-21-REPORT.md", errs[0]["msg"])

    def test_entrada_fantasma_es_report_missing(self):
        self._report("01")
        self._write_changelog(["01", "99"])
        errs = self._errors()
        self.assertEqual(len(errs), 1, errs)
        self.assertEqual(errs[0]["rule"], "REPORT_MISSING")
        self.assertIn("99", errs[0]["msg"])

    def test_entrada_sin_link_es_link_missing(self):
        self._report("05")
        self._write_changelog([], extra="**Contract 05 — Sin link**\n")
        errs = self._errors()
        self.assertEqual(len(errs), 1, errs)
        self.assertEqual(errs[0]["rule"], "LINK_MISSING")
        self.assertIn("05", errs[0]["msg"])

    def test_entrada_duplicada_es_entry_dup(self):
        self._report("07")
        self._write_changelog(["07", "07"])
        errs = self._errors()
        self.assertEqual([e["rule"] for e in errs], ["ENTRY_DUP"])
        self.assertIn("07", errs[0]["msg"])

    def test_linea_que_no_empieza_con_entrada_no_cuenta(self):
        self._report("03")
        self._write_changelog(
            ["03"], extra="ver **Contract 88** mencionado en prosa.\n")
        self.assertEqual(self._run(), [])


class TestCapaOpcionalYCli(_Fixture):
    def test_changelog_ausente_info(self):
        self._report("01")
        findings = vc.validate_changelog(
            os.path.join(self.base, "no-existe.md"), self.reports)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["level"], "INFO")
        self.assertEqual(findings[0]["rule"], "CHANGELOG_MISSING")

    def test_reports_ausente_o_vacio_info(self):
        self._write_changelog([])
        for rd in (os.path.join(self.base, "no-existe"), self.reports):
            findings = vc.validate_changelog(self.changelog, rd)
            self.assertEqual(len(findings), 1, findings)
            self.assertEqual(findings[0]["level"], "INFO")
            self.assertEqual(findings[0]["rule"], "REPORTS_MISSING")

    def test_cli_exit_y_resumen_honesto(self):
        for nn in ("01", "02"):
            self._report(nn)
        self._write_changelog(["01", "02"])
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = vc.main([self.changelog, self.reports])
        self.assertEqual(code, 0)
        self.assertIn("0 error(es), 2 contrato(s)", out.getvalue())

    def test_cli_exit_1_con_error(self):
        self._report("01")
        self._write_changelog([])
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = vc.main([self.changelog, self.reports])
        self.assertEqual(code, 1)
        self.assertIn("ENTRY_MISSING", out.getvalue())

    def test_determinismo(self):
        self._report("01")
        self._report("02")
        self._write_changelog(["01"])
        self.assertEqual(self._run(), self._run())


class TestRepoReal(unittest.TestCase):
    """El gate custodia la historia REAL: el par del repo pasa limpio."""

    def test_repo_real_sin_errores(self):
        findings = vc.validate_changelog(
            os.path.join(ROOT, "CHANGELOG.md"),
            os.path.join(ROOT, "docs", "reports"))
        errors = [f for f in findings if f["level"] == "ERROR"]
        self.assertEqual(errors, [], "repo real incoherente: {!r}".format(
            errors))


if __name__ == "__main__":
    unittest.main()
