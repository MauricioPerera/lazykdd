"""Oraculo congelado del CLI de KDD (Contrato: kdd-gates-run-single-json).

Fija el comportamiento de ``scripts/kdd_cli.py`` -- la Piel 2 (CLI Python)
del proyecto lazykdd. Cubre CINCO subcomandos despachados por UNA sola
funcion (un dispatcher delgado que delega cada rama a un handler
``_handle_*``; toda la logica real vive en los handlers o en las funciones
de modulo, no inline en ``main``):

    main(argv, stdout, run_all_fn=None, list_contracts_fn=None,
         scaffold_fn=None, status_fn=None, run_gate_fn=None) -> int

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
- ``argv == ['gates', 'run', <gate_name>, '--json']`` (4 elementos
  EXACTOS: ``argv[0]=='gates'``, ``argv[1]=='run'``, ``argv[3]=='--json'``;
  ``argv[2]`` es el nombre de gate, un string):
  - ``fn = run_gate_fn if run_gate_fn is not None else run_single_gate_json``
    (default del mismo modulo).
  - ``result = fn(argv[2], repo_root='.')``. ``fn`` SIEMPRE se llama para
    este patron (a diferencia de list/scaffold/status): es ``fn`` la que
    decide si el nombre de gate es invalido y arma el dict de error.
  - si ``result`` tiene clave ``'error'``: escribe ``json.dumps(result)``,
    devuelve ``1``.
  - si no (tiene ``'exit_code'``): escribe ``json.dumps(result)``, devuelve
    ``0`` si ``result['exit_code'] == 0``, si no ``1``.
  - ``run_gate_fn`` NUNCA se llama si ``argv`` no matchea exactamente ese
    patron (largo distinto, subcomandos distintos, falta ``--json``, orden
    roto, flag extra).
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
- ``argv == ['contracts', 'scaffold', <task_name>, '--json']`` (4 elementos
  EXACTOS: ``argv[0]=='contracts'``, ``argv[1]=='scaffold'``,
  ``argv[3]=='--json'``; ``argv[2]`` es el nombre de tarea, un string):
  - ``fn = scaffold_fn if scaffold_fn is not None else scaffold_contract``
    (default del mismo modulo).
  - ``result = fn(argv[2])``.
  - si ``result`` tiene ``'created': True``: escribe ``json.dumps(result)``,
    devuelve ``0``.
  - si ``result`` tiene clave ``'error'``: escribe ``json.dumps(result)``,
    devuelve ``1``.
  - ``scaffold_fn`` NUNCA se llama si ``argv`` no matchea exactamente ese
    patron (largo distinto, subcomandos distintos, falta ``--json``, orden
    roto, flag extra).
- ``argv == ['contracts', 'status', '--json']`` (3 elementos EXACTOS):
  - ``fn = status_fn if status_fn is not None else list_contract_status``
    (default del mismo modulo).
  - ``result = fn()`` (sin argumentos).
  - si ``result`` es una lista (incluida vacia): escribe
    ``json.dumps(result)`` (una sola linea, sin pretty-print), devuelve
    ``0``. Una lista vacia es exito, NO error.
  - si ``result`` es un dict con clave ``'error'``: escribe
    ``json.dumps(result)``, devuelve ``1``.
  - ``status_fn`` NUNCA se llama si ``argv`` no matchea exactamente.
- cualquier otro ``argv`` (vacio, --help, desconocido, subset/superset,
  orden roto, flag extra): escribe un mensaje de uso de UNA linea que
  empieza con ``usage:`` y menciona los CINCO subcomandos (``gates run-all
  --json``, ``gates run <name> --json``, ``contracts list --json``,
  ``contracts scaffold <task> --json`` y ``contracts status --json``) en
  ``stdout``, devuelve ``2``. NINGUN ``fn`` se llama. Nunca lanza una
  excepcion no controlada por un ``argv`` malformado.

``scaffold_contract(task_name, contracts_dir='knowledge/contracts',
template_path='knowledge/contracts/TEMPLATE-task-contract.md') -> dict``:
- valida ``task_name`` contra kebab-case estricto ``^[a-z0-9]+(-[a-z0-9]+)*$``;
  si no matchea devuelve ``{'error': 'invalid task name (must be kebab-case):
  ' + task_name}`` SIN tocar el filesystem.
- ``target_path = os.path.join(contracts_dir, task_name + '.md')``; si YA
  EXISTE devuelve ``{'error': 'contract already exists: ' + target_path}``
  (nunca sobreescribe).
- si ``template_path`` no existe devuelve ``{'error': 'template not found: '
  + template_path}``.
- reemplaza la linea ``task: <nombre-kebab-case>`` por ``task: <task_name>``
  y elimina el bloque final de instrucciones humanas (la linea ``---`` que
  precede a ``<!--`` y todo el comentario HTML hasta ``-->``); los demas
  placeholders ``<...>`` quedan intactos. Escribe el contenido en
  ``target_path`` y devuelve ``{'created': True, 'path': target_path}``.

``list_contract_status(contracts_dir='knowledge/contracts',
repo_root='.') -> list[dict] | dict``: etapa de ciclo de vida
(``draft`` < ``validated`` < ``implemented`` < ``verified``) de cada
contrato. Usa ``validate_contracts._collect_files`` (``None`` si la dir no
existe -> ``{'error': 'contracts dir not found: ' + contracts_dir}``),
corre ``validate_test_commands.run_all`` UNA vez y arma ``{path: item}``.
Por cada archivo: ``task`` del frontmatter (``''`` si no hay); ``validated
= no hay finding ERROR``; ``implemented = validated y el item de run_all
existe con ``ok is True``; ``verified = implemented y task y existe
``.agents/logs/<task>-REPORT.md``. Devuelve ``[{'task','lifecycle'}, ...]``
en el orden de ``_collect_files`` (puede ser vacia).

``run_single_gate_json(gate_name, repo_root='.') -> dict``: corre UN gate
especifico via ``mcp_gate_dispatch.run_gate``. Si ``gate_name`` NO esta en
``mcp_gate_dispatch.LEVEL1_GATES`` (nombre invalido, o ``'validate_attestation'``
que es local-only y esta excluido de ``LEVEL1_GATES`` -- mismo criterio que
``gates run-all``) devuelve ``{'error': 'unknown gate: ' + gate_name}`` SIN
llamar a ``mcp_gate_dispatch.run_gate``. Si es valido, devuelve
``mcp_gate_dispatch.run_gate(gate_name, {}, repo_root=repo_root)`` tal cual
(ese dict YA tiene ``'exit_code'``/``'stdout'``/``'stderr'``).

Los tests NUNCA invocan subprocess real contra el repo ni tocan red: para
``gates run``/``run-all``/``list``/``scaffold`` siempre inyectan un ``*_fn``
fake (lambda que devuelve un literal); el caso ``None`` se ejercita
monkeypatcheando el modulo (``mcp_gate_dispatch`` / ``kdd_cli``) con un fake. Los tests que
ejercitan ``scaffold_contract`` y ``list_contract_status`` directo usan
SIEMPRE un ``tempfile.mkdtemp()`` (contratos sinteticos, ``test_command``
fake tipo ``python -c "import sys; sys.exit(0/1)"`` y un ``.agents/logs/``
sintetico dentro del mismo tempdir) -- NUNCA contra ``knowledge/contracts/``
real. Un UNICO test dedicado verifica el default real via ``main``
chdir-eando a un tempdir (nunca contra el repo). Sin subprocess contra el
repo real, ni red, ni filesystem real del repo dentro de un test.
"""

import io
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import mcp_gate_dispatch  # noqa: E402
import kdd_cli  # noqa: E402
import validate_contracts  # noqa: E402
from kdd_cli import main  # noqa: E402

_JSON_OK = {"overall_ok": True, "results": {}}
_JSON_BAD = {"overall_ok": False, "results": {"x": {"exit_code": 1}}}
_LIST_ERR = {"error": "contracts dir not found: knowledge/contracts"}
_ONE = [{"task": "a", "title": "A", "intent": "do a", "target": "a.py"}]
_TWO = [
    {"task": "a", "title": "A", "intent": "do a", "target": "a.py"},
    {"task": "b", "title": "B", "intent": "do b", "target": "b.py"},
]
_CREATED = {"created": True, "path": "knowledge/contracts/x.md"}
_SCAFFOLD_ERR = {"error": "invalid task name (must be kebab-case): Bad"}
_STATUS_ONE = [{"task": "a", "lifecycle": "draft"}]
_STATUS_TWO = [
    {"task": "a", "lifecycle": "draft"},
    {"task": "b", "lifecycle": "verified"},
]
_STATUS_ERR = {"error": "contracts dir not found: knowledge/contracts"}
_GATE_OK = {"exit_code": 0, "stdout": "ok\n", "stderr": ""}
_GATE_FAIL = {"exit_code": 1, "stdout": "", "stderr": "boom"}
_GATE_ERR = {"error": "unknown gate: does-not-exist"}

_REAL_TEMPLATE = os.path.join(ROOT, "knowledge", "contracts",
                              "TEMPLATE-task-contract.md")


def _list_fn(payload):
    """Construye un list_contracts_fn fake que ignora su argumento."""
    return lambda contracts_dir="knowledge/contracts": payload


def _run_gate_fn(payload):
    """Construye un run_gate_fn fake que ignora sus argumentos
    (``gate_name`` y ``repo_root``)."""
    return lambda gate_name, repo_root=".": payload


def _scaffold_fn(payload):
    """Construye un scaffold_fn fake que ignora su argumento (task_name)."""
    return lambda task_name: payload


def _make_tmpdir_with_template():
    """Crea un tempdir con una copia del template real.

    Devuelve ``(tmpdir, template_path)``. El tempdir se usa como
    ``contracts_dir`` y ``template_path`` apunta a la copia del template
    dentro del tempdir: el test nunca toca ``knowledge/contracts/`` real.
    """
    tmp = tempfile.mkdtemp()
    template_path = os.path.join(tmp, "TEMPLATE-task-contract.md")
    with open(_REAL_TEMPLATE, "r", encoding="utf-8") as fh:
        tmpl = fh.read()
    with open(template_path, "w", encoding="utf-8") as fh:
        fh.write(tmpl)
    return tmp, template_path


def _status_fn(payload):
    """Construye un status_fn fake que ignora su argumento (no recibe ninguno)."""
    return lambda: payload


def _valid_contract_text(task, test_command, tests_rel, tests_hash):
    """Frontmatter+body de un contrato sintetico que pasa ``validate_file``.

    ``target``/``tests`` resuelven a archivos que el test crea en el tempdir;
    ``tests_sha256`` es el hash real del archivo de tests (calculado con
    ``validate_contracts._calculate_tests_hash``). Las secciones obligatorias
    estan todas presentes con la forma que exige el validador (Examples con
    >=2 items, Constraints con 'PARAR y reportar si').
    """
    return (
        "---\n"
        "type: 'Task Contract'\n"
        "title: 'synth'\n"
        "description: 'synth'\n"
        "tags: ['synth']\n"
        "\n"
        "task: {task}\n"
        "intent: \"Hacer algo puntual.\"\n"
        "target: scripts/{task}.py\n"
        "signature: \"def f(x) -> int:\"\n"
        "test_command: '{cmd}'\n"
        "test_cwd: .\n"
        "budget:\n"
        "  cyclomatic_max: 5\n"
        "  nesting_max: 2\n"
        "  params_max: 2\n"
        "  lines_max: 20\n"
        "tests: {tests}\n"
        "tests_sha256: '{hsh}'\n"
        "touch_only: ['scripts/{task}.py']\n"
        "deps_allowed: []\n"
        "forbids: ['network', 'llm']\n"
        "---\n"
        "\n"
        "# Contract: synth\n"
        "\n"
        "## Intent\n"
        "Hacer algo puntual.\n"
        "\n"
        "## Interface\n"
        "```python\n"
        "def f(x) -> int:\n"
        "    ...\n"
        "```\n"
        "\n"
        "## Invariants\n"
        "- ``f`` no lanza.\n"
        "\n"
        "## Examples\n"
        "- ``f(1)`` -> ``1``.\n"
        "- ``f(2)`` -> ``2``.\n"
        "\n"
        "## Do / Don't\n"
        "- DO: mantenerlo simple.\n"
        "\n"
        "## Tests\n"
        "Tests en ``{tests}``.\n"
        "\n"
        "## Constraints\n"
        "- PARAR y reportar si algo falla.\n"
    ).format(task=task, cmd=test_command, tests=tests_rel, hsh=tests_hash)


def _write_valid_contract(repo, task, test_exit=0, with_report=False):
    """Escribe un contrato sintetico valido bajo ``repo`` y devuelve su path.

    Crea tambien ``repo/scripts/<task>.py`` (target) y ``repo/tests/test_<task>.py``
    (oraculo, cuyo hash se sella en el contrato). Opcionalmente crea
    ``repo/.agents/logs/<task>-REPORT.md`` (para la etapa ``verified``).
    """
    contracts_dir = os.path.join(repo, "knowledge", "contracts")
    os.makedirs(contracts_dir, exist_ok=True)
    os.makedirs(os.path.join(repo, "scripts"), exist_ok=True)
    os.makedirs(os.path.join(repo, "tests"), exist_ok=True)
    target_path = os.path.join(repo, "scripts", task + ".py")
    with open(target_path, "w", encoding="utf-8") as fh:
        fh.write("def f(x):\n    return x\n")
    tests_rel = "tests/test_{}.py".format(task)
    tests_abs = os.path.join(repo, tests_rel)
    with open(tests_abs, "w", encoding="utf-8") as fh:
        fh.write("import unittest\n")
    tests_hash = validate_contracts._calculate_tests_hash(tests_abs)
    test_command = 'python -c "import sys; sys.exit({})"'.format(test_exit)
    text = _valid_contract_text(task, test_command, tests_rel, tests_hash)
    contract_path = os.path.join(contracts_dir, task + ".md")
    with open(contract_path, "w", encoding="utf-8") as fh:
        fh.write(text)
    if with_report:
        logs_dir = os.path.join(repo, ".agents", "logs")
        os.makedirs(logs_dir, exist_ok=True)
        with open(os.path.join(logs_dir, task + "-REPORT.md"),
                  "w", encoding="utf-8") as fh:
            fh.write("# Report\n")
    return contract_path


def _write_draft_contract(repo, task):
    """Escribe un contrato sintetico INVALIDO (falla ``validate_file``).

    Solo tiene ``task`` en el frontmatter (sin ``test_command`` ni claves
    requeridas): ``validate_file`` emite ERRORs -> ``validated`` False ->
    etapa ``draft``. No aparece en ``run_all`` (sin ``test_command``).
    """
    contracts_dir = os.path.join(repo, "knowledge", "contracts")
    os.makedirs(contracts_dir, exist_ok=True)
    text = "---\ntask: {task}\n---\n\n# {task}\n".format(task=task)
    with open(os.path.join(contracts_dir, task + ".md"),
              "w", encoding="utf-8") as fh:
        fh.write(text)


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


class TestGatesRunSingleJson(unittest.TestCase):
    """Caso valido: ``['gates', 'run', <name>, '--json']`` con fn inyectado.

    El handler SIEMPRE llama a ``fn`` para este patron: es ``fn`` la que
    decide si el nombre es invalido y arma el dict de error. Los fakes
    devuelven literales (``_GATE_OK``/``_GATE_FAIL``/``_GATE_ERR``).
    """

    def test_valid_exit_0_returns_0(self):
        out = io.StringIO()
        rc = main(["gates", "run", "validate_contracts", "--json"], out,
                  run_gate_fn=_run_gate_fn(_GATE_OK))
        self.assertEqual(rc, 0)

    def test_valid_exit_0_writes_exact_json(self):
        out = io.StringIO()
        main(["gates", "run", "validate_contracts", "--json"], out,
             run_gate_fn=_run_gate_fn(_GATE_OK))
        self.assertEqual(json.loads(out.getvalue()), _GATE_OK)

    def test_valid_single_line_no_pretty_print(self):
        out = io.StringIO()
        main(["gates", "run", "validate_contracts", "--json"], out,
             run_gate_fn=_run_gate_fn(_GATE_OK))
        self.assertNotIn("\n", out.getvalue())

    def test_valid_exit_nonzero_returns_1(self):
        out = io.StringIO()
        rc = main(["gates", "run", "validate_contracts", "--json"], out,
                  run_gate_fn=_run_gate_fn(_GATE_FAIL))
        self.assertEqual(rc, 1)

    def test_valid_exit_nonzero_writes_json(self):
        out = io.StringIO()
        main(["gates", "run", "validate_contracts", "--json"], out,
             run_gate_fn=_run_gate_fn(_GATE_FAIL))
        self.assertEqual(json.loads(out.getvalue()), _GATE_FAIL)

    def test_fn_called_with_gate_name_and_repo_root(self):
        calls = []

        def fake(gate_name, repo_root="."):
            calls.append((gate_name, repo_root))
            return _GATE_OK

        out = io.StringIO()
        main(["gates", "run", "validate_changelog", "--json"], out,
             run_gate_fn=fake)
        self.assertEqual(calls, [("validate_changelog", ".")])

    def test_fn_result_round_trips_as_json(self):
        out = io.StringIO()
        payload = {"exit_code": 0, "stdout": "x\ny\n", "stderr": ""}
        main(["gates", "run", "validate_contracts", "--json"], out,
             run_gate_fn=_run_gate_fn(payload))
        self.assertEqual(json.loads(out.getvalue()), payload)

    def test_error_result_returns_1(self):
        out = io.StringIO()
        rc = main(["gates", "run", "validate_contracts", "--json"], out,
                  run_gate_fn=_run_gate_fn(_GATE_ERR))
        self.assertEqual(rc, 1)

    def test_error_result_writes_json(self):
        out = io.StringIO()
        main(["gates", "run", "validate_contracts", "--json"], out,
             run_gate_fn=_run_gate_fn(_GATE_ERR))
        self.assertEqual(json.loads(out.getvalue()), _GATE_ERR)

    def test_error_not_swallowed_as_success(self):
        out = io.StringIO()
        rc = main(["gates", "run", "validate_contracts", "--json"], out,
                  run_gate_fn=_run_gate_fn(_GATE_ERR))
        self.assertNotEqual(rc, 0)

    def test_missing_json_flag_is_usage(self):
        out = io.StringIO()
        rc = main(["gates", "run", "validate_contracts"], out,
                  run_gate_fn=_run_gate_fn(_GATE_OK))
        self.assertEqual(rc, 2)
        self.assertTrue(out.getvalue().startswith("usage:"))

    def test_wrong_flag_is_usage(self):
        out = io.StringIO()
        rc = main(["gates", "run", "validate_contracts", "--yaml"], out,
                  run_gate_fn=_run_gate_fn(_GATE_OK))
        self.assertEqual(rc, 2)

    def test_wrong_order_is_usage(self):
        out = io.StringIO()
        rc = main(["gates", "run", "--json", "validate_contracts"], out,
                  run_gate_fn=_run_gate_fn(_GATE_OK))
        self.assertEqual(rc, 2)

    def test_extra_arg_is_usage(self):
        out = io.StringIO()
        rc = main(["gates", "run", "validate_contracts", "--json", "extra"],
                  out, run_gate_fn=_run_gate_fn(_GATE_OK))
        self.assertEqual(rc, 2)

    def test_subset_two_words_is_usage(self):
        out = io.StringIO()
        rc = main(["gates", "run"], out, run_gate_fn=_run_gate_fn(_GATE_OK))
        self.assertEqual(rc, 2)

    def test_subset_three_words_is_usage(self):
        out = io.StringIO()
        rc = main(["gates", "run", "validate_contracts"], out,
                  run_gate_fn=_run_gate_fn(_GATE_OK))
        self.assertEqual(rc, 2)

    def test_run_gate_fn_never_called_on_invalid_argv(self):
        called = []

        def fake(gate_name, repo_root="."):
            called.append(gate_name)
            return _GATE_OK

        out = io.StringIO()
        main(["gates", "run"], out, run_gate_fn=fake)
        main(["gates", "run", "validate_contracts"], out, run_gate_fn=fake)
        main(["gates", "run", "validate_contracts", "--yaml"], out,
             run_gate_fn=fake)
        main(["gates", "run", "--json", "validate_contracts"], out,
             run_gate_fn=fake)
        main(["gates", "run", "validate_contracts", "--json", "extra"], out,
             run_gate_fn=fake)
        self.assertEqual(called, [])

    def test_run_all_distinct_from_run(self):
        # ``['gates', 'run-all', '--json']`` NO dispara el handler de ``run``:
        # usa ``run_all_fn``, no ``run_gate_fn``.
        gate_called = []
        out = io.StringIO()
        rc = main(["gates", "run-all", "--json"], out,
                  run_all_fn=lambda repo_root=".": _JSON_OK,
                  run_gate_fn=lambda gate_name, repo_root=".":
                      gate_called.append(gate_name) or _GATE_OK)
        self.assertEqual(rc, 0)
        self.assertEqual(gate_called, [])


class TestDefaultRunGateFn(unittest.TestCase):
    """``run_gate_fn=None`` resuelve a ``kdd_cli.run_single_gate_json``.

    Se ejercita con un nombre de gate valido (miembro de
    ``LEVEL1_GATES``) monkeypatcheando ``mcp_gate_dispatch.run_gate`` con un
    fake que devuelve un literal -- sin subprocess real.
    """

    def test_none_fn_valid_gate_delegates_to_run_single_gate_json(self):
        original = mcp_gate_dispatch.run_gate
        calls = []

        def fake_run_gate(tool_name, params, repo_root=".", timeout=120):
            calls.append((tool_name, params, repo_root))
            return _GATE_OK

        mcp_gate_dispatch.run_gate = fake_run_gate
        try:
            out = io.StringIO()
            rc = main(["gates", "run", "validate_changelog", "--json"], out,
                      run_gate_fn=None)
            self.assertEqual(rc, 0)
            self.assertEqual(json.loads(out.getvalue()), _GATE_OK)
            self.assertEqual(calls, [("validate_changelog", {}, ".")])
        finally:
            mcp_gate_dispatch.run_gate = original

    def test_none_fn_valid_gate_exit_nonzero_returns_1(self):
        original = mcp_gate_dispatch.run_gate
        mcp_gate_dispatch.run_gate = (
            lambda tool_name, params, repo_root=".", timeout=120: _GATE_FAIL)
        try:
            out = io.StringIO()
            rc = main(["gates", "run", "validate_changelog", "--json"], out,
                      run_gate_fn=None)
            self.assertEqual(rc, 1)
            self.assertEqual(json.loads(out.getvalue()), _GATE_FAIL)
        finally:
            mcp_gate_dispatch.run_gate = original


class TestRunSingleGateJsonDirect(unittest.TestCase):
    """``run_single_gate_json`` directo -- sin subprocess real.

    Un nombre invalido (o ``'validate_attestation'``) devuelve el dict de
    error SIN llamar a ``mcp_gate_dispatch.run_gate`` (verificado con un fake
    contador). Un nombre valido delega a ``mcp_gate_dispatch.run_gate``.
    """

    def test_unknown_gate_returns_error(self):
        original = mcp_gate_dispatch.run_gate
        calls = []

        def fake_run_gate(tool_name, params, repo_root=".", timeout=120):
            calls.append(tool_name)
            return _GATE_OK

        mcp_gate_dispatch.run_gate = fake_run_gate
        try:
            rc = kdd_cli.run_single_gate_json("does-not-exist")
            self.assertEqual(rc, {"error": "unknown gate: does-not-exist"})
            self.assertEqual(calls, [])
        finally:
            mcp_gate_dispatch.run_gate = original

    def test_unknown_gate_via_main_run_gate_never_called(self):
        # via ``main`` con ``run_gate_fn=None`` (default real): un nombre
        # inventado -> error, exit 1, y ``mcp_gate_dispatch.run_gate`` NUNCA
        # se llama.
        original = mcp_gate_dispatch.run_gate
        calls = []

        def fake_run_gate(tool_name, params, repo_root=".", timeout=120):
            calls.append(tool_name)
            return _GATE_OK

        mcp_gate_dispatch.run_gate = fake_run_gate
        try:
            out = io.StringIO()
            rc = main(["gates", "run", "nombre-inventado-que-no-existe",
                       "--json"], out, run_gate_fn=None)
            self.assertEqual(rc, 1)
            self.assertEqual(
                json.loads(out.getvalue()),
                {"error": "unknown gate: nombre-inventado-que-no-existe"})
            self.assertEqual(calls, [])
        finally:
            mcp_gate_dispatch.run_gate = original

    def test_validate_attestation_treated_as_invalid(self):
        # ``validate_attestation`` es local-only: NO esta en LEVEL1_GATES,
        # mismo camino que un nombre inventado (error que lo nombra), sin
        # llamar a ``mcp_gate_dispatch.run_gate``.
        original = mcp_gate_dispatch.run_gate
        calls = []

        def fake_run_gate(tool_name, params, repo_root=".", timeout=120):
            calls.append(tool_name)
            return _GATE_OK

        mcp_gate_dispatch.run_gate = fake_run_gate
        try:
            out = io.StringIO()
            rc = main(["gates", "run", "validate_attestation", "--json"], out,
                      run_gate_fn=None)
            self.assertEqual(rc, 1)
            self.assertEqual(
                json.loads(out.getvalue()),
                {"error": "unknown gate: validate_attestation"})
            self.assertEqual(calls, [])
        finally:
            mcp_gate_dispatch.run_gate = original

    def test_valid_gate_delegates_to_run_gate(self):
        original = mcp_gate_dispatch.run_gate
        calls = []

        def fake_run_gate(tool_name, params, repo_root=".", timeout=120):
            calls.append((tool_name, params, repo_root))
            return _GATE_OK

        mcp_gate_dispatch.run_gate = fake_run_gate
        try:
            rc = kdd_cli.run_single_gate_json("validate_contracts",
                                              repo_root=".")
            self.assertEqual(rc, _GATE_OK)
            self.assertEqual(calls, [("validate_contracts", {}, ".")])
        finally:
            mcp_gate_dispatch.run_gate = original


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


class TestContractsScaffoldJson(unittest.TestCase):
    """Caso valido: ``['contracts','scaffold',<task>,'--json']`` con fn fake."""

    def test_created_returns_0(self):
        out = io.StringIO()
        rc = main(["contracts", "scaffold", "x", "--json"], out,
                  scaffold_fn=_scaffold_fn(_CREATED))
        self.assertEqual(rc, 0)

    def test_created_writes_exact_json(self):
        out = io.StringIO()
        main(["contracts", "scaffold", "x", "--json"], out,
             scaffold_fn=_scaffold_fn(_CREATED))
        self.assertEqual(json.loads(out.getvalue()), _CREATED)

    def test_created_single_line_no_pretty_print(self):
        out = io.StringIO()
        main(["contracts", "scaffold", "x", "--json"], out,
             scaffold_fn=_scaffold_fn(_CREATED))
        self.assertNotIn("\n", out.getvalue())

    def test_fn_called_with_task_name(self):
        calls = []

        def fake(task_name):
            calls.append(task_name)
            return _CREATED

        out = io.StringIO()
        main(["contracts", "scaffold", "my-task", "--json"], out,
             scaffold_fn=fake)
        self.assertEqual(calls, ["my-task"])

    def test_error_returns_1(self):
        out = io.StringIO()
        rc = main(["contracts", "scaffold", "Bad", "--json"], out,
                  scaffold_fn=_scaffold_fn(_SCAFFOLD_ERR))
        self.assertEqual(rc, 1)

    def test_error_writes_json(self):
        out = io.StringIO()
        main(["contracts", "scaffold", "Bad", "--json"], out,
             scaffold_fn=_scaffold_fn(_SCAFFOLD_ERR))
        self.assertEqual(json.loads(out.getvalue()), _SCAFFOLD_ERR)

    def test_error_not_swallowed_as_created(self):
        out = io.StringIO()
        rc = main(["contracts", "scaffold", "Bad", "--json"], out,
                  scaffold_fn=_scaffold_fn(_SCAFFOLD_ERR))
        self.assertNotEqual(rc, 0)

    def test_missing_json_flag_is_usage(self):
        out = io.StringIO()
        rc = main(["contracts", "scaffold", "x"], out,
                  scaffold_fn=_scaffold_fn(_CREATED))
        self.assertEqual(rc, 2)
        self.assertTrue(out.getvalue().startswith("usage:"))

    def test_wrong_flag_is_usage(self):
        out = io.StringIO()
        rc = main(["contracts", "scaffold", "x", "--yaml"], out,
                  scaffold_fn=_scaffold_fn(_CREATED))
        self.assertEqual(rc, 2)

    def test_wrong_order_is_usage(self):
        out = io.StringIO()
        rc = main(["contracts", "scaffold", "--json", "x"], out,
                  scaffold_fn=_scaffold_fn(_CREATED))
        self.assertEqual(rc, 2)

    def test_extra_arg_is_usage(self):
        out = io.StringIO()
        rc = main(["contracts", "scaffold", "x", "--json", "extra"], out,
                  scaffold_fn=_scaffold_fn(_CREATED))
        self.assertEqual(rc, 2)

    def test_subset_one_word_is_usage(self):
        out = io.StringIO()
        rc = main(["contracts", "scaffold"], out,
                  scaffold_fn=_scaffold_fn(_CREATED))
        self.assertEqual(rc, 2)

    def test_fn_never_called_on_invalid_argv(self):
        called = []

        def fake(task_name):
            called.append(task_name)
            return _CREATED

        out = io.StringIO()
        main(["contracts", "scaffold"], out, scaffold_fn=fake)
        main(["contracts", "scaffold", "x"], out, scaffold_fn=fake)
        main(["contracts", "scaffold", "x", "--yaml"], out, scaffold_fn=fake)
        main(["contracts", "scaffold", "--json", "x"], out, scaffold_fn=fake)
        main(["contracts", "scaffold", "x", "--json", "extra"], out,
             scaffold_fn=fake)
        self.assertEqual(called, [])


class TestDefaultScaffoldFn(unittest.TestCase):
    """``scaffold_fn=None`` resuelve a ``kdd_cli.scaffold_contract`` (fake)."""

    def test_none_fn_uses_module_scaffold_contract(self):
        original = kdd_cli.scaffold_contract

        def fake(task_name):
            return _CREATED

        kdd_cli.scaffold_contract = fake
        try:
            out = io.StringIO()
            rc = main(["contracts", "scaffold", "x", "--json"], out,
                      scaffold_fn=None)
            self.assertEqual(rc, 0)
            self.assertEqual(json.loads(out.getvalue()), _CREATED)
        finally:
            kdd_cli.scaffold_contract = original


class TestScaffoldRealDefaultViaMain(unittest.TestCase):
    """UN test: el default real (``scaffold_contract``) via ``main``, contra
    un tempdir (chdir). NUNCA contra el repo real.
    """

    def test_real_default_creates_file_in_tempdir(self):
        tmp = tempfile.mkdtemp()
        orig_cwd = os.getcwd()
        try:
            kc = os.path.join(tmp, "knowledge", "contracts")
            os.makedirs(kc)
            with open(_REAL_TEMPLATE, "r", encoding="utf-8") as fh:
                tmpl = fh.read()
            with open(os.path.join(kc, "TEMPLATE-task-contract.md"),
                      "w", encoding="utf-8") as fh:
                fh.write(tmpl)
            os.chdir(tmp)
            out = io.StringIO()
            rc = main(["contracts", "scaffold", "real-default-x", "--json"],
                      out, scaffold_fn=None)
            self.assertEqual(rc, 0)
            data = json.loads(out.getvalue())
            self.assertIs(data.get("created"), True)
            created_path = os.path.join(kc, "real-default-x.md")
            self.assertTrue(os.path.isfile(created_path))
            with open(created_path, "r", encoding="utf-8") as fh:
                text = fh.read()
            self.assertIn("task: real-default-x", text)
            self.assertNotIn("<!--", text)
        finally:
            os.chdir(orig_cwd)
            shutil.rmtree(tmp, ignore_errors=True)


class TestScaffoldContractDirect(unittest.TestCase):
    """``scaffold_contract`` directo contra un tempdir (nunca el repo real)."""

    def setUp(self):
        self.tmp, self.template_path = _make_tmpdir_with_template()
        self.contracts_dir = self.tmp

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_creates_contract_returns_created_true(self):
        rc = kdd_cli.scaffold_contract("my-task",
                                       contracts_dir=self.contracts_dir,
                                       template_path=self.template_path)
        self.assertIs(rc.get("created"), True)
        expected = os.path.join(self.contracts_dir, "my-task.md")
        self.assertEqual(rc["path"], expected)
        self.assertTrue(os.path.isfile(expected))

    def test_written_file_has_real_task_name(self):
        path = kdd_cli.scaffold_contract("demo-thing",
                                         contracts_dir=self.contracts_dir,
                                         template_path=self.template_path)["path"]
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn("task: demo-thing", text)
        self.assertNotIn("task: <nombre-kebab-case>", text)

    def test_written_file_has_no_human_instructions_block(self):
        path = kdd_cli.scaffold_contract("demo-thing",
                                         contracts_dir=self.contracts_dir,
                                         template_path=self.template_path)["path"]
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read()
        self.assertNotIn("<!--", text)
        self.assertNotIn("-->", text)
        self.assertNotIn("COMO USAR ESTA PLANTILLA", text)

    def test_written_file_ends_with_constraints_section(self):
        path = kdd_cli.scaffold_contract("demo-thing",
                                         contracts_dir=self.contracts_dir,
                                         template_path=self.template_path)["path"]
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read()
        self.assertNotIn("<!--", text)
        self.assertTrue(text.endswith("\n"))
        self.assertFalse(text.endswith("\n\n"))
        idx = text.find("## Constraints")
        self.assertGreater(idx, -1)
        tail = text[idx + len("## Constraints"):]
        self.assertNotIn("## ", tail)
        self.assertNotIn("\n---\n", tail)

    def test_other_placeholders_left_intact(self):
        path = kdd_cli.scaffold_contract("demo-thing",
                                         contracts_dir=self.contracts_dir,
                                         template_path=self.template_path)["path"]
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn("<titulo corto de la tarea>", text)
        self.assertIn("<ruta/al/archivo.py>", text)

    def test_kebab_variants_accepted(self):
        for name in ["a", "a-b", "a1-b2", "foo-bar-baz-99"]:
            rc = kdd_cli.scaffold_contract(name,
                                           contracts_dir=self.contracts_dir,
                                           template_path=self.template_path)
            self.assertIs(rc.get("created"), True, msg=name)
            self.assertTrue(os.path.isfile(os.path.join(self.contracts_dir,
                                                        name + ".md")),
                            msg=name)

    def test_non_kebab_rejected(self):
        for name in ["A", "a_B", "a--b", "-a", "a-", "a b", "", "a.b", "aB"]:
            rc = kdd_cli.scaffold_contract(name,
                                           contracts_dir=self.contracts_dir,
                                           template_path=self.template_path)
            self.assertIn("invalid task name", rc.get("error", ""),
                          msg=repr(name))
            self.assertFalse(os.path.isfile(os.path.join(self.contracts_dir,
                                                         name + ".md")),
                             msg=repr(name))

    def test_invalid_name_returns_error_without_touching_fs(self):
        rc = kdd_cli.scaffold_contract("Bad_Name",
                                       contracts_dir=self.contracts_dir,
                                       template_path=self.template_path)
        self.assertIn("error", rc)
        self.assertIn("invalid task name", rc["error"])
        self.assertFalse(os.path.isfile(os.path.join(self.contracts_dir,
                                                     "Bad_Name.md")))

    def test_invalid_name_checked_before_template_existence(self):
        rc = kdd_cli.scaffold_contract("Bad_Name",
                                       contracts_dir=self.contracts_dir,
                                       template_path=os.path.join(self.tmp,
                                                                  "nope.md"))
        self.assertIn("invalid task name", rc["error"])

    def test_existing_contract_returns_error_no_overwrite(self):
        kdd_cli.scaffold_contract("dup-task",
                                  contracts_dir=self.contracts_dir,
                                  template_path=self.template_path)
        path = os.path.join(self.contracts_dir, "dup-task.md")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("ORIGINAL MARKER\n")
        rc = kdd_cli.scaffold_contract("dup-task",
                                       contracts_dir=self.contracts_dir,
                                       template_path=self.template_path)
        self.assertIn("error", rc)
        self.assertIn("already exists", rc["error"])
        with open(path, "r", encoding="utf-8") as fh:
            self.assertEqual(fh.read(), "ORIGINAL MARKER\n")

    def test_template_not_found_returns_error(self):
        rc = kdd_cli.scaffold_contract("orphan-task",
                                       contracts_dir=self.contracts_dir,
                                       template_path=os.path.join(self.tmp,
                                                                  "nope.md"))
        self.assertIn("error", rc)
        self.assertIn("template not found", rc["error"])

    def test_already_exists_checked_before_template_read(self):
        # crea primero un contrato valido
        kdd_cli.scaffold_contract("dup-task",
                                  contracts_dir=self.contracts_dir,
                                  template_path=self.template_path)
        # ahora template_path no existe pero el target ya existe: debe
        # devolver 'already exists' (no 'template not found')
        rc = kdd_cli.scaffold_contract("dup-task",
                                       contracts_dir=self.contracts_dir,
                                       template_path=os.path.join(self.tmp,
                                                                  "nope.md"))
        self.assertIn("already exists", rc["error"])


class TestContractsStatusJson(unittest.TestCase):
    """Caso valido: ``['contracts', 'status', '--json']`` con fn inyectado."""

    def test_status_returns_0(self):
        out = io.StringIO()
        rc = main(["contracts", "status", "--json"], out,
                  status_fn=_status_fn(_STATUS_ONE))
        self.assertEqual(rc, 0)

    def test_status_writes_exact_json(self):
        out = io.StringIO()
        main(["contracts", "status", "--json"], out,
             status_fn=_status_fn(_STATUS_ONE))
        self.assertEqual(json.loads(out.getvalue()), _STATUS_ONE)

    def test_status_single_line_no_pretty_print(self):
        out = io.StringIO()
        main(["contracts", "status", "--json"], out,
             status_fn=_status_fn(_STATUS_TWO))
        self.assertNotIn("\n", out.getvalue())

    def test_status_empty_list_returns_0(self):
        out = io.StringIO()
        rc = main(["contracts", "status", "--json"], out,
                  status_fn=_status_fn([]))
        self.assertEqual(rc, 0)

    def test_status_empty_list_writes_literal_brackets(self):
        out = io.StringIO()
        main(["contracts", "status", "--json"], out, status_fn=_status_fn([]))
        self.assertEqual(out.getvalue(), "[]")

    def test_status_empty_list_is_success_not_error(self):
        out = io.StringIO()
        rc = main(["contracts", "status", "--json"], out,
                  status_fn=_status_fn([]))
        self.assertEqual(rc, 0)

    def test_status_fn_called_with_no_args(self):
        calls = []

        def fake():
            calls.append(())
            return _STATUS_ONE

        out = io.StringIO()
        main(["contracts", "status", "--json"], out, status_fn=fake)
        self.assertEqual(calls, [()])

    def test_status_two_items_round_trips(self):
        out = io.StringIO()
        main(["contracts", "status", "--json"], out,
             status_fn=_status_fn(_STATUS_TWO))
        self.assertEqual(json.loads(out.getvalue()), _STATUS_TWO)

    def test_status_error_dict_returns_1(self):
        out = io.StringIO()
        rc = main(["contracts", "status", "--json"], out,
                  status_fn=_status_fn(_STATUS_ERR))
        self.assertEqual(rc, 1)

    def test_status_error_dict_writes_json(self):
        out = io.StringIO()
        main(["contracts", "status", "--json"], out,
             status_fn=_status_fn(_STATUS_ERR))
        self.assertEqual(json.loads(out.getvalue()), _STATUS_ERR)

    def test_status_error_not_swallowed_as_list(self):
        out = io.StringIO()
        rc = main(["contracts", "status", "--json"], out,
                  status_fn=_status_fn(_STATUS_ERR))
        self.assertNotEqual(rc, 0)

    def test_status_missing_json_flag_is_usage(self):
        out = io.StringIO()
        rc = main(["contracts", "status"], out, status_fn=_status_fn(_STATUS_ONE))
        self.assertEqual(rc, 2)
        self.assertTrue(out.getvalue().startswith("usage:"))

    def test_status_wrong_flag_is_usage(self):
        out = io.StringIO()
        rc = main(["contracts", "status", "--yaml"], out,
                  status_fn=_status_fn(_STATUS_ONE))
        self.assertEqual(rc, 2)

    def test_status_extra_arg_is_usage(self):
        out = io.StringIO()
        rc = main(["contracts", "status", "--json", "extra"], out,
                  status_fn=_status_fn(_STATUS_ONE))
        self.assertEqual(rc, 2)

    def test_status_fn_never_called_on_invalid_argv(self):
        called = []

        def fake():
            called.append(True)
            return _STATUS_ONE

        out = io.StringIO()
        main(["contracts", "status"], out, status_fn=fake)
        main(["contracts", "status", "--yaml"], out, status_fn=fake)
        main(["contracts", "status", "--json", "extra"], out, status_fn=fake)
        main([], out, status_fn=fake)
        self.assertEqual(called, [])


class TestDefaultStatusFn(unittest.TestCase):
    """``status_fn=None`` resuelve a ``kdd_cli.list_contract_status`` (fake)."""

    def test_none_fn_uses_module_list_contract_status(self):
        original = kdd_cli.list_contract_status

        def fake():
            return _STATUS_ONE

        kdd_cli.list_contract_status = fake
        try:
            out = io.StringIO()
            rc = main(["contracts", "status", "--json"], out, status_fn=None)
            self.assertEqual(rc, 0)
            self.assertEqual(json.loads(out.getvalue()), _STATUS_ONE)
        finally:
            kdd_cli.list_contract_status = original


class TestListContractStatusDirect(unittest.TestCase):
    """``list_contract_status`` directo contra un tempdir (nunca el repo real).

    Cada contrato sintetico usa ``test_command`` fake ``python -c "import
    sys; sys.exit(0/1)"`` y un ``.agents/logs/`` sintetico dentro del mismo
    tempdir. NUNCA contra ``knowledge/contracts/`` real.
    """

    def setUp(self):
        self.repo = tempfile.mkdtemp()
        self.contracts_dir = os.path.join(self.repo, "knowledge", "contracts")

    def tearDown(self):
        shutil.rmtree(self.repo, ignore_errors=True)

    def _status(self):
        return kdd_cli.list_contract_status(contracts_dir=self.contracts_dir,
                                             repo_root=self.repo)

    def test_dir_not_found_returns_error(self):
        rc = kdd_cli.list_contract_status(
            contracts_dir=os.path.join(self.repo, "nope"), repo_root=self.repo)
        self.assertIn("error", rc)
        self.assertIn("contracts dir not found", rc["error"])

    def test_empty_dir_returns_empty_list(self):
        os.makedirs(self.contracts_dir, exist_ok=True)
        self.assertEqual(self._status(), [])

    def test_draft_stage(self):
        _write_draft_contract(self.repo, "draft-x")
        status = self._status()
        self.assertEqual(len(status), 1)
        self.assertEqual(status[0], {"task": "draft-x", "lifecycle": "draft"})

    def test_validated_stage(self):
        _write_valid_contract(self.repo, "val-x", test_exit=1)
        status = self._status()
        self.assertEqual(status[0], {"task": "val-x", "lifecycle": "validated"})

    def test_implemented_stage(self):
        _write_valid_contract(self.repo, "impl-x", test_exit=0, with_report=False)
        status = self._status()
        self.assertEqual(status[0],
                         {"task": "impl-x", "lifecycle": "implemented"})

    def test_verified_stage(self):
        _write_valid_contract(self.repo, "ver-x", test_exit=0, with_report=True)
        status = self._status()
        self.assertEqual(status[0], {"task": "ver-x", "lifecycle": "verified"})

    def test_result_items_have_only_task_and_lifecycle(self):
        _write_valid_contract(self.repo, "keys-x", test_exit=0, with_report=True)
        for item in self._status():
            self.assertEqual(set(item.keys()), {"task", "lifecycle"})

    def test_order_is_alphabetical(self):
        _write_valid_contract(self.repo, "zeta", test_exit=0)
        _write_valid_contract(self.repo, "alpha", test_exit=0)
        _write_draft_contract(self.repo, "mid")
        tasks = [item["task"] for item in self._status()]
        self.assertEqual(tasks, ["alpha", "mid", "zeta"])

    def test_multiple_stages_combined(self):
        _write_draft_contract(self.repo, "a-draft")
        _write_valid_contract(self.repo, "b-validated", test_exit=1)
        _write_valid_contract(self.repo, "c-implemented", test_exit=0)
        _write_valid_contract(self.repo, "d-verified", test_exit=0,
                              with_report=True)
        by_task = {item["task"]: item["lifecycle"] for item in self._status()}
        self.assertEqual(by_task["a-draft"], "draft")
        self.assertEqual(by_task["b-validated"], "validated")
        self.assertEqual(by_task["c-implemented"], "implemented")
        self.assertEqual(by_task["d-verified"], "verified")

    def test_verified_requires_report_file(self):
        # implemented pero SIN report -> implemented, no verified
        _write_valid_contract(self.repo, "no-report", test_exit=0,
                              with_report=False)
        status = self._status()
        self.assertEqual(status[0]["lifecycle"], "implemented")

    def test_validated_required_for_implemented(self):
        # test_command exit 0 pero contrato invalido -> draft (no validated)
        _write_draft_contract(self.repo, "bad")
        status = self._status()
        self.assertEqual(status[0]["lifecycle"], "draft")


class TestStatusRealDefaultViaMain(unittest.TestCase):
    """UN test: el default real (``list_contract_status``) via ``main``, contra
    un tempdir (chdir). NUNCA contra el repo real. Solo aserta estructura.
    """

    def test_real_default_returns_list_with_task_and_lifecycle(self):
        repo = tempfile.mkdtemp()
        orig_cwd = os.getcwd()
        try:
            _write_valid_contract(repo, "real-status-x", test_exit=0,
                                  with_report=True)
            os.chdir(repo)
            out = io.StringIO()
            rc = main(["contracts", "status", "--json"], out, status_fn=None)
            self.assertEqual(rc, 0)
            data = json.loads(out.getvalue())
            self.assertIsInstance(data, list)
            self.assertGreater(len(data), 0)
            allowed = {"draft", "validated", "implemented", "verified"}
            for item in data:
                self.assertEqual(set(item.keys()), {"task", "lifecycle"})
                self.assertIn(item["lifecycle"], allowed)
        finally:
            os.chdir(orig_cwd)
            shutil.rmtree(repo, ignore_errors=True)


class TestInvalidArgv(unittest.TestCase):
    """Cualquier otro ``argv`` -> mensaje de uso (``usage:``) + exit 2.

    El mensaje debe mencionar los CINCO subcomandos disponibles.
    """

    def _assert_usage(self, argv, run_all_fn=None, list_contracts_fn=None,
                      scaffold_fn=None, status_fn=None, run_gate_fn=None):
        out = io.StringIO()
        rc = main(argv, out, run_all_fn=run_all_fn,
                  list_contracts_fn=list_contracts_fn, scaffold_fn=scaffold_fn,
                  status_fn=status_fn, run_gate_fn=run_gate_fn)
        self.assertEqual(rc, 2, msg="argv={!r}".format(argv))
        msg = out.getvalue()
        self.assertTrue(msg.startswith("usage:"),
                        msg="argv={!r} -> {!r}".format(argv, msg))
        self.assertIn("gates run-all --json", msg,
                      msg="argv={!r} -> {!r}".format(argv, msg))
        self.assertIn("gates run <name> --json", msg,
                      msg="argv={!r} -> {!r}".format(argv, msg))
        self.assertIn("contracts list --json", msg,
                      msg="argv={!r} -> {!r}".format(argv, msg))
        self.assertIn("contracts scaffold <task> --json", msg,
                      msg="argv={!r} -> {!r}".format(argv, msg))
        self.assertIn("contracts status --json", msg,
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

    def test_scaffold_fn_never_called_on_invalid_argv(self):
        called = []

        def fake(task_name):
            called.append(task_name)
            return _CREATED

        self._assert_usage([], scaffold_fn=fake)
        self._assert_usage(["contracts", "scaffold"], scaffold_fn=fake)
        self._assert_usage(["contracts", "scaffold", "x"], scaffold_fn=fake)
        self._assert_usage(["contracts", "scaffold", "x", "--yaml"],
                           scaffold_fn=fake)
        self._assert_usage(["contracts", "scaffold", "--json", "x"],
                           scaffold_fn=fake)
        self._assert_usage(["contracts", "scaffold", "x", "--json", "extra"],
                           scaffold_fn=fake)
        self.assertEqual(called, [])

    def test_neither_of_three_fn_called_on_invalid_argv(self):
        run_called = []
        list_called = []
        scaffold_called = []

        def rf(repo_root="."):
            run_called.append(True)
            return _JSON_OK

        def lf(contracts_dir="knowledge/contracts"):
            list_called.append(True)
            return []

        def sf(task_name):
            scaffold_called.append(True)
            return _CREATED

        self._assert_usage(["frobnicate"], run_all_fn=rf, list_contracts_fn=lf,
                           scaffold_fn=sf)
        self.assertEqual(run_called, [])
        self.assertEqual(list_called, [])
        self.assertEqual(scaffold_called, [])

    def test_gates_run_subset_one_word(self):
        self._assert_usage(["gates"])

    def test_gates_run_subset_two_words(self):
        self._assert_usage(["gates", "run"])

    def test_gates_run_missing_json_flag(self):
        self._assert_usage(["gates", "run", "validate_contracts"])

    def test_gates_run_wrong_flag(self):
        self._assert_usage(["gates", "run", "validate_contracts", "--yaml"])

    def test_gates_run_wrong_order(self):
        self._assert_usage(["gates", "run", "--json", "validate_contracts"])

    def test_gates_run_superset_extra_arg(self):
        self._assert_usage(["gates", "run", "validate_contracts", "--json",
                            "extra"])

    def test_run_gate_fn_never_called_on_invalid_argv(self):
        called = []

        def fake(gate_name, repo_root="."):
            called.append(gate_name)
            return _GATE_OK

        self._assert_usage([], run_gate_fn=fake)
        self._assert_usage(["gates", "run"], run_gate_fn=fake)
        self._assert_usage(["gates", "run", "validate_contracts"],
                           run_gate_fn=fake)
        self._assert_usage(["gates", "run", "validate_contracts", "--yaml"],
                           run_gate_fn=fake)
        self._assert_usage(["gates", "run", "--json", "validate_contracts"],
                           run_gate_fn=fake)
        self._assert_usage(["gates", "run", "validate_contracts", "--json",
                            "extra"], run_gate_fn=fake)
        self.assertEqual(called, [])

    def test_neither_of_four_fn_called_on_invalid_argv(self):
        run_called = []
        list_called = []
        scaffold_called = []
        gate_called = []

        def rf(repo_root="."):
            run_called.append(True)
            return _JSON_OK

        def lf(contracts_dir="knowledge/contracts"):
            list_called.append(True)
            return []

        def sf(task_name):
            scaffold_called.append(True)
            return _CREATED

        def gf(gate_name, repo_root="."):
            gate_called.append(True)
            return _GATE_OK

        self._assert_usage(["frobnicate"], run_all_fn=rf, list_contracts_fn=lf,
                           scaffold_fn=sf, run_gate_fn=gf)
        self.assertEqual(run_called, [])
        self.assertEqual(list_called, [])
        self.assertEqual(scaffold_called, [])
        self.assertEqual(gate_called, [])


if __name__ == "__main__":
    unittest.main()