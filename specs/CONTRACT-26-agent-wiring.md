# Contrato 26 — Cableado de agentes: el triángulo agente↔skills↔MCP como contrato

Prerrequisitos: contratos 01-25 cerrados, HEAD `6135f87`, suite 315 verde 2×, CI verde en
ambas patas. Octavo dominio de la vertiente rule-contract, y la medición de una clase de
frontera NUEVA: integridad referencial bajo cuantificación.

RECON (2026-07-08): NO existe ningún archivo de definición de agente — ni
`~/.claude/agents/` en la máquina del usuario ni `.claude/agents/` en el repo. La "capa 1"
(gate de definiciones estilo C24) queda SIN activo real que custodiar: construirla hoy
sería especulativa y viola la doctrina evidencia-primero. Este contrato cubre la capa 2 —
el CABLEADO: qué agente usa qué skills, qué servidores MCP, con qué modelo y qué política
de re-delegación — modelado sobre el flujo real de la metodología (PM nativo, devs
efímeros haiku, máximo 2 re-delegaciones), con datos SINTÉTICOS. La capa 1 queda anotada
en el nodo para cuando exista el activo; la capa 3 (comportamiento del agente) NO es
contratable determinísticamente y es la tesis de CCDD: se contrata el artefacto que el
agente produce, no al agente.

> Capa: contrato de ejecución. T1 (código, dev efímero) va contra el oráculo congelado
> `tests/test_check_wiring.py` (autorado y sellado por el PM). T2 (datos + nodo +
> manifest) es del orquestador. Todos los artefactos del dominio son EJEMPLO (MANIFEST).

Frontera medida (y por qué se cierra por código):
- "Toda skill referenciada en `agent_skills` debe EXISTIR en `skills_registry`" (ídem
  servidores MCP y agentes declarados) es una REFERENCIA CRUZADA entre colecciones bajo
  `each`. La familia `refs` opera sobre campos del record top-level, no sobre elementos de
  una lista; `refs`-dentro-de-`each` sería una familia nueva y esta es su PRIMERA
  aparición ⇒ por doctrina NO se agrega familia: la frontera se declara `code_only` y se
  cierra con un task contract de código (precedente exacto: C22, ciclos de grafo).

Decisiones de diseño (fijadas acá):
- **Record del dominio** (forma auditoría, plano):
  `{agents: [{name, model, max_redelegations?}], skills_registry: [nombres],
  mcp_registry: [nombres], agent_skills: [{agent, skill}], agent_mcp: [{agent, server}]}`.
- **Reglas declarativas** (`agent-wiring.rules.json`): `agents` presente; `each agents`:
  `name`+`model` presentes, `name` kebab (`matches`), `model` en
  `{haiku, sonnet, opus, fable}`, `max_redelegations` number con bounds [0, 2] (la
  política real de la metodología); `each agent_skills`: `agent`+`skill` presentes;
  `each agent_mcp`: `agent`+`server` presentes. `code_only`: integridad referencial de
  `agent_skills` y `agent_mcp` (razón: refs bajo each, primera aparición de la clase).
- **Cierre por código** (T1): `src/check_agent_wiring.py` con
  `def check_agent_wiring(record) -> list` — violaciones canónicas
  `"agent_skills: entrada <i>: skill '<x>' no registrada"` /
  `"...: agente '<y>' no declarado"` (ídem `agent_mcp` con server), orden determinista.
  Entradas con campo ausente se SALTAN (eso lo cubre la regla declarativa `required`):
  el checker hace SOLO existencia referencial — separación limpia dato/código.
- Golden sellado; el caso FRONTERA ejercita `code_only_miss` Y el PM cross-checkea que el
  checker lo atrape (patrón C21/C22).

## T1 — `check_agent_wiring` (dev efímero)

OBJETIVO: implementar `src/check_agent_wiring.py` contra el oráculo congelado
`tests/test_check_wiring.py` (válido vacío; skill no registrada; server no registrado;
agente no declarado en ambas colecciones; registros vacíos; campos ausentes se saltan;
mensajes canónicos con índice y nombre; orden determinista; nunca lanza con record raro).
Task contract: `knowledge/contracts/check-agent-wiring.md` (sellado). Stdlib puro, ASCII.

## T2 — Dominio agent-wiring (autoría del orquestador)

`knowledge/data_models/agent_wiring.md` (las 3 capas honestas: definiciones = sin activo
real hoy; cableado = este contrato; comportamiento = CCDD mismo);
`examples/rules/agent-wiring.rules.json` + `examples/rules/agent-wiring-golden.json`
(sellado; caso FRONTERA con `code_only_miss`); artefactos + checker + oráculo al MANIFEST;
index enlazado; CHANGELOG.

## Criterios de aceptación

- [ ] `python -m unittest tests/test_check_wiring.py` verde SIN modificar el oráculo.
- [ ] `python scripts/validate_rules.py examples/rules` exit 0 con 6 rule-sets y REPRO
  verde sobre el golden nuevo.
- [ ] Cross-check PM: el caso FRONTERA del golden (skill fantasma), invisible para el
  declarativo (`code_only_miss`), es ATRAPADO por `check_agent_wiring` con el mensaje
  canónico.
- [ ] Mutación PM (sobre copia): skill fantasma agregada al caso válido del golden
  (re-sellado) → REPRO exit 1.
- [ ] Goldens previos (5) byte-INTACTOS; los 6 gates exit 0; suite 2× verde; post-init
  neutral con los artefactos nuevos en MANIFEST.
- [ ] Final: CI verde en ambas patas.

## Restricciones

- Tocar SOLO — T1 (dev): `src/check_agent_wiring.py` (+ su REPORT local). T2
  (orquestador): `tests/test_check_wiring.py` (nuevo, congelado),
  `knowledge/contracts/check-agent-wiring.md` (nuevo, sellado),
  `knowledge/data_models/agent_wiring.md` (nuevo), `knowledge/index.md` (enlace),
  `examples/rules/agent-wiring.rules.json` + `examples/rules/agent-wiring-golden.json`
  (nuevos), `scripts/init_project.py` (SOLO MANIFEST), `CHANGELOG.md`, el spec y el
  reporte.
- El motor, los gates y sus oráculos NO se tocan (C26 no agrega familias: esa es la
  decisión). Goldens y rule-sets previos: canarios read-only.
- Los specs `CONTRACT-01..25` y sus reportes son históricos: read-only.
- Python stdlib puro; sin red; sin LLM; mensajes ASCII; determinista.
- NO commitear hasta verificar. Si algo no se puede sin romper otro criterio, PARAR y
  reportar.
- ABORTAR SI: la separación "declarativo = presencia, código = existencia referencial"
  resultara imposible de sostener sin duplicar checks (hallazgo de diseño); o el REPRO
  exigiera tocar un golden previo. PARAR, documentar y marcar BLOQUEADO.

## Checklist antes de delegar

- [x] RECON corrido (2026-07-08): sin definiciones de agente reales en ninguna ubicación
  — capa 1 EXCLUIDA por evidencia-primero y anotada en el nodo; el cableado se modela
  del flujo real de la metodología (haiku, máx 2 re-delegaciones) con datos sintéticos.
- [x] Frontera nueva medida y clasificada: integridad referencial bajo cuantificación
  (refs-en-each), primera aparición ⇒ code_only + cierre por código (precedente C22),
  familia solo si la clase repite.
- [x] Todo criterio tiene comando + resultado esperado.
- [x] Red-team hecho: el checker NO duplica `required` (entradas incompletas se saltan);
  mensajes canónicos fijados en el oráculo para que el cross-check sea exacto; mutación
  con re-sellado en copia para aislar REPRO del sello (lección C25: la mutación solo
  cuenta si su aplicación es observable).
- [x] Perímetro declarado; una tarea de código (T1); datos del orquestador (T2).
- [x] Condiciones de aborto explícitas.
