#!/usr/bin/env python3
"""CLI de KDD (Contrato: kdd-gates-run-all-json).

Primera pieza de la Piel 2 (CLI Python) del proyecto lazykdd: un unico
punto de entrada con UNA sola funcion nueva, ``main``, que despacha el
subcomando ``gates run-all --json`` al motor de gates ya existente
(``scripts/mcp_gate_dispatch.py``) y emite el JSON resultante.

  Uso:
    python scripts/kdd_cli.py gates run-all --json

Sin mas subcomandos, sin paquete instalable, sin entry_point (tareas
futuras, fuera del alcance de este contrato). ``mcp_gate_dispatch`` se
importa como modulo hermano -- mismo patron que ``scripts/validate_rules.py``
importa ``rule_engine`` (mismo directorio, sin path hacks mas alla de
poner ``scripts/`` en ``sys.path``).
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mcp_gate_dispatch  # noqa: E402


def main(argv, stdout, run_all_fn=None):
    """Despacha el CLI de KDD.

    ``argv``: lista de argumentos SIN el nombre del programa.
    ``stdout``: stream con ``.write(str)`` (``sys.stdout`` en produccion;
    ``io.StringIO()`` en tests).
    ``run_all_fn``: callable ``fn(repo_root='.') -> {'overall_ok': bool,
      'results': {...}}`` inyectable para tests; si es ``None`` se resuelve
      a ``mcp_gate_dispatch.run_all_level1`` (lookup del atributo en cada
      llamada, para que monkeypatch en tests funcione).

    - ``argv == ['gates', 'run-all', '--json']``: ejecuta ``fn(repo_root='.')``,
      escribe ``json.dumps(result)`` (una linea, sin pretty-print) en
      ``stdout`` y devuelve ``0`` si ``result['overall_ok']`` es ``True``,
      si no ``1``.
    - cualquier otro ``argv``: escribe un mensaje de uso de UNA linea que
      empieza con ``usage:`` en ``stdout`` y devuelve ``2``. ``fn`` NUNCA
      se llama en este caso.
    - nunca lanza una excepcion no controlada por un ``argv`` malformado:
      el unico parseo es una comparacion de igualdad de listas.
    """
    if argv == ['gates', 'run-all', '--json']:
        fn = run_all_fn if run_all_fn is not None else mcp_gate_dispatch.run_all_level1
        result = fn(repo_root='.')
        stdout.write(json.dumps(result))
        return 0 if result['overall_ok'] is True else 1
    stdout.write('usage: kdd_cli gates run-all --json\n')
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:], sys.stdout))