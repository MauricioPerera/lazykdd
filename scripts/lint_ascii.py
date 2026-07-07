#!/usr/bin/env python3
"""Stub del target de lint-ascii (Contrato 13).

Creado por el orquestador para que el task contract valide pre-delegacion
(FM_PATH_target exige que el target exista); el dev de C13 lo REEMPLAZA
con la implementacion real. Contrato: knowledge/contracts/lint-ascii.md.
"""

import sys


def lint_ascii(scripts_dir):
    """Stub: sin implementar. El dev de C13 reemplaza este archivo."""
    raise NotImplementedError("stub: implementacion pendiente (C13)")


if __name__ == "__main__":
    print("stub: implementacion pendiente (C13)", file=sys.stderr)
    sys.exit(1)
