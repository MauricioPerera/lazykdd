---
type: 'Task Contract'
title: 'Gate de diagramas Mermaid (flowchart, Python puro)'
description: 'Validador determinista de diagramas Mermaid flowchart contra un contrato JSON declarativo (nodos y edges requeridos). Parser propio en Python puro, sin subprocess/red/LLM: NO usa el parser real de mermaid (eso exigiria Node.js via subprocess, prohibido por forbids en los gates de este repo). Cobertura deliberadamente parcial: solo el subconjunto flowchart. Ver el proyecto hermano mermaid-gate (Node, parser real, 20 tipos de diagrama) para verificacion con fidelidad completa fuera de la restriccion de dependencias de este repo.'
tags: ['ccdd', 'diagramas', 'mermaid', 'gate', 'infra']

task: diagram-gate
intent: "Validar la estructura (nodos/edges) de un diagrama Mermaid flowchart contra un contrato JSON, sin depender de Node.js ni del parser real de mermaid."
target: scripts/validate_diagrams.py
signature: "def validate_diagram(mmd_path, contract_path) -> list"
test_command: "python -m unittest tests/test_validate_diagrams.py"
budget:
  max_cyclomatic_complexity: 14
  max_nesting_depth: 4
tests: "tests/test_validate_diagrams.py"
tests_sha256: "4d5fc3c0ebc578618d5f5f85144a1ecc6d9f268c3656935f1a673168d26b0c71"
touch_only: ['scripts/validate_diagrams.py']
deps_allowed: []
forbids: ['network', 'subprocess', 'llm']
---

# Contract: Gate de diagramas Mermaid (validate_diagrams)

## Intent
Verificar de forma determinista que un diagrama Mermaid `flowchart` contiene
los nodos y relaciones que un contrato JSON declara obligatorios, sin
ejecutar el parser real de mermaid (Node.js, requeriria `subprocess`,
prohibido por `forbids` en los gates de este repo). Es la contraparte
pure-Python, de cobertura parcial (solo flowchart), del proyecto hermano
`mermaid-gate` (Node, parser real, 20 tipos de diagrama). Convencion del
contrato JSON: `knowledge/diagram-contract-spec.md`. Nota de proceso: este
contrato se implemento directo en una sesion (no via el pipeline PM/dev
delegado descrito en `knowledge/metodologia-ejecucion.md`), por eso no
lleva numeracion `CONTRACT-NN` ni reporte en `docs/reports/`.

## Interface
- `parse_flowchart(text) -> {'nodes': [{'id','label'}], 'edges': [{'from','to','label'}]}`
  — parser regex de linea por linea para el subconjunto flowchart de Mermaid
  (definicion de nodo con shape `[ ]`/`{ }`/`( )`, edges `-->`, `-->|label|`,
  `---`, `-.->`). Nodo sin shape usa su id como label.
- `get_diagram_type(text) -> str|None` — primer token no vacio/no-comentario
  del texto (`'flowchart'` o `'graph'`).
- `validate_diagram(mmd_path, contract_path) -> list` — findings
  `{'file','level','rule','msg'}` ordenados por (rule, msg). Reglas, niveles
  y mensajes EXACTOS: docstring del oraculo congelado
  `tests/test_validate_diagrams.py` (FILE_ERROR, CONTRACT_INVALID,
  DIAGRAM_TYPE_UNSUPPORTED, DIAGRAM_TYPE_MISMATCH, MIN_NODES, MAX_NODES,
  MISSING_NODE, NODE_LABEL_MISMATCH, MISSING_EDGE).
- `main(argv) -> int` — uno o mas paths (archivo `.mmd` o directorio; default
  `['examples/diagrams']`); escanea `*.mmd` recursivo; cada `.mmd` espera un
  `<mismo-nombre>.diagram-contract.json` al lado (capa opcional: sin
  contrato, WARNING `CONTRACT_MISSING`, no bloquea); path ausente o sin
  `.mmd` -> INFO `PATH_MISSING`, no bloquea; exit 1 solo si hay >=1 ERROR;
  Resumen honesto con diagramas EFECTIVAMENTE verificados (pares con
  contrato presente).

## Invariants
- Python stdlib puro (`json`, `re`, `os`); sin red, sin subprocess, sin
  navegador; determinista; mensajes ASCII.
- Solo soporta `diagram_type: flowchart` (o alias `graph` en el `.mmd`). Un
  contrato que pida otro `diagram_type` produce `DIAGRAM_TYPE_UNSUPPORTED`
  (ERROR) en vez de intentar parsearlo de forma incorrecta.
- El contrato JSON es un subconjunto deliberadamente simple del formato YAML
  de `mermaid-gate` (mismo vocabulario: `diagram_type`, `min_nodes`,
  `max_nodes`, `required_nodes`, `required_edges`) pero en JSON, no YAML —
  este repo no tiene parser YAML de proposito general (mismo precedente que
  `rule_engine.py`, que usa JSON para `examples/rules/*.rules.json`).
- El parser NO maneja subgraphs, estilos, ni edges multi-linea — cobertura
  parcial declarada, no un bug oculto.

## Examples
- `flowchart TD\n    A[Inicio] --> B{Condicion}\n` con contrato
  `{"required_nodes":[{"id":"A","label":"Inicio"}]}` -> `[]`.
- Contrato con `required_edges: [{"from":"C","to":"A"}]` sobre un diagrama
  que no tiene ese edge -> `MISSING_EDGE` (ERROR), exit 1.
- `.mmd` sin `.diagram-contract.json` al lado -> `CONTRACT_MISSING`
  (WARNING), exit sigue en 0.

## Do / Don't
- DO: estilo de `validate_ux_page.py`/`validate_skills.py` (findings,
  Resumen honesto, capa opcional).
- DON'T: tocar `tests/test_validate_diagrams.py` (oraculo congelado,
  sellado).
- DON'T: usar `subprocess` para invocar Node/mermaid real — eso es
  exactamente lo que este gate evita, por `forbids` de este repo.
- DON'T: fingir soporte para tipos de diagrama distintos de flowchart; un
  contrato para otro tipo debe fallar explicito (`DIAGRAM_TYPE_UNSUPPORTED`),
  no intentar parsearlo con la gramatica equivocada.

## Tests
`python -m unittest tests/test_validate_diagrams.py` verde SIN modificar el
oraculo; suite completa sin regresiones.

## Constraints
- Tocar SOLO: `scripts/validate_diagrams.py`. Reporte local en
  `.agents/logs/C32-REPORT.md`.
- NO commitear (el PM commitea tras verificar).
- PARAR y reportar si: el oraculo exigiera comportamiento contradictorio; el
  budget de complejidad no alcanzara sin romper un test; o soportar un caso
  de sintaxis flowchart exigiera un parser real (no regex) — en ese caso el
  limite se documenta, no se fuerza con una heuristica fragil.
