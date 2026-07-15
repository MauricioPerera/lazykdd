---
type: 'Task Contract'
title: 'CLI: contracts status --json'
description: 'Extiende el CLI Python (Piel 2) de lazykdd con un cuarto subcomando `contracts status --json` que emite la etapa de ciclo de vida de cada contrato.'
tags: ['ccdd', 'cli', 'lazykdd', 'contracts', 'status']

task: kdd-contracts-status-json
intent: "Emitir la etapa de ciclo de vida de cada contrato como una linea de JSON al despachar `contracts status --json`."
target: scripts/kdd_cli.py
signature: "def main(argv, stdout, run_all_fn=None, list_contracts_fn=None, scaffold_fn=None, status_fn=None) -> int:"
test_command: "python -m unittest tests/test_kdd_cli.py"
test_cwd: ../..
budget:
  cyclomatic_max: 17
  nesting_max: 3
tests: "tests/test_kdd_cli.py"
tests_sha256: "0bafcc414fbcc772724d3d64161cafdfddb31c9069f553cf8673458d765fa6d1"
touch_only: ['scripts/kdd_cli.py']
deps_allowed: []
forbids: ['network', 'llm']
---

# Contract: CLI `contracts status --json`

## Intent
Cuarta pieza de la Piel 2 (CLI Python) del proyecto lazykdd: extender la
funcion `main` de `scripts/kdd_cli.py` con un cuarto subcomando,
`contracts status --json`, que devuelve la etapa de ciclo de vida
(``draft`` < ``validated`` < ``implemented`` < ``verified``) de CADA
contrato real del repo. Reusa ``scripts/validate_contracts.py``
(``_collect_files``, ``parse_frontmatter``, ``validate_file``) y
``scripts/validate_test_commands.py`` (``run_all``) como modulos hermanos.
NO toca el comportamiento existente de ``gates run-all --json``
([kdd-gates-run-all-json](./kdd-gates-run-all-json.md)), ``contracts list
--json`` ([kdd-contracts-list-json](./kdd-contracts-list-json.md)) ni
``contracts scaffold <task> --json``
([kdd-contracts-scaffold-json](./kdd-contracts-scaffold-json.md)).

## Interface
```python
def main(argv, stdout, run_all_fn=None, list_contracts_fn=None,
         scaffold_fn=None, status_fn=None) -> int:
    """Despacha el CLI.

    ``status_fn``: callable ``fn() -> list[dict] | {'error': ...}`` inyectable
    para tests; si es ``None`` se resuelve a ``list_contract_status`` (mismo
    modulo, lookup del atributo en cada llamada).

    - ``['gates', 'run-all', '--json']``, ``['contracts', 'list', '--json']``
      y ``['contracts', 'scaffold', <task>, '--json']``: comportamiento
      existente (sin cambios).
    - ``['contracts', 'status', '--json']`` (3 elementos exactos):
      ``fn = status_fn if status_fn is not None else list_contract_status``;
      ``result = fn()``. Si ``result`` es una lista (incluida vacia) escribe
      ``json.dumps(result)`` y devuelve ``0``; si es un dict con clave
      ``'error'`` escribe ``json.dumps(result)`` y devuelve ``1``.
    - cualquier otro ``argv``: mensaje de uso de UNA linea que empieza con
      ``usage:`` y menciona los CUATRO subcomandos, devuelve ``2``. Ningun
      ``fn`` se llama.
    """
```

```python
def list_contract_status(contracts_dir='knowledge/contracts',
                         repo_root='.') -> list[dict] | dict:
    """Etapa de ciclo de vida de cada contrato.

    - ``validate_contracts._collect_files(contracts_dir)`` da los ``*.md``
      (excluye ``TEMPLATE-*.md``, orden alfabetico). Si devuelve ``None``
      (dir inexistente) -> ``{'error': 'contracts dir not found: ' +
      contracts_dir}``.
    - Corre ``validate_test_commands.run_all(contracts_dir, repo_root)`` UNA
      vez y arma ``{path: item}`` para lookup O(1).
    - Por cada archivo (mismo orden que ``_collect_files``):
      1. ``fm, _ = parse_frontmatter(text)``; ``task = fm.get('task', '') if
         fm else ''``.
      2. ``findings = validate_file(path, repo_root=repo_root)``;
         ``validated = not any(f.level == 'ERROR' for f in findings)``.
      3. ``implemented = validated and (path en run_all) and
         item['ok'] is True``.
      4. ``verified = implemented and task and os.path.isfile(
         .agents/logs/<task>-REPORT.md bajo repo_root)``.
      5. Etapa mas alta que cumple; agrega ``{'task': task, 'lifecycle':
         <etapa>}``.
    - Devuelve la lista (puede quedar vacia si no hay contratos).
    """
```

## Invariants
- ``status_fn`` NUNCA se invoca si ``argv`` no es exactamente
  ``['contracts', 'status', '--json']`` (3 elementos): cero side effects
  para argv invalido (ni lectura de disco, ni subprocess, ni red).
- ``run_all`` se invoca UNA sola vez por llamada (no por contrato): se
  reusa su resultado via un dict ``{path: item}``.
- Un contrato ausente de ``run_all`` (p. ej. ``test_command`` vacio/ausente)
  NUNCA es ``implemented`` (``item is None`` -> ``implemented`` False).
- ``verified`` exige ``implemented`` AND ``task`` no vacio AND existencia de
  ``.agents/logs/<task>-REPORT.md``; NO valida el envelope de atestacion
  opcional (solo existencia del archivo, per
  [validacion.md](../validacion.md) seccion "Ciclo de vida del contrato").
- La etapa es la MAS ALTA que cumple, en orden ``verified`` > ``implemented``
  > ``validated`` > ``draft``.
- Cada elemento del resultado de exito tiene EXACTAMENTE las claves ``task``
  y ``lifecycle`` (``task`` es ``''`` si el contrato no tiene frontmatter
  valido; ``lifecycle`` es uno de ``draft``/``validated``/``implemented``/
  ``verified``).
- La salida de exito es EXACTAMENTE ``json.dumps(result)``: una sola linea,
  sin pretty-print, sin newline añadido. Exit ``0`` para lista (incluida
  vacia), ``1`` para dict con ``'error'``.
- Para argv invalido, lo escrito empieza con ``usage:`` y menciona los
  CUATRO subcomandos; el exit code es siempre ``2``.
- ``main`` nunca lanza por un ``argv`` malformado: el unico parseo es una
  comparacion de igualdad de listas.

## Examples
- ``main(['contracts','status','--json'], out, status_fn=lambda=[{'task':'a','lifecycle':'draft'}])`` -> escribe ese JSON, devuelve ``0``.
- ``main(['contracts','status','--json'], out, status_fn=lambda=[])`` -> escribe ``[]``, devuelve ``0`` (lista vacia es exito).
- ``main(['contracts','status','--json'], out, status_fn=lambda={'error':'contracts dir not found: knowledge/contracts'})`` -> escribe ese JSON, devuelve ``1``.
- ``list_contract_status(contracts_dir=tmp/contracts, repo_root=tmp)`` sobre un contrato valido con ``test_command`` exit 0 y ``.agents/logs/<task>-REPORT.md`` presente -> ``[{'task':<task>,'lifecycle':'verified'}]``.
- ``list_contract_status('nonexistent')`` -> ``{'error': 'contracts dir not found: nonexistent'}``.
- ``main(['contracts','status'], out)`` -> escribe ``usage: ...`` mencionando los CUATRO subcomandos, devuelve ``2``; ``status_fn`` no se llama.

## Do / Don't
- DO: importar ``validate_test_commands`` como modulo hermano, mismo patron
  que ``mcp_gate_dispatch``/``validate_contracts`` ya usados en este archivo.
- DO: resolver ``fn = status_fn if status_fn is not None else
  list_contract_status`` (lookup del atributo en cada llamada, para que
  monkeypatch en tests funcione).
- DO: armar ``by_path = {item['path']: item for item in run_results}`` y
  hacer lookup O(1) por path (el path de ``run_all`` y el de
  ``_collect_files`` coinciden porque ambos hacen ``os.path.join(contracts_dir,
  name)`` sobre el mismo ``contracts_dir``).
- DO: preservar el comportamiento de los TRES subcomandos existentes
  exactamente como estaban (los 73 tests originales siguen describiendo lo
  mismo).
- DON'T: incluir ``subprocess`` en ``forbids`` -- el target importa
  ``mcp_gate_dispatch`` (y ahora ``validate_test_commands``) que usan
  subprocess internamente; ``forbids`` es ``['network','llm']`` unicamente.
- DON'T: validar el envelope de atestacion opcional -- solo la existencia de
  ``.agents/logs/<task>-REPORT.md`` alcanza para ``verified``.
- DON'T: agregar flags de filtrado, un modo "un solo contrato", ni paginacion.
- DON'T: tocar ``validate_contracts.py``, ``validate_test_commands.py``,
  ``mcp_gate_dispatch.py`` ni nada fuera de ``touch_only`` (salvo re-sellar
  ``tests_sha256`` de los contratos viejos por el oraculo compartido, ya
  autorizado).

## Tests
(Los tests estan en `tests/test_kdd_cli.py`, oraculo congelado sellado por
`tests_sha256`: el implementador no los escribe ni los modifica. Preservan
los 73 casos originales de los TRES subcomandos previos y agregan los de
`contracts status`: el despacho via `main` inyecta siempre un `status_fn`
fake (lambda que devuelve una lista literal o un dict de error literal); el
caso `status_fn=None` se ejercita monkeypatcheando
`kdd_cli.list_contract_status` con un fake. Los tests de
`list_contract_status` directo usan SIEMPRE un `tempfile.mkdtemp()` con
contratos sinteticos, `test_command` fake tipo `python -c "import sys;
sys.exit(0/1)"` y un `.agents/logs/` sintetico dentro del mismo tempdir --
NUNCA contra `knowledge/contracts/` real. Un UNICO test dedicado verifica
el default real via `main` chdir-eando a un tempdir, asertando solo
estructura (lista no vacia, claves `task`/`lifecycle`, `lifecycle` en el
conjunto permitido), nunca valores exactos del repo real. Sin subprocess
contra el repo real, red ni filesystem real del repo dentro de un test.)

## Constraints
- PARAR y reportar si necesitas conectarte a la red o invocar un LLM.
- PARAR y reportar si el `intent` exige tocar un archivo fuera de
  `touch_only` (mas alla del re-sellado de `tests_sha256` ya autorizado
  para los contratos viejos por el oraculo compartido).
- PARAR y reportar si `main` extendida supera el tope global firmado en una
  dimension que NO se puede omitir sin invalidar el gate por completo.

## Budget note
`lines_max` y `params_max` se omiten a propósito:
- ``main`` real mide ``function_length = 82`` (la metrica cuenta las lineas
  del docstring, que es largo porque documenta los CUATRO subcomandos), por
  encima del tope global firmado de 80 -> se omite ``lines_max``.
- ``main`` real mide ``parameter_count = 6`` (la firma mandate seis
  parametros: ``argv``, ``stdout``, ``run_all_fn``, ``list_contracts_fn``,
  ``scaffold_fn``, ``status_fn``), por encima del tope global firmado de 5
  -> se omite ``params_max``. No se puede reducir sin romper la firma
  exigida por esta tarea.
Omitir esas claves puntuales ya ocurrio antes en este repo y no es bloqueo;
el resto del budget (``cyclomatic_max=17``, ``nesting_max=3``) refleja lo
medido real y esta bajo los topes globales (20 y 4).