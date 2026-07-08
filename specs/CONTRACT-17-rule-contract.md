# Contrato 17 — Rule contract: validar reglas de negocio como datos, no solo código

Prerrequisitos: contratos 01-16 cerrados, HEAD sincronizado, suite verde 2×, CI verde en
ambas patas. C16 dejó `validate-payment-limit` como reglas de compliance expresadas en
**código** (función pura + oráculo de tests). Este contrato abre una **vertiente nueva**:
expresar las mismas reglas como **datos declarativos** verificados por un checker
determinista sin LLM, siguiendo el patrón probado en `MauricioPerera/game-protocol` (sus
`profiles/*.json` validan reglas de género —`refs/bounds/enums`— como datos puros; su
`papers-please` modela control de fronteras, estructuralmente idéntico a compliance de
pagos). Es un **experimento falsable**, no una promesa: la entrega incluye el veredicto
honesto de qué reglas de pago caben como datos y cuáles no.

> Capa: contrato de ejecución. La tarea de código (T1) lleva su task contract CCDD en
> `knowledge/contracts/validate-rules.md`. El formato del rule contract se documenta en el
> nodo `knowledge/rule-contract-spec.md`.

Decisiones de diseño (fijadas acá, no las decide el dev):
- **Infra vs. ejemplo.** El motor (`scripts/rule_engine.py` + tests) y el nodo de formato
  son infraestructura permanente. El rule-set de pagos + su golden set + el test de
  equivalencia son **artefactos de EJEMPLO** (van al `MANIFEST` de `init_project`, se
  eliminan al instanciar) — la vertiente queda, el dominio no ata la plantilla.
- **La frontera dato/lógica es un ENTREGABLE, no un fracaso.** game-protocol la reconoce
  explícito; C17 la mide sobre el dominio de pagos y la documenta.

## T1 — Motor de reglas declarativo (`scripts/rule_engine.py`)

OBJETIVO: `def evaluate(ruleset: dict, record: dict, refs: dict) -> list:` que evalúa un
`record` contra un `ruleset` declarativo y devuelve la lista de violaciones legibles
(vacía = válido), ordenada deterministamente. Familias declarativas soportadas (paridad
game-protocol + las extensiones "keyed" que el dominio de pagos exige):
`required`, `type` (number/string/dict, con `number` excluyendo bool),
`enums` (conjunto cerrado, admite `[true]` para verificación exacta),
`bounds` (`gt/min/max/integer` sobre un campo), `refs` (un campo debe existir como clave en
una colección de `refs`), y `keyed_bounds`/`keyed_enums` (el tope/conjunto permitido se
busca en una tabla de `refs` por el valor de otro campo del record — p. ej. el límite por
país). Python stdlib puro; sin red; sin subprocess; sin LLM; determinista; mensajes ASCII
(lint de C13). Funciones chicas dentro del budget declarado en el task contract. El oráculo
`tests/test_rule_engine.py` lo autora el orquestador ANTES de delegar y queda congelado
(`tests_sha256`); el implementador solo escribe `scripts/rule_engine.py`.

## T2 — Reexpresar pagos como datos + prueba de equivalencia (autoría del orquestador)

OBJETIVO (lo cablea el orquestador, no un dev): `examples/rules/payment-compliance.rules.json`
(las reglas de `knowledge/data_models/payment_limits.md` como rule-set declarativo),
`examples/rules/payment-golden.json` (golden set congelado de pagos ya decididos: record +
violaciones esperadas), y `tests/test_payment_rules_equivalence.py` que corre, sobre CADA
caso del golden, el checker declarativo (`rule_engine` sobre el rule-set) Y el validador de
código (`src/payment_limit.py` de C16), y exige que produzcan las MISMAS violaciones. Toda
regla que el rule-set NO pueda expresar declarativamente se declara explícita en un campo
`code_only` del rule-set con su razón; el test la exceptúa de la equivalencia y el REPORT la
nombra. La frontera documentada ES el resultado del experimento.

## Criterios de aceptación

- [ ] `python -m unittest tests/test_rule_engine.py` verde (oráculo congelado, sin
  modificarlo).
- [ ] `python -m unittest tests/test_payment_rules_equivalence.py` verde: declarativo y
  código coinciden en todo el golden, salvo las reglas marcadas `code_only`.
- [ ] `python scripts/validate_contracts.py knowledge/contracts` exit 0 (task contract
  `validate-rules.md` con su sello vigente) y `python scripts/validate_okf.py knowledge`
  exit 0 (nodo `rule-contract-spec.md` enlazado desde `index.md`, sin huérfanos).
- [ ] `python scripts/validate_specs.py specs` exit 0 y `python scripts/lint_ascii.py
  scripts` exit 0.
- [ ] `python -m unittest discover -s tests -p "test_*.py"` suite completa 2× verde,
  incluyendo `tests/test_init_project.py`: post-init, el rule-set/golden/equivalencia de
  pagos se eliminan con el manifiesto y los gates quedan verdes (la plantilla queda neutral;
  el motor y el nodo de formato permanecen).
- [ ] El REPORT nombra, con evidencia, qué reglas de pago caben como datos y cuáles
  quedaron `code_only` y por qué (la frontera dato/lógica medida).
- [ ] Final: CI verde en ambas patas.

## Restricciones

- Tocar SOLO — T1 (dev): `scripts/rule_engine.py` (+ su REPORT en `.agents/logs/`).
  Todo lo demás (oráculo del motor, rule-set de pagos, golden, test de equivalencia, nodo
  de formato, task contract, index, MANIFEST, CHANGELOG, spec, reporte) lo autora/cablea el
  orquestador.
- Los specs `CONTRACT-01..16` y sus reportes son históricos: read-only.
- Python stdlib puro en el motor; sin red; sin subprocess; sin LLM; mensajes ASCII.
- El golden set y el oráculo del motor quedan congelados por `tests_sha256`: el
  implementador no los toca.
- NO commitear (el PM commitea la tarea verificada). Si algo no se puede sin romper otro
  criterio, PARAR y reportar.
- ABORTAR SI: expresar una regla de pago como datos exigiera lógica no-uniforme que ninguna
  familia declarativa cubre y forzarla degradaría el motor a un intérprete ad-hoc -> se
  marca `code_only` y se documenta, NO se fuerza (esa es la frontera, no un fallo); o si el
  golden set no pudiera fijarse sin acoplar el checker declarativo a la implementación de
  código (deben ser oráculos independientes). PARAR, documentar con evidencia en el reporte
  y marcar BLOQUEADO.

## Checklist antes de delegar

- [x] RECON corrido (2026-07-08): game-protocol leído entero; familias declarativas
  (`refs/bounds/enums`) confirmadas en `profiles/quiz.json` (pure-data) y `papers-please.js`
  (reglas de frontera); la frontera dato/lógica está declarada por el propio repo ("un type
  nuevo exige código, eso es logica no dato"). `src/payment_limit.py` y `payment_limits.md`
  existen en KDD (C16). Sin conteo hardcodeado del manifiesto en los tests.
- [x] Todo criterio de aceptación tiene comando + resultado esperado.
- [x] Red-team hecho: la prueba de equivalencia contra el código de C16 impide un checker
  declarativo "decorativo" que diga verde sin validar; el campo `code_only` obliga a
  declarar la frontera en vez de fingir cobertura total; el golden set congelado impide que
  el dev afloje el oráculo; oráculo del motor y validador de código son independientes (no
  se importan entre sí).
- [x] Perímetro declarado; una sola tarea de código (T1); el resto lo cablea el orquestador.
- [x] Condiciones de aborto explícitas.
