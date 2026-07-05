# Contrato 01 — Completar la plantilla KDD con la capa de ejecución y el ensamblador de contexto

Prerrequisitos: plantilla base de KDD (validador determinista + tests + CI + KB OKF).
Incorpora las piezas probadas en producción en el proyecto `workflow` (28 contratos):
la capa de contratos de ejecución con reportes verificados en-repo, la metodología
operativa como nodo OKF, y el ensamblador de contexto presupuestado (CCDD Nivel 2).

> Capa: contrato de ejecución (nivel proyecto). La tarea de código (E-ASSEMBLE) lleva su
> task contract CCDD en `knowledge/contracts/assemble-context.md`.

## E-SPECS (T2) — capa de contratos de ejecución

Hoy KDD tiene task contracts (nivel función/tarea, `knowledge/contracts/`) pero no una capa
de nivel proyecto. OBJETIVO: `specs/` con plantilla (`TEMPLATE-CONTRACT.md`) y este contrato
como primer ejemplar; `docs/reports/` en-repo con plantilla (`TEMPLATE-REPORT.md`). Los
reportes de contrato de ejecución viven EN el repo (evidencia publicada); los REPORT de
tarea de dev siguen en `.agents/logs/` (gitignorados), como manda el ciclo de vida de KDD.

## E-METODO (T3) — metodología operativa como nodo OKF

OBJETIVO: nodo `knowledge/metodologia-ejecucion.md` (type `Concept`, OKF-válido, enlazado
desde `index.md`) con el proceso operativo probado: spec por objetivo con plantilla fija,
delegación a agentes efímeros, política de reintentos (máx 2 con feedback → subdividir →
escalar), verificación por artefacto (salida real de comandos, nunca la palabra del agente),
suite 2× al cierre, commit por tarea verificada. README con línea de estado verificado
(EN y ES).

## E-ASSEMBLE (T1) — ensamblador de contexto CCDD Nivel 2 (Python stdlib)

KDD prescribe CCDD pero no tiene ensamblador de contexto. OBJETIVO: puerto del patrón
probado (workflow C26) a Python stdlib: `scripts/assemble_context.py` — contrato de contexto
JSON (`ccdd/context.json`: presupuesto max_tokens/output_reserve, slots con prioridad/
compaction none|truncate|summarize/max·min_tokens/sign sha256 12-hex, guardrails) con slots
dinámicos sobre la KB OKF: provider `okf_index` (índice) y provider `okf_nodes` (nodos
seleccionados por retriever determinista: mención literal + tags del frontmatter; sin
matches → todos compactados; orden estable) + slot `runtime` (la tarea). Guardrails:
`regex_deny` (on_fail abort → exit 2) y `reference_check` (rutas de nodos citadas en la
tarea que no existen en `knowledge/` → hallazgo). Determinismo estricto: mismas entradas →
stdout byte a byte idéntico (sin relojes ni orden de dict no determinista). CLI:
`python scripts/assemble_context.py ccdd/context.json "<tarea>" [-v]`; exit 0 ok · 2
contrato inválido o guardrail abort · 1 I/O. Sin red, sin subprocess, sin dependencias
fuera de stdlib. Tests `unittest` en `tests/test_assemble_context.py` (presupuesto,
prioridades, compaction, firma estable, determinismo 2×, retriever, guardrails, exit
codes). Paso nuevo en `.github/workflows/validate.yml` que ensambla el contrato real como
smoke (exit 0). Task contract: `knowledge/contracts/assemble-context.md` (pasa el validador).

## Criterios de aceptación

- [ ] `python scripts/validate_contracts.py knowledge/contracts` exit 0 (incluye el task
  contract nuevo).
- [ ] `python -m unittest discover -s tests -p "test_*.py"` verde, 2× al cierre.
- [ ] `python scripts/assemble_context.py ccdd/context.json "tarea de ejemplo"` → exit 0 con
  reporte de slots; 2 invocaciones idénticas → stdout byte a byte idéntico.
- [ ] Tarea citando un nodo inexistente → hallazgo de `reference_check` en el reporte.
- [ ] Todo nodo nuevo de `knowledge/` OKF-válido y enlazado desde `index.md`.
- [ ] CI (`validate.yml`) con el paso nuevo, coherente con los pasos existentes.

## Restricciones

- E-ASSEMBLE toca SOLO: `scripts/assemble_context.py`, `ccdd/context.json`,
  `tests/test_assemble_context.py`, `.github/workflows/validate.yml` (solo agregar paso).
  NO toca `scripts/validate_contracts.py`, `src/`, tests existentes, nodos existentes.
- Python stdlib puro; sin red; sin subprocess; sin LLM.
- NO commitear (el PM commitea por tarea verificada). Si algo no se puede sin romper otro
  criterio, PARAR y reportar.
