# Contrato 02 — El ensamblador de contexto como paso estándar de las reglas de agentes

Prerrequisitos: Contrato 01 completado (ensamblador `scripts/assemble_context.py` +
`ccdd/context.json` operativos, 38 tests verdes). Hoy las reglas de agentes
(`.agents/AGENTS.md`, skill `kdd-okf-ccdd-hybrid`) no mencionan el ensamblador: un agente
que clona el repo no sabe que existe ni que debe usarlo. Este contrato lo ancla como paso
obligatorio del flujo de delegación, con un test de coherencia que impide que la regla y la
herramienta se desincronicen.

> Capa: contrato de ejecución. La tarea lleva su task contract CCDD en
> `knowledge/contracts/agents-context-rule.md`.

## A-RULE (T1) — regla en AGENTS.md + skill + test de coherencia

OBJETIVO:
1. `.agents/AGENTS.md` gana una regla nueva (numerada, estilo de las existentes):
   **Contexto presupuestado (CCDD Nivel 2)** — antes de implementar una tarea delegada, el
   agente ensambla su contexto con `python scripts/assemble_context.py ccdd/context.json
   "<tarea>" [-v]`; el reporte de slots/guardrails forma parte de la evidencia que se pega
   en `.agents/logs/<task>-REPORT.md`; un guardrail `on_fail: abort` (exit 2) bloquea la
   tarea hasta resolverlo. Sin duplicar la doc del ensamblador: referencia por ruta.
2. `.agents/skills/kdd-okf-ccdd-hybrid/SKILL.md` gana una sección corta (numerada a
   continuación de las existentes) que integra el paso de ensamblado en el flujo de
   definición/delegación de contratos — coherente con la regla de AGENTS.md, sin duplicar.
3. `tests/test_agents_rules.py` (nuevo): test de coherencia que fija la regla — asserts:
   `.agents/AGENTS.md` y `SKILL.md` referencian `scripts/assemble_context.py` y
   `ccdd/context.json`; ambos archivos referenciados existen; el comando citado en
   AGENTS.md usa el contrato real (`ccdd/context.json`). Si mañana alguien renombra el
   script o el contrato sin actualizar las reglas, la suite se pone roja.
4. Los puentes raíz (`AGENTS.md`, `CLAUDE.md`) NO se tocan (son espejos, no duplican).

## Criterios de aceptación

- [ ] `python scripts/validate_contracts.py knowledge/contracts` exit 0 (incluye el task
  contract nuevo).
- [ ] `python -m unittest discover -s tests -p "test_*.py"` verde (38 + los nuevos), 2× al
  cierre.
- [ ] Revertir mentalmente la regla (quitar la mención del script) rompería
  `test_agents_rules.py` — el test la fija de verdad, no es decorativo.
- [ ] CI verde sin cambios en `validate.yml` (el discover ya recoge el test nuevo).

## Restricciones

- Tocar SOLO: `.agents/AGENTS.md`, `.agents/skills/kdd-okf-ccdd-hybrid/SKILL.md`,
  `tests/test_agents_rules.py`. NO tocar scripts/, ccdd/, src/, tests existentes,
  knowledge/ (el task contract lo autora el orquestador), README, puentes raíz.
- stdlib puro; sin red; sin subprocess en el test (leer archivos basta).
- NO commitear. Si algo no se puede sin romper otro criterio, PARAR y reportar.
