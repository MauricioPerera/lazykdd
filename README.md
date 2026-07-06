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
3. When delegating work to an agent (e.g. an AI coding agent), the agent will read `.agents/AGENTS.md` and immediately understand that it must respect the CCDD contracts of this repository.
4. Drop the example artifacts and rewire `knowledge/index.md` with `python scripts/init_project.py --apply --name "<Your Project>"` (it removes `src/hello.py`, `src/users.py`, the sample tests, and the OKF example nodes; without `--apply` it only prints the plan).

#### Instantiating for a non-Python project

This template's KDD tooling is Python and stays Python even if your project is not — these are two separate planes (template tooling vs. your project's code).

- **Kept unchanged:** `scripts/validate_contracts.py`, `scripts/validate_okf.py`, `scripts/validate_specs.py`, `scripts/export_gate_contract.py`, and `scripts/init_project.py` remain Python; they validate contracts and produce the gate export regardless of your project's language.
- **Adapted:** each contract's `test_command` must use your language's runner (`node --test ...`, `cargo test ...`, etc. — see the multi-language support under Level 2 above). The CI workflow `.github/workflows/validate.yml` installs Python and runs only the template's Python suite (`python -m unittest discover -s tests`); if your project adds code/tests in another language, you add an extra CI step (e.g. `actions/setup-node` + `npm test`) so that suite also runs in CI. The existing Python step is still required because it validates the KDD tooling itself.
- **Example artifacts:** `scripts/init_project.py --apply` removes Python-written EXAMPLE artifacts (`src/hello.py`, `src/users.py`, the sample tests, the example OKF nodes) — they are only illustrative examples of the contract pattern, not a language dependency: they are removed the same way regardless of your project's language, and afterwards you add your own contracts/tests in your language.

### Contract Validation

Validation has **two levels**. Only level 1 is mandatory and is included in the template.

#### Level 1 — Included and mandatory (local + CI)
- `python scripts/validate_contracts.py knowledge/contracts` — validates frontmatter, mandatory sections, and examples of each contract.
- `python scripts/validate_specs.py specs` — validates that project-level execution contracts in `specs/` have machine-checkable acceptance criteria, a perimeter, and abort conditions (open vs. closed by `docs/reports/CONTRACT-NN-REPORT.md`).
- The `test_command` declared in the contract frontmatter — must finish green.

Both run locally and in CI (`.github/workflows/validate.yml` runs the validator and `python -m unittest discover -s tests -p "test_*.py"`).

#### Level 2 — Optional (if the agent environment has it)
If the agent has the `ccdd-complexity` MCP server available, the real CCDD gate is invoked with its tools `lint_task_contract` (contract lint) and `run_integration_gate` (complexity/integration gate). If it is not available, level 1 is sufficient to consider a contract valid.

The gate is **multi-language**. Python has a complete native signature parser (strictly validated). Other supported languages — JavaScript among them, with `measure_complexity` coverage that also includes TS/TSX/Rust/Go/Java/C#/PHP at the time of writing (this list is not exhaustive nor fixed; check the real gate for the current list) — route through a tree-sitter backend that applies the same complexity budget (cyclomatic/nesting/params) as Python. The `test_command` declared in the contract is run **verbatim** by the gate (the gate executes the declared command, with `cwd` = the target's directory). Tests must be self-runnable by that `test_command`; for JavaScript this means ESM (`.mjs` or `"type": "module"` in `package.json`) with a `test_command` like `"node --test <path>"`. With `language` set to something other than python, the `signature` is validated by **generic arity** (parameter count), not by a native parser of that language — Python is the only one with full signature parsing. `scan_dependencies` reasons in Python terms (imports/stdlib) and should NOT be used as part of the gate for non-Python languages.

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
3. Al delegar trabajo a un agente (ej. un agente de IA), el agente leerá `.agents/AGENTS.md` y entenderá inmediatamente que debe respetar los contratos CCDD de este repositorio.
4. Quita los artefactos de ejemplo y reescribe `knowledge/index.md` con `python scripts/init_project.py --apply --name "<Tu Proyecto>"` (elimina `src/hello.py`, `src/users.py`, los tests de ejemplo y los nodos OKF de ejemplo; sin `--apply` solo imprime el plan).

#### Instanciar para un proyecto no-Python

El tooling KDD de esta plantilla es Python y sigue siéndolo aunque tu proyecto no lo sea — son dos planos distintos (tooling de la plantilla vs. código de tu proyecto).

- **Se conserva sin cambios:** `scripts/validate_contracts.py`, `scripts/validate_okf.py`, `scripts/validate_specs.py`, `scripts/export_gate_contract.py` y `scripts/init_project.py` siguen siendo Python; validan contratos y generan el export del gate sin importar el lenguaje de tu proyecto.
- **Se adapta:** el `test_command` de cada contrato debe usar el runner de tu lenguaje (`node --test ...`, `cargo test ...`, etc. — ver el soporte multi-lenguaje del Nivel 2 arriba). El workflow de CI `.github/workflows/validate.yml` instala Python y corre solo la suite Python de la plantilla (`python -m unittest discover -s tests`); si tu proyecto agrega código/tests en otro lenguaje, agregas un paso de CI adicional (ej. `actions/setup-node` + `npm test`) para que esa suite también corra en CI. El paso Python existente sigue siendo necesario porque valida el tooling KDD mismo.
- **Artefactos de ejemplo:** `scripts/init_project.py --apply` borra artefactos de EJEMPLO escritos en Python (`src/hello.py`, `src/users.py`, los tests de ejemplo, los nodos OKF de ejemplo) — son solo ejemplos ilustrativos del patrón de contratos, no una dependencia de lenguaje: se borran igual sin importar el lenguaje de tu proyecto, y después agregas tus propios contratos/tests en tu lenguaje.

### Validación de Contratos

La validación tiene **dos niveles**. Solo el nivel 1 es obligatorio y viene incluido en la plantilla.

#### Nivel 1 — Incluido y obligatorio (local + CI)
- `python scripts/validate_contracts.py knowledge/contracts` — valida frontmatter, secciones obligatorias y examples de cada contrato.
- `python scripts/validate_specs.py specs` — valida que los contratos de ejecución de nivel proyecto en `specs/` tengan criterios de aceptación verificables por máquina, perímetro y condiciones de aborto (abierto vs. cerrado según `docs/reports/CONTRACT-NN-REPORT.md`).
- El `test_command` declarado en el frontmatter del contrato — debe terminar en verde.

Ambos corren localmente y en CI (`.github/workflows/validate.yml` ejecuta el validador y `python -m unittest discover -s tests -p "test_*.py"`).

#### Nivel 2 — Opcional (si el entorno del agente lo tiene)
Si el agente dispone del servidor MCP `ccdd-complexity`, el gate CCDD real se invoca con sus tools `lint_task_contract` (lint del contrato) y `run_integration_gate` (gate de complejidad/integración). Si no está disponible, el nivel 1 es suficiente para considerar un contrato válido.

El gate es **multi-lenguaje**. Python tiene un parser de firma nativo completo (validado estrictamente). Otros lenguajes soportados — JavaScript entre ellos, con cobertura de `measure_complexity` que además incluye TS/TSX/Rust/Go/Java/C#/PHP a la fecha (la lista no es exhaustiva ni fija; consulta el gate real para la lista vigente) — enrutan a un backend tree-sitter que aplica el mismo budget de complejidad (cyclomatic/nesting/params) que Python. El `test_command` declarado en el contrato se corre **verbatim** (el gate ejecuta el comando declarado, con `cwd` = directorio del target). Los tests deben ser auto-ejecutables por ese `test_command`; para JavaScript esto implica ESM (`.mjs` o `"type": "module"` en `package.json`) con un `test_command` como `"node --test <ruta>"`. Con `language` distinto de python, la `signature` se valida por **aridad genérica** (cantidad de parámetros), no con un parser nativo de ese lenguaje — Python es el único con parsing de firma completo. `scan_dependencies` razona en clave Python (imports/stdlib) y NO debe usarse como parte del gate para lenguajes no-Python.

El gate se corre sobre el **export** generado por `scripts/export_gate_contract.py` (normalización ASCII + `target`/`tests` reescritos relativos al export): `lint_task_contract` recibe el texto del export + tests, y `run_integration_gate` recibe la ruta del export en disco. Por defecto el export se escribe en la raíz del repo como `<task>.gate.md` (gitignorado vía `*.gate.md`) para que las rutas reescritas no contengan `..`, como exige el gate real.

### Precedencia del Budget

- **Con gate CCDD disponible (nivel 2):** la config firmada por el gate manda. El `budget` del frontmatter solo puede ser **<=** los topes firmados; ante cualquier conflicto gana la config firmada del gate.
- **Sin gate (solo nivel 1):** el `budget` del contrato es declarativo/informativo. El validador incluido solo verifica su **presencia** en el frontmatter; no aplica (enforce) los topes.

### Ciclo de Vida del Contrato

1. **draft** — contrato redactado en `knowledge/contracts/<task>.md`.
2. **validated** — `python scripts/validate_contracts.py knowledge/contracts` (y `lint_task_contract` si hay gate) en verde.
3. **implemented** — `test_command` del contrato en verde.
4. **verified** — la salida **REAL** de los comandos (validador + `test_command`, y gate si corre) se pega en `.agents/logs/<task>-REPORT.md`. Ese directorio está gitignorado a propósito: es evidencia local, no parte del repo.