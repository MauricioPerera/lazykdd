---
type: 'Task Contract'
title: 'CLI: gates run-all --json'
description: 'Primera pieza del CLI Python (Piel 2) de lazykdd: despacha `gates run-all --json` al motor de gates existente y emite JSON, sin subprocess propio.'
tags: ['ccdd', 'cli', 'lazykdd', 'gate']

task: kdd-gates-run-all-json
intent: "Despachar el subcomando `gates run-all --json` al motor de gates existente, escribiendo su JSON en stdout."
target: scripts/kdd_cli.py
signature: "def main(argv, stdout, run_all_fn=None) -> int:"
test_command: "python -m unittest tests/test_kdd_cli.py"
test_cwd: ../..
budget:
  max_cyclomatic_complexity: 5
  max_nesting_depth: 2
  cyclomatic_max: 5
  nesting_max: 2
  params_max: 3
  lines_max: 30
tests: "tests/test_kdd_cli.py"
tests_sha256: "c47379bb8ad8ea050e87709c9d0c6c9bf4412c31998af9dc00d87855b3e8118f"
touch_only: ['scripts/kdd_cli.py']
deps_allowed: []
forbids: ['network', 'llm']
---

# Contract: CLI `gates run-all --json`

## Intent
Primera pieza de la Piel 2 (CLI Python) del proyecto lazykdd: un unico
punto de entrada `scripts/kdd_cli.py` con UNA sola funcion nueva,
`main(argv, stdout, run_all_fn=None) -> int`, que despacha el subcomando
`gates run-all --json` al motor de gates ya existente
([mcp-gate-dispatch](./mcp-gate-dispatch.md)) y emite el JSON resultante.
Esta funcion es TODO el alcance de esta tarea: sin mas subcomandos, sin
paquete instalable, sin entry_point (tareas futuras, fuera de alcance).

## Interface
```python
def main(argv, stdout, run_all_fn=None) -> int:
    """Despacha el CLI.

    ``argv``: lista de argumentos SIN el nombre del programa.
    ``stdout``: stream con ``.write(str)`` (``sys.stdout`` en produccion).
    ``run_all_fn``: callable ``fn(repo_root='.') -> {'overall_ok': bool,
      'results': {...}}`` inyectable para tests; si es ``None`` se usa
      ``mcp_gate_dispatch.run_all_level1``.

    - ``argv == ['gates', 'run-all', '--json']``: ejecuta ``fn(repo_root='.')``,
      escribe ``json.dumps(result)`` (una linea, sin pretty-print) en
      ``stdout``, devuelve ``0`` si ``result['overall_ok']`` es ``True`` si
      no ``1``.
    - cualquier otro ``argv``: escribe un mensaje de uso de UNA linea que
      empieza con ``usage:`` en ``stdout``, devuelve ``2``. ``fn`` NUNCA se
      llama.
    - nunca lanza una excepcion no controlada por un ``argv`` malformado.
    """
```

## Invariants
- ``fn`` NUNCA se invoca si ``argv`` no es exactamente
  ``['gates', 'run-all', '--json']`` (cero side effects para argv invalido:
  ni gates corridos, ni subprocess, ni red).
- Para el argv valido, el exit code coincide con ``result['overall_ok']``:
  ``0`` si es ``True``, ``1`` si no.
- La salida del argv valido es EXACTAMENTE ``json.dumps(result)``: una sola
  linea, sin pretty-print, sin newline añadido.
- Para argv invalido, lo escrito en ``stdout`` empieza siempre con
  ``usage:`` y ocupa una sola linea; el exit code es siempre ``2``.
- ``main`` nunca lanza por un ``argv`` malformado (lista vacia, strings
  raros, etc.): el unico parseo es una comparacion de igualdad de listas.

## Examples
- ``main(['gates','run-all','--json'], out, run_all_fn=lambda r={'overall_ok':True,...})`` -> escribe ese JSON, devuelve ``0``.
- ``main(['gates','run-all','--json'], out, run_all_fn=lambda r={'overall_ok':False,...})`` -> escribe ese JSON, devuelve ``1``.
- ``main([], out)`` -> escribe ``usage: ...``, devuelve ``2``; ``fn`` no se llama.
- ``main(['gates','run-all','--json','extra'], out)`` -> escribe ``usage: ...``, devuelve ``2`` (superset no matchea).
- ``main(['--help'], out)`` -> escribe ``usage: ...``, devuelve ``2``.

## Do / Don't
- DO: importar ``mcp_gate_dispatch`` como modulo hermano, mismo patron que
  ``scripts/validate_rules.py`` importa ``rule_engine`` (mismo directorio).
- DO: resolver ``fn = run_all_fn if run_all_fn is not None else
  mcp_gate_dispatch.run_all_level1`` (lookup del atributo en cada llamada,
  para que monkeypatch en tests funcione).
- DO: usar ``json.dumps(result)`` sin ``indent`` (una linea).
- DON'T: incluir ``subprocess`` en ``forbids`` de este contrato -- el target
  SI importa ``mcp_gate_dispatch`` que usa subprocess internamente (ver
  [mcp-gate-dispatch](./mcp-gate-dispatch.md)); ``forbids`` es
  ``['network','llm']`` unicamente.
- DON'T: implementar mas subcomandos, ni paquete instalable, ni entry_point.
- DON'T: tocar ``scripts/mcp_gate_dispatch.py`` ni ningun archivo fuera de
  ``touch_only``.

## Tests
(Los tests estan en `tests/test_kdd_cli.py`, oraculo congelado sellado por
`tests_sha256`: el implementador no los escribe ni los modifica. Inyectan
siempre un `run_all_fn` fake (lambda que devuelve un dict literal) para el
caso `--json`; el caso `run_all_fn=None` se ejercita monkeypatcheando
`mcp_gate_dispatch` con un fake; los casos de argv invalido asertan exit 2,
mensaje `usage:` y que el fake NUNCA se llama. Sin subprocess real ni red.)

## Constraints
- PARAR y reportar si necesitas conectarte a la red o invocar un LLM.
- PARAR y reportar si el `intent` exige tocar un archivo fuera de
  `touch_only` (probablemente signifique que la spec esta mal escrita).