---
type: 'Task Contract'
title: 'CLI: contracts list --json'
description: 'Extiende el CLI Python (Piel 2) de lazykdd con un segundo subcomando `contracts list --json` que lista el frontmatter de los contratos como JSON.'
tags: ['ccdd', 'cli', 'lazykdd', 'contracts']

task: kdd-contracts-list-json
intent: "Emitir el frontmatter de los contratos como una linea de JSON al despachar el subcomando `contracts list --json`."
target: scripts/kdd_cli.py
signature: "def main(argv, stdout, run_all_fn=None, list_contracts_fn=None) -> int:"
test_command: "python -m unittest tests/test_kdd_cli.py"
test_cwd: ../..
budget:
  cyclomatic_max: 8
  nesting_max: 3
  params_max: 4
  lines_max: 50
tests: "tests/test_kdd_cli.py"
tests_sha256: "4bc9f54303e665627c0a6d0c449d63382d7da22e6a72f6720796ca9020d57355"
touch_only: ['scripts/kdd_cli.py']
deps_allowed: []
forbids: ['network', 'llm']
---

# Contract: CLI `contracts list --json`

## Intent
Segunda pieza de la Piel 2 (CLI Python) del proyecto lazykdd: extender la
funcion `main` de `scripts/kdd_cli.py` con un segundo subcomando,
`contracts list --json`, que lista el frontmatter de los contratos de un
directorio como una linea de JSON en stdout. Reusa el parser de
`scripts/validate_contracts.py` (`_collect_files` + `parse_frontmatter`,
modulos hermanos) y NO toca el comportamiento existente de
`gates run-all --json` ([kdd-gates-run-all-json](./kdd-gates-run-all-json.md)).

## Interface
```python
def main(argv, stdout, run_all_fn=None, list_contracts_fn=None) -> int:
    """Despacha el CLI.

    ``argv``: lista de argumentos SIN el nombre del programa.
    ``run_all_fn`` / ``list_contracts_fn``: callables inyectables para
    tests; si son ``None`` se resuelven a ``mcp_gate_dispatch.run_all_level1``
    y ``list_contracts_json`` respectivamente (lookup del atributo en cada
    llamada).

    - ``['gates', 'run-all', '--json']``: comportamiento existente (sin
      cambios).
    - ``['contracts', 'list', '--json']``: ``result = fn(contracts_dir=
      'knowledge/contracts')``. Si ``result`` es una lista (incluida
      vacia): escribe ``json.dumps(result)`` y devuelve ``0``. Si es un
      dict con clave ``'error'``: escribe ``json.dumps(result)`` y
      devuelve ``1``.
    - cualquier otro ``argv``: mensaje de uso de UNA linea que empieza con
      ``usage:`` y menciona AMBOS subcomandos, devuelve ``2``. Ningun ``fn``
      se llama.
    """
```

```python
def list_contracts_json(contracts_dir='knowledge/contracts'):
    """Devuelve list[dict] | {'error': ...}.

    - ``validate_contracts._collect_files(contracts_dir)`` da los ``*.md``
      ordenados (excluye ``TEMPLATE-*.md``). Si devuelve ``None`` (directorio
      inexistente) -> ``{'error': 'contracts dir not found: ' + contracts_dir}``.
    - Por cada archivo con frontmatter valido (``parse_frontmatter`` no
      devuelve ``None``) agrega ``{'task','title','intent','target'}``; las
      claves ausentes se rellenan con ``''``. Los archivos sin frontmatter
      valido se saltan (no falla la llamada completa).
    - Orden: el de ``_collect_files`` (alfabetico por nombre de archivo).
    """
```

## Invariants
- ``run_all_fn`` y ``list_contracts_fn`` NUNCA se invocan si ``argv`` no es
  exactamente uno de los dos patrones validos (cero side effects para argv
  invalido: ni gates, ni lectura de disco, ni red).
- Para ``['contracts','list','--json']``, una lista VACIA es exito (devuelve
  ``0`` y escribe ``[]``); solo un dict con ``'error'`` devuelve ``1``.
- Cada elemento del resultado de exito tiene EXACTAMENTE las claves
  ``task``, ``title``, ``intent``, ``target`` (ninguna omitida; ausentes ->
  ``''``, nunca ``None``).
- La salida de exito es EXACTAMENTE ``json.dumps(result)``: una sola linea,
  sin pretty-print, sin newline añadido.
- Para argv invalido, lo escrito empieza con ``usage:`` y menciona AMBOS
  subcomandos; el exit code es siempre ``2``.
- ``main`` nunca lanza por un ``argv`` malformado: el unico parseo es una
  comparacion de igualdad de listas.

## Examples
- ``main(['contracts','list','--json'], out, list_contracts_fn=lambda c=[])`` -> escribe ``[]``, devuelve ``0`` (lista vacia es exito).
- ``main(['contracts','list','--json'], out, list_contracts_fn=lambda c=[{'task':'a','title':'A','intent':'i','target':'a.py'}])`` -> escribe ese JSON, devuelve ``0``.
- ``main(['contracts','list','--json'], out, list_contracts_fn=lambda c={'error':'...'})`` -> escribe ese JSON, devuelve ``1``.
- ``main([], out)`` -> escribe ``usage: ...`` mencionando ambos subcomandos, devuelve ``2``; ningun ``fn`` se llama.
- ``main(['contracts','list','--json','extra'], out)`` -> escribe ``usage: ...``, devuelve ``2`` (superset no matchea); ``list_contracts_fn`` no se llama.

## Do / Don't
- DO: importar ``validate_contracts`` como modulo hermano, mismo patron que
  ``mcp_gate_dispatch`` ya usa en este archivo.
- DO: resolver ``fn = list_contracts_fn if list_contracts_fn is not None
  else list_contracts_json`` (lookup del atributo en cada llamada, para que
  monkeypatch en tests funcione).
- DO: usar ``data.get('task', '')`` etc. para rellenar claves ausentes con
  ``''`` y dejar ``title`` tal cual lo devuelve el parser.
- DO: preservar el comportamiento de ``['gates','run-all','--json']``
  exactamente como estaba (los 24 tests originales siguen describiendo lo
  mismo).
- DON'T: incluir ``subprocess`` en ``forbids`` -- el target importa
  ``mcp_gate_dispatch`` que usa subprocess internamente; ``forbids`` es
  ``['network','llm']`` unicamente.
- DON'T: leer el CUERPO de los contratos (solo frontmatter), ni implementar
  mas subcomandos, ni paginacion ni filtros.
- DON'T: tocar ``scripts/validate_contracts.py``, ``mcp_gate_dispatch.py`` ni
  ningun archivo fuera de ``touch_only``.

## Tests
(Los tests estan en `tests/test_kdd_cli.py`, oraculo congelado sellado por
`tests_sha256`: el implementador no los escribe ni los modifica. Preservan
los 24 casos originales de `gates run-all --json` (reorganizados en clases)
y agregan los de `contracts list --json`: inyectan siempre un
`list_contracts_fn` fake (lambda que devuelve una lista literal o un dict
de error literal); el caso `list_contracts_fn=None` se ejercita
monkeypatcheando `kdd_cli.list_contracts_json` con un fake. Los casos de
argv invalido asertan exit 2, mensaje `usage:` que menciona AMBOS
subcomandos, y que ningun fake se llama. Sin subprocess real, red ni
filesystem real del repo dentro de un test.)

## Constraints
- PARAR y reportar si necesitas conectarte a la red o invocar un LLM.
- PARAR y reportar si el `intent` exige tocar un archivo fuera de
  `touch_only` (probablemente signifique que la spec esta mal escrita).
- PARAR y reportar si preservar el comportamiento viejo de
  `gates run-all --json` resulta imposible sin romper el nuevo subcomando.