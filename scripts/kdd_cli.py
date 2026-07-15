#!/usr/bin/env python3
"""CLI de KDD (Contrato: kdd-contracts-status-json).

Piel 2 (CLI Python) del proyecto lazykdd: un unico punto de entrada con
una funcion ``main`` que despacha CUATRO subcomandos y emite JSON:

  - ``gates run-all --json``   -> motor de gates ya existente
    (``scripts/mcp_gate_dispatch.py``).
  - ``contracts list --json``  -> lista el frontmatter de los contratos de
    un directorio (``scripts/validate_contracts.py``).
  - ``contracts scaffold <task> --json`` -> crea un nuevo contrato a partir
    de ``TEMPLATE-task-contract.md`` (``scaffold_contract``).
  - ``contracts status --json`` -> etapa de ciclo de vida de cada contrato
    (``list_contract_status``).

Los modulos hermanos se importan igual que ``scripts/validate_rules.py``
importa ``rule_engine`` (mismo directorio, sin path hacks mas alla de
poner ``scripts/`` en ``sys.path``).

  Uso:
    python scripts/kdd_cli.py gates run-all --json
    python scripts/kdd_cli.py contracts list --json
    python scripts/kdd_cli.py contracts scaffold <task> --json
    python scripts/kdd_cli.py contracts status --json
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mcp_gate_dispatch  # noqa: E402
import validate_contracts  # noqa: E402
import validate_test_commands  # noqa: E402


_KEBAB_RE = re.compile(r'^[a-z0-9]+(-[a-z0-9]+)*$')
_TASK_PLACEHOLDER_LINE = 'task: <nombre-kebab-case>'


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


def scaffold_contract(task_name, contracts_dir='knowledge/contracts',
                      template_path='knowledge/contracts/TEMPLATE-task-contract.md'):
    """Crea un nuevo contrato a partir de ``TEMPLATE-task-contract.md``.

    - Valida ``task_name`` contra kebab-case estricto
      (``^[a-z0-9]+(-[a-z0-9]+)*$``). Si NO matchea, devuelve
      ``{'error': 'invalid task name (must be kebab-case): ' + task_name}``
      SIN tocar el filesystem (ni leer el template ni escribir nada).
    - ``target_path = os.path.join(contracts_dir, task_name + '.md')``. Si
      YA EXISTE (``os.path.exists``), devuelve
      ``{'error': 'contract already exists: ' + target_path}`` SIN
      sobreescribir nunca un archivo existente.
    - Si ``template_path`` no existe, devuelve
      ``{'error': 'template not found: ' + template_path}``.
    - Lee el template. Genera el contenido nuevo:
      1. Reemplaza la linea ``task: <nombre-kebab-case>`` por
         ``task: <task_name>`` (reemplazo literal de esa linea exacta del
         frontmatter).
      2. Elimina el bloque final de instrucciones humanas: todo desde (e
         incluyendo) la linea ``---`` que precede a ``<!--`` hasta el final
         del archivo (el comentario HTML completo, incluido su ``-->`` de
         cierre). El contenido resultante termina justo despues de la
         seccion ``## Constraints`` con un unico salto de linea final.
      3. NO toca ningun otro placeholder ``<...>``.
    - Escribe el contenido nuevo en ``target_path`` (crealo, no existia) y
      devuelve ``{'created': True, 'path': target_path}``.
    """
    if not _KEBAB_RE.fullmatch(task_name):
        return {'error': 'invalid task name (must be kebab-case): ' + task_name}
    target_path = os.path.join(contracts_dir, task_name + '.md')
    if os.path.exists(target_path):
        return {'error': 'contract already exists: ' + target_path}
    if not os.path.exists(template_path):
        return {'error': 'template not found: ' + template_path}
    with open(template_path, 'r', encoding='utf-8') as fh:
        text = fh.read()
    lines = text.split('\n')
    for i, line in enumerate(lines):
        if line == _TASK_PLACEHOLDER_LINE:
            lines[i] = 'task: ' + task_name
            break
    comment_idx = None
    for i, line in enumerate(lines):
        if line.lstrip().startswith('<!--'):
            comment_idx = i
            break
    if comment_idx is not None:
        sep_idx = comment_idx - 1
        while sep_idx >= 0 and lines[sep_idx].strip() == '':
            sep_idx -= 1
        if sep_idx >= 0 and lines[sep_idx].strip() == '---':
            lines = lines[:sep_idx]
        else:
            lines = lines[:comment_idx]
    while lines and lines[-1].strip() == '':
        lines.pop()
    content = '\n'.join(lines) + '\n'
    with open(target_path, 'w', encoding='utf-8') as fh:
        fh.write(content)
    return {'created': True, 'path': target_path}


def list_contract_status(contracts_dir='knowledge/contracts',
                         repo_root='.'):
    """Devuelve la etapa de ciclo de vida de cada contrato como list[dict].

    Etapas (la mas alta que cumple, en orden): ``draft`` < ``validated`` <
    ``implemented`` < ``verified``.

    - ``validate_contracts._collect_files(contracts_dir)`` da los ``*.md``
      (excluye ``TEMPLATE-*.md``, orden alfabetico). Si devuelve ``None``
      (directorio inexistente) -> ``{'error': 'contracts dir not found: '
      + contracts_dir}``.
    - Corre ``validate_test_commands.run_all(contracts_dir, repo_root)``
      UNA sola vez (ya recorre todos los ``test_command`` reales) y arma
      ``{path: item}`` para lookup O(1).
    - Por cada archivo (mismo orden que ``_collect_files``):
      1. Lee el texto, ``parse_frontmatter`` -> ``fm``; ``task =
         fm.get('task', '') if fm else ''``.
      2. ``findings = validate_contracts.validate_file(path,
         repo_root=repo_root)``; ``validated = not any(f.level ==
         'ERROR' for f in findings)``.
      3. ``implemented = validated and (path en run_all) and
         item['ok'] is True`` (un contrato ausente de ``run_all`` -- p.
         ej. ``test_command`` vacio -- NO es ``implemented``).
      4. ``verified = implemented and task and os.path.isfile(
         .agents/logs/<task>-REPORT.md bajo repo_root)``.
      5. Etapa mas alta que cumple; agrega ``{'task': task, 'lifecycle':
         <etapa>}``.
    - Devuelve la lista (puede quedar vacia si no hay contratos).
    """
    files = validate_contracts._collect_files(contracts_dir)
    if files is None:
        return {'error': 'contracts dir not found: ' + contracts_dir}
    # ``run_all`` ejecuta los ``test_command`` reales via subprocess que
    # heredan los fds 1/2 del proceso; su stdout/stderr contaminarian el JSON
    # que el CLI emite en stdout. Los silenciamos a nivel de fd (no a nivel de
    # sys.stdout, que los hijos bypass) solo durante la corrida, restaurando
    # despues para que la salida del CLI sea exactamente el JSON.
    saved_out = os.dup(1)
    saved_err = os.dup(2)
    devnull = os.open(os.devnull, os.O_WRONLY)
    try:
        os.dup2(devnull, 1)
        os.dup2(devnull, 2)
        run_results = validate_test_commands.run_all(contracts_dir, repo_root)
    finally:
        os.dup2(saved_out, 1)
        os.dup2(saved_err, 2)
        os.close(devnull)
        os.close(saved_out)
        os.close(saved_err)
    by_path = {item['path']: item for item in run_results}
    result = []
    for path in files:
        with open(path, 'r', encoding='utf-8') as fh:
            text = fh.read()
        fm, _ = validate_contracts.parse_frontmatter(text)
        task = fm.get('task', '') if fm else ''
        findings = validate_contracts.validate_file(path, repo_root=repo_root)
        validated = not any(f.level == 'ERROR' for f in findings)
        item = by_path.get(path)
        implemented = validated and item is not None and item['ok'] is True
        report_path = os.path.join(repo_root, '.agents', 'logs',
                                   task + '-REPORT.md')
        verified = implemented and bool(task) and os.path.isfile(report_path)
        if verified:
            lifecycle = 'verified'
        elif implemented:
            lifecycle = 'implemented'
        elif validated:
            lifecycle = 'validated'
        else:
            lifecycle = 'draft'
        result.append({'task': task, 'lifecycle': lifecycle})
    return result


def main(argv, stdout, run_all_fn=None, list_contracts_fn=None,
         scaffold_fn=None, status_fn=None):
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
    ``scaffold_fn``: callable ``fn(task_name) -> {'created': True, ...} |
      {'error': ...}`` inyectable para tests; si es ``None`` se resuelve a
      ``scaffold_contract`` (mismo modulo, lookup en cada llamada).
    ``status_fn``: callable ``fn() -> list[dict] | {'error': ...}`` inyectable
      para tests; si es ``None`` se resuelve a ``list_contract_status``
      (mismo modulo, lookup en cada llamada).

    - ``argv == ['gates', 'run-all', '--json']``: ejecuta ``fn(repo_root='.')``,
      escribe ``json.dumps(result)`` (una linea, sin pretty-print) en
      ``stdout`` y devuelve ``0`` si ``result['overall_ok']`` es ``True``,
      si no ``1``.
    - ``argv == ['contracts', 'list', '--json']``: ejecuta
      ``fn(contracts_dir='knowledge/contracts')``. Si el resultado es una
      lista (incluida vacia) escribe ``json.dumps(result)`` y devuelve
      ``0``; si es un dict con clave ``'error'`` escribe
      ``json.dumps(result)`` y devuelve ``1``.
    - ``argv == ['contracts', 'scaffold', <task_name>, '--json']`` (4
      elementos exactos: ``argv[0]=='contracts'``, ``argv[1]=='scaffold'``,
      ``argv[3]=='--json'``, ``argv[2]`` un string): ejecuta
      ``fn(argv[2])``. Si ``result`` tiene ``'created': True`` escribe
      ``json.dumps(result)`` y devuelve ``0``; si tiene clave ``'error'``
      escribe ``json.dumps(result)`` y devuelve ``1``.
    - ``argv == ['contracts', 'status', '--json']`` (3 elementos exactos):
      ejecuta ``fn()``. Si ``result`` es una lista (incluida vacia) escribe
      ``json.dumps(result)`` y devuelve ``0``; si es un dict con clave
      ``'error'`` escribe ``json.dumps(result)`` y devuelve ``1``.
    - cualquier otro ``argv``: escribe un mensaje de uso de UNA linea que
      empieza con ``usage:`` y menciona los CUATRO subcomandos en ``stdout`` y
      devuelve ``2``. Ningun ``fn`` se llama en este caso.
    - nunca lanza una excepcion no controlada por un ``argv`` malformado:
      el unico parseo es una comparacion de igualdad de listas (y, para
      scaffold, un chequeo de largo + posiciones + tipo).
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
    if (len(argv) == 4 and argv[0] == 'contracts' and argv[1] == 'scaffold'
            and argv[3] == '--json' and isinstance(argv[2], str)):
        fn = scaffold_fn if scaffold_fn is not None else scaffold_contract
        result = fn(argv[2])
        if result.get('created') is True:
            stdout.write(json.dumps(result))
            return 0
        stdout.write(json.dumps(result))
        return 1
    if argv == ['contracts', 'status', '--json']:
        fn = status_fn if status_fn is not None else list_contract_status
        result = fn()
        if isinstance(result, list):
            stdout.write(json.dumps(result))
            return 0
        stdout.write(json.dumps(result))
        return 1
    stdout.write('usage: kdd_cli gates run-all --json | contracts list --json '
                 '| contracts scaffold <task> --json '
                 '| contracts status --json\n')
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:], sys.stdout))