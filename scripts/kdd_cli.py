#!/usr/bin/env python3
"""CLI de KDD (Contrato: kdd-contracts-list-json).

Piel 2 (CLI Python) del proyecto lazykdd: un unico punto de entrada con
una funcion ``main`` que despacha DOS subcomandos y emite JSON:

  - ``gates run-all --json``   -> motor de gates ya existente
    (``scripts/mcp_gate_dispatch.py``).
  - ``contracts list --json``  -> lista el frontmatter de los contratos de
    un directorio (``scripts/validate_contracts.py``).

Ambos modulos hermanos se importan igual que ``scripts/validate_rules.py``
importa ``rule_engine`` (mismo directorio, sin path hacks mas alla de
poner ``scripts/`` en ``sys.path``).

  Uso:
    python scripts/kdd_cli.py gates run-all --json
    python scripts/kdd_cli.py contracts list --json
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mcp_gate_dispatch  # noqa: E402
import validate_contracts  # noqa: E402


def list_contracts_json(contracts_dir='knowledge/contracts'):
    """Lista los contratos de ``contracts_dir`` como dicts de frontmatter.

    Usa ``validate_contracts._collect_files`` para obtener los ``*.md`` (ya
    excluye ``TEMPLATE-*.md`` y los ordena alfabeticamente por nombre de
    archivo). Para cada archivo lee el texto y parsea el frontmatter con
    ``validate_contracts.parse_frontmatter``.

    - Si ``_collect_files`` devuelve ``None`` (el directorio no existe),
      devuelve ``{'error': 'contracts dir not found: ' + contracts_dir}``.
    - Archivos sin frontmatter valido (parser devuelve ``None``) se
      saltan: no falla la llamada completa por un archivo malformado.
    - Por cada archivo con frontmatter valido agrega un dict con
      EXACTAMENTE las claves ``task``, ``title``, ``intent`` y ``target``;
      las claves ausentes en el frontmatter se rellenan con ``''`` (nunca
      ``None`` ni se omite la clave). Los valores salen tal cual los
      devuelve el parser (``data.get('task', '')`` etc.).
    - Devuelve la lista en el orden de ``_collect_files`` (puede estar
      vacia si el directorio existe pero no tiene contratos).
    """
    files = validate_contracts._collect_files(contracts_dir)
    if files is None:
        return {'error': 'contracts dir not found: ' + contracts_dir}
    result = []
    for path in files:
        with open(path, 'r', encoding='utf-8') as fh:
            text = fh.read()
        data, _ = validate_contracts.parse_frontmatter(text)
        if data is None:
            continue
        result.append({
            'task': data.get('task', ''),
            'title': data.get('title', ''),
            'intent': data.get('intent', ''),
            'target': data.get('target', ''),
        })
    return result


def main(argv, stdout, run_all_fn=None, list_contracts_fn=None):
    """Despacha el CLI de KDD.

    ``argv``: lista de argumentos SIN el nombre del programa.
    ``stdout``: stream con ``.write(str)`` (``sys.stdout`` en produccion;
    ``io.StringIO()`` en tests).
    ``run_all_fn``: callable ``fn(repo_root='.') -> {'overall_ok': bool,
      'results': {...}}`` inyectable para tests; si es ``None`` se resuelve
      a ``mcp_gate_dispatch.run_all_level1`` (lookup del atributo en cada
      llamada, para que monkeypatch en tests funcione).
    ``list_contracts_fn``: callable ``fn(contracts_dir='knowledge/contracts')
      -> list[dict] | {'error': ...}`` inyectable para tests; si es ``None``
      se resuelve a ``list_contracts_json`` (mismo modulo, lookup en cada
      llamada para que monkeypatch funcione).

    - ``argv == ['gates', 'run-all', '--json']``: ejecuta ``fn(repo_root='.')``,
      escribe ``json.dumps(result)`` (una linea, sin pretty-print) en
      ``stdout`` y devuelve ``0`` si ``result['overall_ok']`` es ``True``,
      si no ``1``.
    - ``argv == ['contracts', 'list', '--json']``: ejecuta
      ``fn(contracts_dir='knowledge/contracts')``. Si el resultado es una
      lista (incluida vacia) escribe ``json.dumps(result)`` y devuelve
      ``0``; si es un dict con clave ``'error'`` escribe
      ``json.dumps(result)`` y devuelve ``1``.
    - cualquier otro ``argv``: escribe un mensaje de uso de UNA linea que
      empieza con ``usage:`` y menciona AMBOS subcomandos en ``stdout`` y
      devuelve ``2``. Ningun ``fn`` se llama en este caso.
    - nunca lanza una excepcion no controlada por un ``argv`` malformado:
      el unico parseo es una comparacion de igualdad de listas.
    """
    if argv == ['gates', 'run-all', '--json']:
        fn = run_all_fn if run_all_fn is not None else mcp_gate_dispatch.run_all_level1
        result = fn(repo_root='.')
        stdout.write(json.dumps(result))
        return 0 if result['overall_ok'] is True else 1
    if argv == ['contracts', 'list', '--json']:
        fn = list_contracts_fn if list_contracts_fn is not None else list_contracts_json
        result = fn(contracts_dir='knowledge/contracts')
        if isinstance(result, list):
            stdout.write(json.dumps(result))
            return 0
        stdout.write(json.dumps(result))
        return 1
    stdout.write('usage: kdd_cli gates run-all --json | contracts list --json\n')
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:], sys.stdout))