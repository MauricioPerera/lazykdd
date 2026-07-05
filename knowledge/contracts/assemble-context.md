---
type: 'Task Contract'
title: 'Ensamblador de contexto CCDD Nivel 2'
description: 'Ensamblador determinista de contexto presupuestado sobre la KB OKF: slots con prioridad, compaction, firmas sha256 y guardrails.'
tags: ['ccdd', 'context', 'okf', 'assembler']

task: assemble-context
intent: "Ensamblar contexto presupuestado y determinista desde la KB OKF según un contrato JSON de slots."
target: scripts/assemble_context.py
signature: "def assemble(contract: dict, task: str, base_dir: str) -> dict:"
test_command: "python -m unittest tests/test_assemble_context.py"
budget:
  max_cyclomatic_complexity: 10
  max_nesting_depth: 4
tests: "tests/test_assemble_context.py"
deps_allowed: []
forbids: ['network', 'subprocess']
---

# Contract: assemble-context

## Intent
Portar el ensamblador de contexto CCDD Nivel 2 (probado en el proyecto origen, ver
[metodología de ejecución](../metodologia-ejecucion.md)) a esta plantilla: dado un contrato
JSON de slots y una tarea, produce contexto presupuestado, firmado y auditado desde la KB
OKF de `knowledge/`.

## Interface
```python
def assemble(contract: dict, task: str, base_dir: str) -> dict:
    """Ensambla el contexto. Devuelve dict con: slots (lista de reportes por slot:
    id, priority, status included|omitted, tokens, compaction, sign, selected),
    context (str), used, available, guardrails {ok, findings}.
    Lanza ValueError con mensaje claro ante contrato inválido; los guardrails
    on_fail=abort se reportan vía excepción dedicada o clave de error (documentar)."""
```
CLI: `python scripts/assemble_context.py <contract.json> "<tarea>" [-v]` — reporte por
slot + totales + guardrails; con `-v` además el contexto completo. Exit 0 ok · 2 contrato
inválido o guardrail abort · 1 I/O.

## Invariants
- Determinismo estricto: mismas entradas → stdout byte a byte idéntico (sin relojes, sin
  orden de dict no determinista; heurística 1 token ≈ 4 chars, documentada).
- Slots por prioridad ascendente; presupuesto global = max_tokens - output_reserve; topes
  max_tokens/min_tokens por slot; compaction `none`|`truncate`|`summarize`. **`truncate` y
  `summarize` son AMBOS corte por caracteres determinista (sin LLM, sin resumen semántico):
  solo difieren el marcador que dejan al cortar (`[...truncated]` vs `[...summarized]`).
  `summarize` se mantiene aceptado por compatibilidad con la plantilla publicada, pero el
  nombre es histórico, no descriptivo: no resume, corta igual que `truncate`.
- `sign: true` → sha256 del contenido compactado, primeros 12 hex.
- Providers dinámicos: `okf_index` (knowledge/index.md) y `okf_nodes` (nodos seleccionados
  por retriever determinista: mención literal del nombre de archivo o de valores de `tags`
  del frontmatter en la tarea; sin matches → todos, compactados; orden alfabético estable).
- Guardrails: `regex_deny` (cada patrón se evalúa con `re.search` de stdlib sobre el
  contexto ensamblado — es un patrón regex de verdad, no un substring literal; un patrón que
  no compila → `ValueError` que nombra el patrón, sin silencio ni fallback a literal;
  on_fail abort → exit 2) y `reference_check` (ruta `knowledge/...md` citada en la tarea que
  no existe → hallazgo). El reporte lista SOLO los guardrails configurados en el
  contrato/config: sin `regex_deny` configurado, la palabra `regex_deny` no aparece en el
  reporte.
- Solo stdlib; sin red; sin subprocess; sin escribir archivos (salida por stdout).

## Examples
- `python scripts/assemble_context.py ccdd/context.json "documentar la tabla users"` ->
  exit 0, reporte con `okf_nodes` incluyendo `users_table` (match por tag/mención).
- `assemble(contract, "tarea que cita knowledge/no-existe.md", ".")` -> guardrails con
  hallazgo de `reference_check` (nodo inexistente).
- `assemble(contract, "log: secret : value", ".")` con `regex_deny.patterns=["secret\\s*:"]`
  -> abort: el patrón regex matchea `secret :` (con espacio), que un substring literal
  `secret\s*:` no atraparía. Con `patterns=["["]` -> `ValueError` que nombra el patrón.
- `assemble(contract_sin_guardrails, "tarea", ".")` -> el reporte no menciona `regex_deny`
  ni `reference_check` (no configurados); `guardrails: ok` sin sub-líneas.
- Dos invocaciones idénticas del CLI -> stdout byte a byte idéntico.

## Do / Don't
- DO: portar la semántica del patrón probado (prioridad/presupuesto/compaction/firma).
- DO: mensajes de error con la causa exacta (qué clave falta, qué slot excede, qué patrón
  regex no compila).
- DO: que el reporte sea honesto — listar solo los guardrails configurados y declarar que
  `truncate`/`summarize` son corte por caracteres (no sobre-prometer con el nombre).
- DON'T: dependencias fuera de stdlib, red, subprocess, timestamps en la salida.
- DON'T: usar `pat in context` (substring literal) para `regex_deny`; usar `re.search`.
- DON'T: imprimir `regex_deny: ok`/`reference_check: ok` cuando ese guardrail no está
  configurado en el contrato.
- DON'T: modificar `scripts/validate_contracts.py`, `src/`, tests existentes o nodos OKF existentes.

## Tests
(Los tests están en `tests/test_assemble_context.py`: presupuesto respetado, prioridades,
truncado, min_tokens, firma estable, determinismo 2×, retriever por mención/tags/fallback,
regex_deny aborta, reference_check detecta y pasa, exit codes del CLI. Además (CTX-HONESTO,
T8): `regex_deny` evalúa con `re.search` — un patrón regex real como `secret\s*:` matchea
contenido que el substring literal no matchearía; un patrón que no compila lanza `ValueError`
que lo nombra; un patrón alfanumérico simple (sin metacaracteres regex) da el mismo veredicto
que antes; y el reporte omite los guardrails no configurados — sin `regex_deny` configurado
la palabra `regex_deny` no aparece.)

## Constraints
- PARAR y reportar si... el contrato JSON exigiera capacidades imposibles con stdlib puro,
  si hiciera falta red o subprocess para cumplir un criterio, o si un test existente del
  repo se rompiera con el cambio.
