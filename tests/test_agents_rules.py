"""Test de coherencia de las reglas de agentes (KDD).

Fija la regla 7 de ``.agents/AGENTS.md`` y la seccion 7 de la skill
``kdd-okf-ccdd-hybrid`` contra la herramienta real: si alguien renombra
``scripts/assemble_context.py`` o ``ccdd/context.json`` sin actualizar las
reglas, esta suite se pone roja nombrando la referencia faltante y el archivo.

Solo lee archivos con ``pathlib``/``open`` (UTF-8); sin red, sin subprocess,
sin mocks. Task contract: ``knowledge/contracts/agents-context-rule.md``.
"""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENTS_MD = ROOT / ".agents" / "AGENTS.md"
SKILL_MD = ROOT / ".agents" / "skills" / "kdd-okf-ccdd-hybrid" / "SKILL.md"

ASSEMBLER_REF = "scripts/assemble_context.py"
CONTEXT_REF = "ccdd/context.json"


def _read(path: Path) -> str:
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


class TestAgentsRules(unittest.TestCase):
    def test_agents_md_references_assembler(self) -> None:
        text = _read(AGENTS_MD)
        self.assertIn(
            ASSEMBLER_REF,
            text,
            f"Falta la referencia '{ASSEMBLER_REF}' en {AGENTS_MD}",
        )
        self.assertIn(
            CONTEXT_REF,
            text,
            f"Falta la referencia '{CONTEXT_REF}' en {AGENTS_MD}",
        )

    def test_skill_references_assembler(self) -> None:
        text = _read(SKILL_MD)
        self.assertIn(
            ASSEMBLER_REF,
            text,
            f"Falta la referencia '{ASSEMBLER_REF}' en {SKILL_MD}",
        )
        self.assertIn(
            CONTEXT_REF,
            text,
            f"Falta la referencia '{CONTEXT_REF}' en {SKILL_MD}",
        )

    def test_referenced_files_exist(self) -> None:
        assembler = ROOT / ASSEMBLER_REF
        self.assertTrue(
            assembler.is_file(),
            f"El archivo referenciado '{ASSEMBLER_REF}' no existe en el repo",
        )
        context = ROOT / CONTEXT_REF
        self.assertTrue(
            context.is_file(),
            f"El archivo referenciado '{CONTEXT_REF}' no existe en el repo",
        )


if __name__ == "__main__":
    unittest.main()