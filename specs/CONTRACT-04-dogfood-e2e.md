# Contrato 04 — Dogfood E2E: una feature real por el ciclo KDD completo

Prerrequisitos: Contratos 01-03 (60 tests, 3 gates en CI). Este contrato ejecuta el ciclo
completo de la plantilla sobre una feature real y queda como **caso resuelto de
referencia** para quien la clone: task contract anclado a un nodo de la KB → tests
congelados autorados ANTES de delegar → contexto ensamblado (regla 7) → agente efímero
implementa SOLO producción → gates nivel 1 → reporte verificado.

> Diferencia deliberada con C01-C03: acá los tests los autora el ORQUESTADOR y quedan
> congelados antes de la delegación (CCDD canónico: el implementador nunca escribe ni
> modifica su propio oráculo). En los contratos de tooling el dev escribía sus tests;
> para features de producto, el oráculo es independiente.

## F-USERS (T1) — `validate_user_record` anclada al modelo de datos

OBJETIVO: `src/users.py` con `def validate_user_record(record: dict) -> list:` que valida
un registro contra las **restricciones de dominio y campos** declarados en
`knowledge/data_models/users_table.md` (el task contract ENLAZA el nodo, no lo duplica —
regla 3 de la skill). Devuelve lista de violaciones legibles (vacía = válido). El detalle
normativo de qué se valida vive en el task contract
`knowledge/contracts/validate-user-record.md` y en los tests congelados
`tests/test_users.py` (autorados por el orquestador, INTOCABLES para el implementador).

## Criterios de aceptación

- [ ] `python -m unittest tests/test_users.py` verde SIN modificar el archivo de tests
  (diff vacío sobre tests/ al cierre).
- [ ] `python scripts/validate_contracts.py knowledge/contracts` exit 0 y
  `python scripts/validate_okf.py knowledge` exit 0.
- [ ] Suite completa verde 2× al cierre.
- [ ] Evidencia del ensamblador (regla 7) en el REPORT del agente.
- [ ] El caso queda documentado como referencia en `docs/reports/CONTRACT-04-REPORT.md`.

## Restricciones

- El implementador toca SOLO `src/users.py` (+ su REPORT en `.agents/logs/`). Tests,
  contratos, KB, scripts y CI: intocables para él.
- Python stdlib puro; sin red; sin subprocess; sin `re`? — `re` SÍ está permitido (es
  stdlib y el dominio pide patrones); prohibidos red/subprocess/IO de archivos.
- NO commitear (el PM commitea el batch completo verificado).
