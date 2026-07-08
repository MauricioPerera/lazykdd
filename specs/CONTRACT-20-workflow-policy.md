# Contrato 20 — Workflows como dominio + familia `each` (cuantificación sobre colecciones)

Prerrequisitos: contratos 01-19 cerrados, release v1.1.0, HEAD `d539df7`, suite 233 verde
2×, CI verde en ambas patas. Tercer dominio de la vertiente rule contract: **política de
workflows/automatizaciones** (forma del JSON de n8n: settings escalares + array de nodos).
RECON (2026-07-08, ejecutado): las reglas ESCALARES del workflow caben en las familias
actuales; las reglas POR NODO ("todo httpRequest tiene timeout", "sin credenciales
inline") NO — y peor: expresarlas con paths punteados produce **falsos positivos en todo
workflow** (el motor trata una lista intermedia como ausente). Es la segunda clase de
frontera medida (∀ sobre colecciones), distinta de la cross-field de C17/C19.

**La evidencia para extender ya está**: 3 dominios, 2 clases de frontera, y una de las dos
la resuelven declarativamente las familias de game-protocol (que son `{collection, field}`
nativas). Este contrato agrega la familia `each` al motor CON esa evidencia — el criterio
"evidencia antes que feature" se cumple, no se esquiva.

> Capa: contrato de ejecución. T1 (código, dev efímero) lleva su task contract en
> `knowledge/contracts/validate-rules.md` (el del motor, con oráculo ACTUALIZADO y
> re-sellado por el orquestador ANTES de delegar). T2 (dominio como datos) es autoría del
> orquestador, verificada por el gate (regla REPRO).

Decisiones de diseño (fijadas acá):
- **Familia `each` (v1 mínima)**: `{"collection": "<campo lista>", "where": {"field",
  "equals"}?, "rules": {subset interno}}`. El subset interno v1: `required`, `type`,
  `enums`, `bounds` (sin `refs`/`keyed_*` internos — se agregan si un dominio los pide;
  documentado en el nodo de formato). Semántica: se evalúan las `rules` sobre CADA
  elemento (filtrado por `where` si está); toda violación se emite con el prefijo del
  nombre de la colección (`"nodes: elemento 2 (httpRequest): parameters.timeout ..."`) —
  así el campo top-level del golden es la colección. Colección ausente o no-lista → se
  salta (la presencia la exige un `required` top-level aparte); elemento no-dict → una
  violación de la colección.
- **Fixtures sintéticos** con la forma real del JSON de n8n (nodos con
  `type/parameters/credentials`, `settings.error_workflow`, `settings.execution_timeout`,
  `environment`) — la plantilla pública no se acopla a una instancia real.
- **La frontera restante se sigue declarando**: "sin ciclos entre nodos" (recorrido de
  grafo) queda `code_only` — tercera clase (propiedad global del grafo), no se fuerza.

## T1 — Familia `each` en el motor (dev efímero)

OBJETIVO: `scripts/rule_engine.py` gana la familia `each` con la semántica de arriba,
contra el oráculo ACTUALIZADO `tests/test_rule_engine.py` (nuevos casos: `each` con
`required`/`enums`/`bounds` internos, `where` filtrando por tipo, prefijo de colección en
la violación, colección ausente/no-lista se salta, elemento no-dict, determinismo).
`scripts/validate_rules.py` reconoce `each` como familia conocida (una línea en su lista)
y su regla REPRO la ejercita vía el motor sin cambios adicionales. Las familias existentes
quedan byte-compatibles (los goldens de pagos y fronteras NO cambian y deben seguir
reproduciéndose).

## T2 — Dominio workflow-policy (autoría del orquestador)

OBJETIVO: `knowledge/data_models/workflow_policy.md` (Data Model, indexado: el record, el
mapeo regla→familia con `each` incluido, y las fronteras `code_only` del dominio);
`examples/rules/workflow-policy.rules.json` (escalares: error_workflow requerido, timeout
acotado por entorno vía `keyed_bounds`, entorno vía `refs`; por-nodo vía `each`: todo
httpRequest con `parameters.timeout`, ningún nodo con `credentials_inline`, tipos de nodo
permitidos; `code_only`: ciclos del grafo) + `examples/rules/workflow-golden.json` (≥10
workflows sintéticos decididos, sellado). Los 3 artefactos al `MANIFEST`.

## Criterios de aceptación

- [ ] `python -m unittest tests/test_rule_engine.py` verde (oráculo actualizado y
  re-sellado por el orquestador, SIN que el dev lo toque).
- [ ] `python scripts/validate_rules.py examples/rules` exit 0 con
  `Resumen: 0 error(es) en 3 archivo(s)` (pagos + fronteras byte-intactos + workflows).
- [ ] `python -m unittest tests/test_payment_rules_equivalence.py` verde (regresión: la
  familia nueva no altera las existentes).
- [ ] Mutación PM (sobre copia): workflow con un httpRequest sin timeout en el golden
  marcado como válido → `REPRO`; golden aflojado → `GOLDEN_FROZEN`.
- [ ] `python scripts/validate_contracts.py knowledge/contracts` exit 0 (sello del oráculo
  del motor vigente), `python scripts/validate_okf.py knowledge` exit 0,
  `python scripts/validate_specs.py specs` exit 0, `python scripts/lint_ascii.py scripts`
  exit 0.
- [ ] `python -m unittest discover -s tests -p "test_*.py"` suite completa 2× verde
  (incluye `test_init_project`: post-init el dominio de workflows se elimina con el
  manifiesto).
- [ ] Final: CI verde en ambas patas.

## Restricciones

- Tocar SOLO — T1 (dev): `scripts/rule_engine.py`, `scripts/validate_rules.py` (SOLO la
  lista de familias conocidas) (+ su REPORT en `.agents/logs/`). T2 (orquestador): el
  oráculo del motor + re-sello en `knowledge/contracts/validate-rules.md`,
  `knowledge/rule-contract-spec.md` (fila `each` + subset interno documentado),
  `knowledge/data_models/workflow_policy.md` (nuevo), `knowledge/index.md` (enlace),
  `examples/rules/workflow-policy.rules.json` y `workflow-golden.json` (nuevos),
  `scripts/init_project.py` (MANIFEST), `CHANGELOG.md`, el spec y el reporte.
- Los goldens de pagos y fronteras NO se tocan (regresión por REPRO).
- Los specs `CONTRACT-01..19` y sus reportes son históricos: read-only.
- Python stdlib puro; sin red; sin LLM; mensajes ASCII; determinista.
- NO commitear hasta verificar. Si algo no se puede sin romper otro criterio, PARAR y
  reportar.
- ABORTAR SI: `each` no pudiera implementarse sin romper la byte-compatibilidad de las
  familias existentes (los 2 goldens previos son el canario), o el subset interno v1
  resultara insuficiente hasta para las reglas por-nodo del propio dominio (eso invalida
  el diseño, no se parchea con hacks). PARAR, documentar con evidencia y marcar BLOQUEADO.

## Checklist antes de delegar

- [x] RECON corrido (2026-07-08, salidas reales): escalares del workflow funcionan con las
  familias actuales; reglas por-nodo con path punteado producen falsos positivos SIEMPRE
  (lista intermedia = ausente) — la frontera es real y filosa, no teórica. Las familias de
  game-protocol son collection-based: el patrón declarativo para ∀ existe y está probado.
- [x] Todo criterio tiene comando + resultado esperado.
- [x] Red-team hecho: los goldens previos intactos actúan de canario de regresión vía
  REPRO; el prefijo de colección en las violaciones mantiene el matching top-level del
  golden sin tocar el gate; "ciclos de grafo" va `code_only` para no inflar `each` con
  lógica de grafos; el `where` por igualdad simple evita meter un mini-lenguaje de queries.
- [x] Perímetro declarado; una tarea de código (T1) y cableado del orquestador (T2).
- [x] Condiciones de aborto explícitas.
