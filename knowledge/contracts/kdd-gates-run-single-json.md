---
type: 'Task Contract'
title: 'CLI: gates run <name> --json'
description: 'Extiende el CLI Python (Piel 2) de lazykdd con un quinto subcomando `gates run <name> --json` que corre UN gate especifico via mcp_gate_dispatch.run_gate y emite su JSON, refactorizando main a un dispatcher delgado.'
tags: ['ccdd', 'cli', 'lazykdd', 'gate']

task: kdd-gates-run-single-json
intent: "Correr un gate especifico via el subcomando `gates run <name> --json`."
target: scripts/kdd_cli.py
signature: "def main(argv, stdout, run_all_fn=None, list_contracts_fn=None, scaffold_fn=None, status_fn=None, run_gate_fn=None) -> int:"
test_command: "python -m unittest tests/test_kdd_cli.py"
test_cwd: ../..
budget:
  cyclomatic_max: 14
  nesting_max: 2
  lines_max: 45
tests: "tests/test_kdd_cli.py"
tests_sha256: "db8dfc1d5c1d99ef23784174f14f03f500de7e0e0a7c16fbcb9456af32750236"
touch_only: ['scripts/kdd_cli.py']
deps_allowed: []
forbids: ['network', 'llm']
---

# Contract: CLI `gates run <name> --json`

## Intent
Quinta pieza de la Piel 2 (CLI Python) del proyecto lazykdd: extender la
funcion `main` de `scripts/kdd_cli.py` con un quinto subcomando,
`gates run <name> --json`, que corre UN gate especifico (no los 11 juntos)
via `mcp_gate_dispatch.run_gate` y emite su resultado como una linea de
JSON. Exige refactorizar `main` a un DISPATCHER delgado (un type-check
corto por `argv`, cada rama UNA linea de delegacion a un handler
`_handle_*` separado) porque `main` ya estaba en `cyclomatic` 17, muy
cerca del tope global firmado 20, y un quinto subcomando inline lo
excederia. NO toca el comportamiento existente de `gates run-all --json`
([kdd-gates-run-all-json](./kdd-gates-run-all-json.md)), `contracts list
--json` ([kdd-contracts-list-json](./kdd-contracts-list-json.md)),
`contracts scaffold <task> --json`
([kdd-contracts-scaffold-json](./kdd-contracts-scaffold-json.md)) ni
`contracts status --json`
([kdd-contracts-status-json](./kdd-contracts-status-json.md)).

## Interface
```python
def main(argv, stdout, run_all_fn=None, list_contracts_fn=None,
         scaffold_fn=None, status_fn=None, run_gate_fn=None) -> int:
    """Despacha el CLI (dispatcher delgado).

    ``run_gate_fn``: callable ``fn(gate_name, repo_root='.') -> dict``
    inyectable para tests; si es ``None`` se resuelve a
    ``run_single_gate_json`` (mismo modulo, lookup del atributo en cada
    llamada).

    - Los CUATRO subcomandos previos: comportamiento existente (sin
      cambios), ahora movido a handlers ``_handle_*``.
    - ``['gates', 'run', <gate_name>, '--json']`` (4 elementos exactos:
      ``argv[0]=='gates'``, ``argv[1]=='run'``, ``argv[3]=='--json'``,
      ``argv[2]`` un string): ``fn = run_gate_fn if run_gate_fn is not
      None else run_single_gate_json``; ``result = fn(argv[2],
      repo_root='.')``. Si ``result`` tiene clave ``'error'`` escribe
      ``json.dumps(result)`` y devuelve ``1``; si no, escribe
      ``json.dumps(result)`` y devuelve ``0`` si
      ``result['exit_code'] == 0``, si no ``1``.
    - cualquier otro ``argv``: mensaje de uso de UNA linea que empieza con
      ``usage:`` y menciona los CINCO subcomandos, devuelve ``2``. Ningun
      ``fn`` se llama.
    """
```

```python
def run_single_gate_json(gate_name, repo_root='.') -> dict:
    """Corre UN gate especifico via ``mcp_gate_dispatch.run_gate``.

    Devuelve ``{'error': 'unknown gate: ' + gate_name}`` si ``gate_name``
    NO esta en ``mcp_gate_dispatch.LEVEL1_GATES`` (nombre invalido O es
    ``'validate_attestation'``, que es local-only y esta deliberadamente
    excluido de ``LEVEL1_GATES`` -- mismo criterio que ``gates run-all``).
    Si es valido, devuelve ``mcp_gate_dispatch.run_gate(gate_name, {},
    repo_root=repo_root)`` tal cual (ese dict YA tiene ``'exit_code'``/
    ``'stdout'``/``'stderr'``).
    """
```

## Invariants
- ``run_gate_fn`` NUNCA se invoca si ``argv`` no es exactamente
  ``['gates', 'run', <str>, '--json']`` (4 elementos, ``argv[0]=='gates'``,
  ``argv[1]=='run'``, ``argv[3]=='--json'``, ``argv[2]`` un string): cero
  side effects para argv invalido (ni gate corrido, ni subprocess, ni red).
- Para el argv valido, ``run_gate_fn`` SIEMPRE se llama (a diferencia de
  ``list``/``scaffold``/``status``, donde el error viene DE la llamada
  misma): es ``fn`` (o el default ``run_single_gate_json``) la que decide
  si el nombre de gate es invalido y arma el dict de error.
- ``run_single_gate_json`` devuelve ``{'error': 'unknown gate: ' +
  gate_name}`` SIN llamar a ``mcp_gate_dispatch.run_gate`` cuando
  ``gate_name`` no es miembro de ``LEVEL1_GATES`` (incluido
  ``'validate_attestation'``).
- ``run_single_gate_json`` para un gate valido devuelve el dict de
  ``mcp_gate_dispatch.run_gate(gate_name, {}, repo_root=repo_root)`` tal
  cual, sin transformarlo.
- Exit code del argv valido: ``1`` si ``result`` tiene ``'error'``; si no,
  ``0`` si ``result['exit_code'] == 0`` si no ``1`` (un ``exit_code``
  ``None`` -- timeout -- cuenta como ``1``).
- La salida del argv valido es EXACTAMENTE ``json.dumps(result)``: una
  sola linea, sin pretty-print, sin newline añadido.
- Para argv invalido, lo escrito empieza con ``usage:`` y menciona los
  CINCO subcomandos (``gates run-all --json``, ``gates run <name> --json``,
  ``contracts list --json``, ``contracts scaffold <task> --json``,
  ``contracts status --json``); el exit code es siempre ``2``.
- ``main`` es un dispatcher delgado: cada rama es UNA linea de delegacion
  a un handler ``_handle_*``; la logica real (resolucion de ``fn``,
  llamada, formato del JSON, exit code) vive en los handlers, no inline.
- ``main`` nunca lanza por un ``argv`` malformado (incluido un ``argv[2]``
  no string, que cae al usage en vez de llamarse ``fn``): el unico parseo
  es igualdad de listas / largo + posiciones + tipo.

## Examples
- ``main(['gates','run','validate_contracts','--json'], out, run_gate_fn=lambda g,r={'exit_code':0,'stdout':'','stderr':''})`` -> escribe ese JSON, devuelve ``0``.
- ``main(['gates','run','validate_contracts','--json'], out, run_gate_fn=lambda g,r={'exit_code':1,'stdout':'','stderr':'boom'})`` -> escribe ese JSON, devuelve ``1``.
- ``main(['gates','run','does-not-exist','--json'], out, run_gate_fn=lambda g,r={'error':'unknown gate: does-not-exist'})`` -> escribe ese JSON, devuelve ``1``.
- ``run_single_gate_json('does-not-exist')`` -> ``{'error': 'unknown gate: does-not-exist'}`` sin llamar a ``mcp_gate_dispatch.run_gate``.
- ``run_single_gate_json('validate_attestation')`` -> ``{'error': 'unknown gate: validate_attestation'}`` (local-only, mismo camino que un nombre inventado).
- ``main(['gates','run'], out)`` -> escribe ``usage: ...`` mencionando los CINCO subcomandos, devuelve ``2``; ``run_gate_fn`` no se llama.
- ``main(['gates','run','x','--yaml'], out)`` -> escribe ``usage: ...``, devuelve ``2``; ``run_gate_fn`` no se llama.

## Do / Don't
- DO: refactorizar ``main`` a dispatcher delgado con un handler
  ``_handle_*`` por subcomando (incluidos los CUATRO previos): ``main``
  hace solo el match de ``argv`` y delega, toda la logica real vive en los
  handlers. Este refactor es REQUISITO, no opcional (presupuesto).
- DO: resolver ``fn = run_gate_fn if run_gate_fn is not None else
  run_single_gate_json`` (lookup del atributo en cada llamada, para que
  monkeypatch en tests funcione).
- DO: preservar el comportamiento de los CUATRO subcomandos existentes
  EXACTAMENTE (mismos mensajes, mismos exit codes, misma logica de
  resolucion ``fn is not None``), solo movido a handlers.
- DO: que ``run_single_gate_json`` valide membresia en
  ``mcp_gate_dispatch.LEVEL1_GATES`` ANTES de llamar a ``run_gate`` (un
  nombre invalido no dispara subprocess).
- DON'T: incluir ``subprocess`` en ``forbids`` -- el target importa
  ``mcp_gate_dispatch`` que usa subprocess internamente; ``forbids`` es
  ``['network','llm']`` unicamente.
- DON'T: tocar ``scripts/mcp_gate_dispatch.py`` ni nada fuera de
  ``touch_only`` (salvo re-sellar ``tests_sha256`` de los contratos viejos
  por el oraculo compartido, ya autorizado).
- DON'T: agregar flags adicionales (``--all``, listado de gates
  disponibles), ni validacion de nombre de gate en Go/TUI (esta tarea es
  SOLO el CLI Python).

## Tests
(Los tests estan en `tests/test_kdd_cli.py`, oraculo congelado sellado por
`tests_sha256`: el implementador no los escribe ni los modifica. Preservan
los 101 casos originales de los CUATRO subcomandos previos y agregan los
de `gates run <name> --json`: el despacho via `main` inyecta siempre un
`run_gate_fn` fake (`_run_gate_fn`, lambda que devuelve un dict literal
`{'exit_code',...}` o `{'error',...}`); el caso `run_gate_fn=None` se
ejercita monkeypatcheando `mcp_gate_dispatch.run_gate` con un fake que
devuelve un literal (sin subprocess real). Los tests de
`run_single_gate_json` directo verifican que un nombre invalido (y
`'validate_attestation'`) devuelven `{'error': 'unknown gate: ' + name}`
SIN llamar a `mcp_gate_dispatch.run_gate` (fake con contador), y que un
nombre valido delega con `params={}`. Los casos de argv invalido asertan
exit 2, mensaje `usage:` que menciona los CINCO subcomandos, y que
`run_gate_fn` nunca se llama. Sin subprocess real contra el repo, red ni
filesystem real del repo dentro de un test.)

## Constraints
- PARAR y reportar si necesitas conectarte a la red o invocar un LLM.
- PARAR y reportar si el `intent` exige tocar un archivo fuera de
  `touch_only` (mas alla del re-sellado de `tests_sha256` ya autorizado
  para los contratos viejos por el oraculo compartido).
- PARAR y reportar si refactorizar `main` a dispatcher sin romper ninguno
  de los 101 tests viejos resulta imposible (deberia ser posible: es una
  decision de estructura interna, no de comportamiento externo).
- PARAR y reportar si el budget no se cumple sin violar la interfaz.

## Budget note
`params_max` se omite a proposito: ``main`` real mide
``parameter_count = 7`` (la firma mandate siete parametros: ``argv``,
``stdout``, ``run_all_fn``, ``list_contracts_fn``, ``scaffold_fn``,
``status_fn``, ``run_gate_fn``), por encima del tope global firmado de 5
-> se omite ``params_max``. No se puede reducir sin romper la firma
exigida por esta tarea (un inyectable ``*_fn`` por subcomando).
Omitir esa clave puntual ya ocurrio antes en este repo
([kdd-contracts-status-json](./kdd-contracts-status-json.md), que omite
``lines_max`` y ``params_max``) y no es bloqueo.

El refactor a dispatcher es el punto de esta tarea: ``main`` real mide
``cyclomatic = 14`` (era 17 pre-refactor con cuatro subcomandos inline;
cinco inline la hubiesen llevado >20) y ``nesting = 1``, ambos bajo los
topes globales (20 y 4). ``function_length`` queda bajo ``lines_max=45``
(el docstring es corto: el dispatcher no documenta cada subcomando, solo
el contrato de despacho). Los handlers ``_handle_*`` son helpers sin
contrato propio, mismo criterio ya usado en este repo.