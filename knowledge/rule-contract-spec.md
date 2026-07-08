---
type: 'Concept'
title: 'Rule contract: reglas de negocio como datos'
description: 'Formato de un rule contract KDD: reglas de dominio expresadas como datos declarativos y verificadas por un checker determinista sin LLM, con golden set congelado.'
tags: ['rule-contract', 'ccdd', 'reglas', 'declarativo', 'reference']
---

# Rule contract — reglas de negocio como datos

Vertiente de KDD que complementa al task contract (que verifica **código**): un rule
contract verifica **reglas de negocio** de forma determinista, expresándolas como **datos**
en vez de código. Linaje directo del patrón de `MauricioPerera/game-protocol`, cuyos
`profiles/*.json` validan reglas de género como datos puros (`refs/bounds/enums`) cargados
sin ejecutar código. Contexto de la metodología: [metodologia-ejecucion](./metodologia-ejecucion.md).

## Piezas

- **Rule-set** (datos): un objeto con las familias declarativas de abajo. No es código; se
  carga con `json.load`, nunca se ejecuta.
- **Refs** (datos): tablas auxiliares contra las que se resuelven las reglas keyed (p. ej.
  los límites por país).
- **Motor** (`scripts/rule_engine.py`): `evaluate(ruleset, record, refs) -> list` — checker
  determinista, stdlib puro, sin LLM ni red; devuelve las violaciones de un record.
- **Golden set** (oráculo congelado): casos ya decididos (record + violaciones esperadas)
  sellados por `tests_sha256`. Es la evidencia de que el rule-set dice lo que debe.

## Familias declarativas

| Familia        | Qué exige                                                              |
|----------------|-----------------------------------------------------------------------|
| `required`     | campos presentes y no vacios.                                         |
| `type`         | tipo del campo (`number` excluye bool; `string`; `dict`).            |
| `enums`        | valor en un conjunto cerrado (admite `[true]` para exactitud).       |
| `bounds`       | `gt`/`min`/`max`/`integer` sobre un campo numerico.                  |
| `refs`         | un campo debe existir como clave en una coleccion de `refs`.        |
| `keyed_bounds` | el tope de un campo se busca en una tabla `refs` por otro campo.    |
| `keyed_enums`  | el conjunto permitido de un campo depende de otro campo (via `refs`).|

## Frontera dato/logica (honesta)

No toda regla es dato. game-protocol lo declara explicito: un `type` de regla nuevo exige
codigo en el motor ("eso es logica, no dato"). Un rule contract marca esas reglas con
`code_only` y su razon; quedan fuera del rule-set y se validan por codigo (task contract).
La frontera documentada ES parte del contrato, no un fallo: dice donde termina lo
declarativo para ese dominio.

## Conformidad

Un rule contract es valido si: el rule-set solo usa familias soportadas o marca
`code_only`; el motor sobre el rule-set reproduce el golden set congelado; y las reglas
`code_only` estan documentadas con su razon.
