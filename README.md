# KDD Template (Knowledge-Driven Development)

[English](#english) | [Español](#español)

<a id="english"></a>

## English

This is a template repository for projects that implement the **Knowledge-Driven Development (KDD)** methodology, which unifies:
- **OKF (Open Knowledge Format):** A minimalist format for structuring knowledge, design, and architecture as markdown files with YAML frontmatter. The normative spec for OKF nodes lives in [`knowledge/OKF-SPEC.md`](knowledge/OKF-SPEC.md).
- **CCDD (Contract-Driven Development):** A methodology for governing development with ephemeral AI agents through strict contracts and deterministic thresholds (complexity, frozen tests).

### Repository Structure

- `knowledge/`: Where your OKF knowledge base lives. Every file here is an indexable node.
- `knowledge/contracts/`: Where tasks for developers (human or AI) are defined using the hybrid OKF+CCDD format.
- `src/` and `tests/`: Implementation code and automated tests.
- `scripts/validate_contracts.py`: Deterministic contract validator (stdlib, no LLM, no network).
- `.agents/`: Local rules for AI agents that clone this repository.
- `specs/` and `docs/reports/`: Project-level **execution contracts** and their verified,
  in-repo reports (templates included). Task-level evidence stays local in `.agents/logs/`;
  see [`knowledge/metodologia-ejecucion.md`](knowledge/metodologia-ejecucion.md).
- `scripts/assemble_context.py` + `ccdd/context.json`: budgeted, deterministic context
  assembler over the OKF knowledge base (CCDD Level 2).

### How to use this template

1. Use this repository as a "Template" on GitHub or clone it locally.
2. Explore `knowledge/index.md` to see how concepts are structured.
3. When delegating work to an agent (e.g. Claude, Antigravity, etc.), the agent will read `.agents/AGENTS.md` and immediately understand that it must respect the CCDD contracts of this repository.
4. Drop the example artifacts and rewire `knowledge/index.md` with `python scripts/init_project.py --apply --name "<Your Project>"` (it removes `src/hello.py`, `src/users.py`, the sample tests, and the OKF example nodes; without `--apply` it only prints the plan).

### Contract Validation

Validation has **two levels**. Only level 1 is mandatory and is included in the template.

#### Level 1 — Included and mandatory (local + CI)
- `python scripts/validate_contracts.py knowledge/contracts` — validates frontmatter, mandatory sections, and examples of each contract.
- The `test_command` declared in the contract frontmatter — must finish green.

Both run locally and in CI (`.github/workflows/validate.yml` runs the validator and `python -m unittest discover -s tests -p "test_*.py"`).

#### Level 2 — Optional (if the agent environment has it)
If the agent has the `ccdd-complexity` MCP server available, the real CCDD gate is invoked with its tools `lint_task_contract` (contract lint) and `run_integration_gate` (complexity/integration gate). If it is not available, level 1 is sufficient to consider a contract valid.

The gate runs over the **export** produced by `scripts/export_gate_contract.py` (ASCII normalization + `target`/`tests` rewritten relative to the export): `lint_task_contract` takes the export text + tests, and `run_integration_gate` takes the export path on disk. By default the export is written to the repo root as `<task>.gate.md` (gitignored via `*.gate.md`) so the rewritten paths have no `..`, which the real gate requires.

### Budget Precedence

- **With CCDD gate available (level 2):** the config signed by the gate takes precedence. The frontmatter `budget` can only be **<=** the signed limits; on any conflict, the gate's signed config wins.
- **Without gate (level 1 only):** the contract's `budget` is declarative/informative. The included validator only checks its **presence** in the frontmatter; it does not enforce the limits.

### Contract Lifecycle

1. **draft** — contract written in `knowledge/contracts/<task>.md`.
2. **validated** — `python scripts/validate_contracts.py knowledge/contracts` (and `lint_task_contract` if the gate is present) green.
3. **implemented** — the contract's `test_command` green.
4. **verified** — the **REAL** output of the commands (validator + `test_command`, and gate if it runs) is pasted into `.agents/logs/<task>-REPORT.md`. That directory is gitignored on purpose: it is local evidence, not part of the repo.

<a id="español"></a>

## Español

Este repositorio plantilla es para proyectos que implementan la metodología **Knowledge-Driven Development (KDD)**, la cual unifica:
- **OKF (Open Knowledge Format):** Un formato minimalista para estructurar el conocimiento, diseño y arquitectura como archivos markdown con frontmatter YAML. La spec normativa de los nodos OKF está en [`knowledge/OKF-SPEC.md`](knowledge/OKF-SPEC.md).
- **CCDD (Contract-Driven Development):** Una metodología para gobernar el desarrollo con agentes de IA efímeros mediante contratos estrictos y umbrales deterministas (complejidad, tests congelados).

### Estructura del Repositorio

- `knowledge/`: Aquí vive tu base de conocimiento OKF. Todo archivo aquí es un nodo indexable.
- `knowledge/contracts/`: Donde se definen las tareas para los desarrolladores (humanos o IA) usando el formato híbrido OKF+CCDD.
- `src/` y `tests/`: Código de implementación y pruebas automatizadas.
- `scripts/validate_contracts.py`: Validador determinista de contratos (stdlib, sin LLM, sin red).
- `.agents/`: Reglas locales para agentes de IA que clonen este repositorio.
- `specs/` y `docs/reports/`: **contratos de ejecución** de nivel proyecto y sus reportes
  verificados en-repo (plantillas incluidas). La evidencia de tarea sigue siendo local en
  `.agents/logs/`; ver [`knowledge/metodologia-ejecucion.md`](knowledge/metodologia-ejecucion.md).
- `scripts/assemble_context.py` + `ccdd/context.json`: ensamblador de contexto presupuestado
  y determinista sobre la KB OKF (CCDD Nivel 2).

### Cómo usar esta plantilla

1. Usa este repositorio como "Template" en GitHub o clónalo localmente.
2. Explora `knowledge/index.md` para ver cómo se estructuran los conceptos.
3. Al delegar trabajo a un agente (ej. Claude, Antigravity, etc.), el agente leerá `.agents/AGENTS.md` y entenderá inmediatamente que debe respetar los contratos CCDD de este repositorio.
4. Quita los artefactos de ejemplo y reescribe `knowledge/index.md` con `python scripts/init_project.py --apply --name "<Tu Proyecto>"` (elimina `src/hello.py`, `src/users.py`, los tests de ejemplo y los nodos OKF de ejemplo; sin `--apply` solo imprime el plan).

### Validación de Contratos

La validación tiene **dos niveles**. Solo el nivel 1 es obligatorio y viene incluido en la plantilla.

#### Nivel 1 — Incluido y obligatorio (local + CI)
- `python scripts/validate_contracts.py knowledge/contracts` — valida frontmatter, secciones obligatorias y examples de cada contrato.
- El `test_command` declarado en el frontmatter del contrato — debe terminar en verde.

Ambos corren localmente y en CI (`.github/workflows/validate.yml` ejecuta el validador y `python -m unittest discover -s tests -p "test_*.py"`).

#### Nivel 2 — Opcional (si el entorno del agente lo tiene)
Si el agente dispone del servidor MCP `ccdd-complexity`, el gate CCDD real se invoca con sus tools `lint_task_contract` (lint del contrato) y `run_integration_gate` (gate de complejidad/integración). Si no está disponible, el nivel 1 es suficiente para considerar un contrato válido.

El gate se corre sobre el **export** generado por `scripts/export_gate_contract.py` (normalización ASCII + `target`/`tests` reescritos relativos al export): `lint_task_contract` recibe el texto del export + tests, y `run_integration_gate` recibe la ruta del export en disco. Por defecto el export se escribe en la raíz del repo como `<task>.gate.md` (gitignorado vía `*.gate.md`) para que las rutas reescritas no contengan `..`, como exige el gate real.

### Precedencia del Budget

- **Con gate CCDD disponible (nivel 2):** la config firmada por el gate manda. El `budget` del frontmatter solo puede ser **<=** los topes firmados; ante cualquier conflicto gana la config firmada del gate.
- **Sin gate (solo nivel 1):** el `budget` del contrato es declarativo/informativo. El validador incluido solo verifica su **presencia** en el frontmatter; no aplica (enforce) los topes.

### Ciclo de Vida del Contrato

1. **draft** — contrato redactado en `knowledge/contracts/<task>.md`.
2. **validated** — `python scripts/validate_contracts.py knowledge/contracts` (y `lint_task_contract` si hay gate) en verde.
3. **implemented** — `test_command` del contrato en verde.
4. **verified** — la salida **REAL** de los comandos (validador + `test_command`, y gate si corre) se pega en `.agents/logs/<task>-REPORT.md`. Ese directorio está gitignorado a propósito: es evidencia local, no parte del repo.