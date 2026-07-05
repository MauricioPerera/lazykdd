"""Tests unitarios del validador de specs (scripts/validate_specs.py).

Fixtures propias en tempdir (NO tocan specs/ real) + un test contra specs/
real del repo (debe pasar limpio). Los tests del CLI usan subprocess
(permitido en tests, prohibido en el target).
"""

import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'scripts'))

import validate_specs as vs  # noqa: E402


# ---------------------------------------------------------------------------
# Plantillas de fixture
# ---------------------------------------------------------------------------

def _open_body(criterios, restricciones):
    return (
        "# Contrato fixture\n\n"
        "## Criterios de aceptación\n\n{crit}\n\n"
        "## Restricciones\n\n{restr}\n"
    ).format(crit=criterios, restr=restricciones)


# Criterios validos: checkbox con comando entre backticks.
GOOD_CRIT = (
    "- [ ] `python scripts/validate_specs.py specs` exit 0.\n"
    "- [ ] `python -m unittest discover -s tests` verde.\n"
)

# Restricciones validas para un ABIERTO: Tocar SOLO + ABORTAR SI sin angulos.
GOOD_RESTR_OPEN = (
    "- Tocar SOLO: `scripts/validate_specs.py`, `tests/test_validate_specs.py`.\n"
    "- Sin dependencias nuevas (stdlib).\n"
    "- ABORTAR SI: una regla resulta imposible de cumplir manteniendo verdes los\n"
    "  contratos historicos. En ese caso PARAR, documentar y marcar BLOQUEADO.\n"
)

# Restricciones validas para un CERRADO: no exige Tocar SOLO ni ABORTAR SI.
GOOD_RESTR_CLOSED = (
    "- Sin dependencias nuevas (stdlib).\n"
    "- NO commitear (el PM commitea por tarea verificada).\n"
)


def _write(d, rel, content):
    path = os.path.join(d, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(content)
    return path


def _make_repo(d, contracts):
    """Crea un specs/ + docs/reports/ simulado en `d`.

    `contracts` es lista de tuplas (filename, body, closed_bool).
    """
    for filename, body, closed in contracts:
        _write(d, os.path.join('specs', filename), body)
        if closed:
            prefix = vs._prefix_of(filename)
            _write(d, os.path.join('docs', 'reports',
                                   prefix + '-REPORT.md'),
                   "# Reporte de {}\n".format(prefix))


def _rules(findings):
    return {f['rule'] for f in findings if f['level'] == 'ERROR'}


def _files(findings):
    return {f['file'] for f in findings if f['level'] == 'ERROR'}


# ---------------------------------------------------------------------------
# Tests de la API
# ---------------------------------------------------------------------------

class TestRealRepo(unittest.TestCase):
    def test_real_specs_pass_clean(self):
        specs = os.path.join(ROOT, 'specs')
        findings = vs.validate_specs(specs)
        errors = [f for f in findings if f['level'] == 'ERROR']
        self.assertEqual(errors, [], msg=errors)


class TestOpenComplete(unittest.TestCase):
    def test_open_complete_no_errors(self):
        with tempfile.TemporaryDirectory() as d:
            _make_repo(d, [(
                'CONTRACT-10-abierto-completo.md',
                _open_body(GOOD_CRIT, GOOD_RESTR_OPEN),
                False)])
            findings = vs.validate_specs(os.path.join(d, 'specs'))
            self.assertEqual(findings, [], msg=findings)


class TestOpenNoAbortar(unittest.TestCase):
    def test_open_without_abortar_is_error(self):
        restr = (
            "- Tocar SOLO: `scripts/x.py`.\n"
            "- Sin dependencias nuevas.\n"
        )  # sin ABORTAR SI
        with tempfile.TemporaryDirectory() as d:
            _make_repo(d, [(
                'CONTRACT-11-sin-abortar.md',
                _open_body(GOOD_CRIT, restr),
                False)])
            findings = vs.validate_specs(os.path.join(d, 'specs'))
            self.assertIn('ABORTAR', _rules(findings))
            self.assertIn('specs/CONTRACT-11-sin-abortar.md', _files(findings))


class TestOpenAbortarWithPlaceholder(unittest.TestCase):
    def test_open_abortar_with_angle_placeholder_is_error(self):
        restr = (
            "- Tocar SOLO: `scripts/x.py`.\n"
            "- ABORTAR SI: <condicion del template> -> PARAR y reportar.\n"
        )
        with tempfile.TemporaryDirectory() as d:
            _make_repo(d, [(
                'CONTRACT-12-abortar-placeholder.md',
                _open_body(GOOD_CRIT, restr),
                False)])
            findings = vs.validate_specs(os.path.join(d, 'specs'))
            self.assertIn('ABORTAR', _rules(findings))


class TestOpenNoBacktickCommand(unittest.TestCase):
    def test_open_without_backtick_command_is_error(self):
        crit = (
            "- [ ] La suite de tests pasa en verde.\n"
            "- [ ] El validador exit 0.\n"
        )  # sin backticks
        with tempfile.TemporaryDirectory() as d:
            _make_repo(d, [(
                'CONTRACT-13-sin-backtick.md',
                _open_body(crit, GOOD_RESTR_OPEN),
                False)])
            findings = vs.validate_specs(os.path.join(d, 'specs'))
            self.assertIn('SEC_CRITERIOS', _rules(findings))


class TestClosedNoAbortarNoTocar(unittest.TestCase):
    def test_closed_without_abortar_and_tocar_passes(self):
        with tempfile.TemporaryDirectory() as d:
            _make_repo(d, [(
                'CONTRACT-14-cerrado.md',
                _open_body(GOOD_CRIT, GOOD_RESTR_CLOSED),
                True)])
            findings = vs.validate_specs(os.path.join(d, 'specs'))
            self.assertEqual(findings, [], msg=findings)


class TestTemplateIgnored(unittest.TestCase):
    def test_template_is_ignored(self):
        # TEMPLATE con placeholders que FALLARIAN si se validara como abierto.
        template_body = (
            "# Contrato NN\n\n"
            "## Criterios de aceptacion\n\n"
            "- [ ] Sin comando entre backticks.\n\n"
            "## Restricciones\n\n"
            "- ABORTAR SI: <placeholder> -> <otro>.\n"
        )
        with tempfile.TemporaryDirectory() as d:
            _write(d, 'specs/TEMPLATE-CONTRACT.md', template_body)
            findings = vs.validate_specs(os.path.join(d, 'specs'))
            self.assertEqual(findings, [], msg=findings)


# ---------------------------------------------------------------------------
# Tests del CLI (subprocess permitido en tests)
# ---------------------------------------------------------------------------

class TestCLI(unittest.TestCase):
    def _run_cli(self, specs_dir):
        proc = subprocess.run(
            [sys.executable, os.path.join(ROOT, 'scripts',
                                         'validate_specs.py'), specs_dir],
            capture_output=True, text=True)
        return proc.returncode, proc.stdout + proc.stderr

    def test_cli_exit_zero_on_real_specs(self):
        rc, out = self._run_cli(os.path.join(ROOT, 'specs'))
        self.assertEqual(rc, 0, msg=out)
        self.assertIn('Resumen', out)

    def test_cli_exit_zero_on_open_complete(self):
        with tempfile.TemporaryDirectory() as d:
            _make_repo(d, [(
                'CONTRACT-10-abierto-completo.md',
                _open_body(GOOD_CRIT, GOOD_RESTR_OPEN),
                False)])
            rc, out = self._run_cli(os.path.join(d, 'specs'))
            self.assertEqual(rc, 0, msg=out)

    def test_cli_exit_one_on_open_no_abortar(self):
        with tempfile.TemporaryDirectory() as d:
            _make_repo(d, [(
                'CONTRACT-11-sin-abortar.md',
                _open_body(GOOD_CRIT,
                           "- Tocar SOLO: `scripts/x.py`.\n"),
                False)])
            rc, out = self._run_cli(os.path.join(d, 'specs'))
            self.assertEqual(rc, 1, msg=out)
            self.assertIn('ABORTAR', out)


if __name__ == '__main__':
    unittest.main()