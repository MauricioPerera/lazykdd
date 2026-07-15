---
type: 'Task Contract'
title: 'CLI: contracts scaffold <task> --json'
description: 'Extiende el CLI Python (Piel 2) de lazykdd con un tercer subcomando `contracts scaffold <task> --json` que crea un contrato nuevo a partir de la plantilla.'
tags: ['ccdd', 'cli', 'lazykdd', 'contracts', 'scaffold']

task: kdd-contracts-scaffold-json
intent: "Crear un contrato nuevo en `knowledge/contracts/<task>.md` a partir de la plantilla al despachar `contracts scaffold <task> --json`."
target: scripts/kdd_cli.py
signature: "def main(argv, stdout, run_all_fn=None, list_contracts_fn=None, scaffold_fn=None) -> int:"
test_command: "python -m unittest tests/test_kdd_cli.py"
test_cwd: ../..
budget:
  cyclomatic_max: 16
  nesting_max: 4
  params_max: 5
  lines_max: 68
tests: "tests/test_kdd_cli.py"
tests_sha256: "0bafcc414fbcc772724d3d64161cafdfddb31c9069f553cf8673458d765fa6d1"
touch_only: ['scripts/kdd_cli.py']
deps_allowed: []
forbids: ['network', 'llm']
---

# Contract: CLI `contracts scaffold <task> --json`

## Intent
Tercera pieza de la Piel 2 (CLI Python) del proyecto lazykdd: extender la
funcion `main` de `scripts/kdd_cli.py` con un tercer subcomando,
`contracts scaffold <task> --json`, que crea un nuevo archivo de contrato
en `knowledge/contracts/<task>.md` a partir de
`TEMPLATE-task-contract.md`, reemplazando el placeholder `task:` por el
nombre real y eliminando el bloque final de instrucciones humanas. NO
toca el comportamiento existente de `gates run-all --json`
([kdd-gates-run-all-json](./kdd-gates-run-all-json.md)) ni de
`contracts list --json`
([kdd-contracts-list-json](./kdd-contracts-list-json.md)).

## Interface
```python
def main(argv, stdout, run_all_fn=None, list_contracts_fn=None,
         scaffold_fn=None) -> int:
    """Despacha el CLI.

    ``argv``: lista de argumentos SIN el nombre del programa.
    ``scaffold_fn``: callable ``fn(task_name) -> {'created': True, ...} |
      {'error': ...}`` inyectable para tests; si es ``None`` se resuelve a
      ``scaffold_contract`` (mismo modulo, lookup del atributo en cada
      llamada).

    - ``['gates', 'run-all', '--json']`` y ``['contracts', 'list',
      '--json']``: comportamiento existente (sin cambios).
    - ``['contracts', 'scaffold', <task_name>, '--json']`` (4 elementos
      exactos): ``fn = scaffold_fn if scaffold_fn is not None else
      scaffold_contract``; ``result = fn(argv[2])``. Si ``result`` tiene
      ``'created': True`` escribe ``json.dumps(result)`` y devuelve ``0``;
      si tiene clave ``'error'`` escribe ``json.dumps(result)`` y devuelve
      ``1``.
    - cualquier otro ``argv``: mensaje de uso de UNA linea que empieza con
      ``usage:`` y menciona los TRES subcomandos, devuelve ``2``. Ningun
      ``fn`` se llama.
    """
```

```python
def scaffold_contract(task_name, contracts_dir='knowledge/contracts',
                      template_path='knowledge/contracts/TEMPLATE-task-contract.md') -> dict:
    """Crea un contrato nuevo a partir de la plantilla.

    - Valida ``task_name`` contra kebab-case estricto
      ``^[a-z0-9]+(-[a-z0-9]+)*$``; si no matchea devuelve
      ``{'error': 'invalid task name (must be kebab-case): ' + task_name}``
      SIN tocar el filesystem.
    - ``target_path = os.path.join(contracts_dir, task_name + '.md')``; si
      ya existe devuelve ``{'error': 'contract already exists: ' +
      target_path}`` (nunca sobreescribe).
    - si ``template_path`` no existe devuelve ``{'error': 'template not
      found: ' + template_path}``.
    - reemplaza la linea ``task: <nombre-kebab-case>`` por ``task:
      <task_name>`` y elimina el bloque final de instrucciones humanas
      (la linea ``---`` que precede a ``<!--`` y todo el comentario HTML
      hasta ``-->``); los demas placeholders ``<...>`` quedan intactos.
      Escribe en ``target_path`` y devuelve ``{'created': True, 'path':
      target_path}``.
    """
```

## Invariants
- ``scaffold_fn`` NUNCA se invoca si ``argv`` no es exactamente
  ``['contracts', 'scaffold', <str>, '--json']`` (4 elementos, ``argv[0]
  == 'contracts'``, ``argv[1] == 'scaffold'``, ``argv[3] == '--json'``,
  ``argv[2]`` un string): cero side effects para argv invalido (ni
  lectura de template, ni escritura, ni red).
- ``scaffold_contract`` valida el nombre kebab ANTES de tocar el
  filesystem: un nombre invalido no lee el template ni crea archivo.
- ``scaffold_contract`` nunca sobreescribe un archivo existente: si
  ``target_path`` existe devuelve error sin abrirlo para escritura.
- El contenido escrito termina justo despues de la seccion ``##
  Constraints`` (un unico salto de linea final) y NO contiene el
  comentario HTML ``<!-- ... -->`` ni el ``---`` que lo precedia.
- La linea ``task: <nombre-kebab-case>`` del frontmatter queda reemplazada
  por ``task: <task_name>``; los demas placeholders ``<...>`` quedan
  intactos.
- La salida de exito es EXACTAMENTE ``json.dumps(result)``: una sola
  linea, sin pretty-print, sin newline añadido. Exit ``0`` si
  ``'created' is True``, ``1`` si hay ``'error'``.
- Para argv invalido, lo escrito empieza con ``usage:`` y menciona los
  TRES subcomandos; el exit code es siempre ``2``.
- ``main`` nunca lanza por un ``argv`` malformado (incluido un
  ``argv[2]`` no string, que cae al usage en vez de llamarse ``fn``).

## Examples
- ``main(['contracts','scaffold','my-task','--json'], out, scaffold_fn=lambda t={'created':True,'path':'knowledge/contracts/my-task.md'})`` -> escribe ese JSON, devuelve ``0``.
- ``main(['contracts','scaffold','Bad','--json'], out, scaffold_fn=lambda t={'error':'invalid task name (must be kebab-case): Bad'})`` -> escribe ese JSON, devuelve ``1``.
- ``scaffold_contract('my-task', contracts_dir=tmp, template_path=tmp_tmpl)`` -> ``{'created': True, 'path': tmp/my-task.md}`` y el archivo existe; su texto tiene ``task: my-task`` y no contiene ``<!--``.
- ``scaffold_contract('Bad_Name')`` -> ``{'error': 'invalid task name (must be kebab-case): Bad_Name'}`` sin tocar el filesystem.
- ``scaffold_contract('dup')`` cuando ``dup.md`` ya existe -> ``{'error': 'contract already exists: ...'}`` sin sobreescribir.
- ``main(['contracts','scaffold','--json','x'], out)`` -> escribe ``usage: ...``, devuelve ``2``; ``scaffold_fn`` no se llama.

## Do / Don't
- DO: resolver ``fn = scaffold_fn if scaffold_fn is not None else
  scaffold_contract`` (lookup del atributo en cada llamada, para que
  monkeypatch en tests funcione).
- DO: aislar el bloque de instrucciones humanas localizando la linea
  ``<!--`` y caminando hacia atras hasta el ``---`` que la precede (no
  asumas offsets fijos: el template puede cambiar).
- DO: validar kebab-case con ``re.fullmatch(r'^[a-z0-9]+(-[a-z0-9]+)*$',
  task_name)`` antes de cualquier operacion de filesystem.
- DO: preservar el comportamiento de ``['gates','run-all','--json']`` y
  ``['contracts','list','--json']`` exactamente como estaban.
- DON'T: incluir ``subprocess`` en ``forbids`` -- el target importa
  ``mcp_gate_dispatch`` que usa subprocess internamente; ``forbids`` es
  ``['network','llm']`` unicamente.
- DON'T: tocar ``TEMPLATE-task-contract.md``, ``scripts/validate_contracts.py``,
  ``scripts/mcp_gate_dispatch.py`` ni nada fuera de ``touch_only`` (salvo
  re-sellar ``tests_sha256`` de los contratos viejos por el oraculo
  compartido, ya autorizado).
- DON'T: implementar mas subcomandos, ni flags adicionales, ni pedir
  confirmacion al usuario (un solo write, sin prompts). No valides
  colision con ``TEMPLATE-*.md`` (no es kebab-case puro).

## Tests
(Los tests estan en `tests/test_kdd_cli.py`, oraculo congelado sellado por
`tests_sha256`: el implementador no los escribe ni los modifica. Preservan
los 44 casos originales de `gates run-all --json` y `contracts list
--json` y agregan los de `contracts scaffold`: el despacho via `main`
inyecta siempre un `scaffold_fn` fake (lambda que devuelve un dict
literal), salvo UN test dedicado que verifica el default real contra un
tempdir (chdir, nunca contra el repo); los tests de `scaffold_contract`
directo usan siempre `tempfile.mkdtemp()` para `contracts_dir`/`template_path`
(una copia del template real dentro del tempdir). Los casos de argv
invalido asertan exit 2, mensaje `usage:` que menciona los TRES
subcomandos, y que ningun fake se llama. Sin subprocess real, red ni
filesystem real del repo dentro de un test.)

## Constraints
- PARAR y reportar si necesitas conectarte a la red o invocar un LLM.
- PARAR y reportar si el `intent` exige tocar un archivo fuera de
  `touch_only` (mas alla del re-sellado de `tests_sha256` ya autorizado
  para los contratos viejos por el oraculo compartido).
- PARAR y reportar si el bloque de instrucciones humanas del template no
  se puede aislar de forma confiable (formato cambio, no hay separador
  claro) -- no improvises un recorte aproximado.