---
type: 'Task Contract'
title: 'TUI: Parse contracts status JSON a struct (lista navegable)'
description: 'Variante estructurada de SummarizeContractsStatus: una funcion pura ParseContractsStatus que parsea el JSON de contracts status --json a []ContractStatus (task + lifecycle), para alimentar la lista navegable del TUI.'
tags: ['ccdd', 'tui', 'lazykdd', 'go', 'contracts']

task: kdd-contracts-list-parse
intent: "Parsear el JSON de contracts status --json a un slice estructurado de ContractStatus ordenado por task."
language: go
target: tui/internal/kdd/contracts_list.go
signature: "func ParseContractsStatus(data []byte) ([]ContractStatus, error)"
test_command: "go test -C tui ./..."
test_cwd: ../..
budget:
  cyclomatic_max: 14
  nesting_max: 3
  params_max: 1
  lines_max: 70
tests: "tui/internal/kdd/contracts_list_test.go"
tests_sha256: "a73837bc210b18e7cddefc0d3c2be2d08dec7b0be836ad12b4f2599aff901ec5"
touch_only: ['tui/internal/kdd/contracts_list.go']
deps_allowed: []
forbids: ['network', 'llm']
---

# Contract: TUI `ParseContractsStatus` (Piel 3, Go)

## Intent
Pieza del segundo panel del TUI de lazykdd (Piel 3, Go): una unica funcion
pura `ParseContractsStatus(data []byte) ([]ContractStatus, error)` en el
paquete `kdd` que consume el JSON crudo que emite `python scripts/kdd_cli.py
contracts status --json` ([kdd-contracts-status-json](./kdd-contracts-status-json.md))
y devuelve los datos ESTRUCTURADOS (no un string formateado) para que
`UpdateModel`/`View` en [tui-bubbletea-model](./tui-bubbletea-model.md) armen
la lista NAVEGABLE de contratos (cursor arriba/abajo, Enter muestra el .md
completo). Es la variante estructurada de
[SummarizeContractsStatus](./kdd-contracts-status-summarize.md) (que arma un
string plano): mismo parseo/validacion, mismo orden defensivo, misma
lista-vacia-es-valida. No usa Bubble Tea (este paquete `kdd` no lo necesita).

## Interface
```go
type ContractStatus struct {
    Task      string
    Lifecycle string
}

func ParseContractsStatus(data []byte) ([]ContractStatus, error)
```
`data` es el JSON crudo de `contracts status --json`: una lista de objetos
`{"task": string, "lifecycle": string}` (una entrada por contrato real del
repo; `lifecycle` es uno de `draft`/`validated`/`implemented`/`verified`).

- Si `data` NO es JSON valido, o el top-level NO es una lista (o es `null`), o
  algun elemento de la lista NO es un objeto con AL MENOS las claves `task` y
  `lifecycle` como string (numero/bool/null/objeto/array rechazados): devuelve
  `(nil, err)` con `err` no nil (`fmt.Errorf` o el error nativo de
  `encoding/json`; sin tipo de error custom).
- Si `data` es valido (incluida una lista VACIA, que es exito): devuelve un
  slice de `ContractStatus` con una entrada por elemento, en orden ALFABETICO
  por `Task` (no confiar en que el JSON ya venga ordenado — se ordena uno mismo
  con `sort.Slice`, mismo criterio defensivo que `Summarize`). Una lista vacia
  (`[]`) devuelve un slice de longitud 0 (no nil) y error nil.
- La funcion es PURA: sin I/O, sin red, sin `os.Exit`, nunca paniquea (un JSON
  malformado es un `error` devuelto, NUNCA un panic).

## Invariants
- Para input invalido (no JSON, top-level no lista o `null`, elemento no objeto
  o `null`, elemento sin `task` o sin `lifecycle`, o `task`/`lifecycle` de tipo
  no-string incluido `null`), el primer retorno es SIEMPRE `nil` y el segundo
  no nil; nunca panic.
- Para input valido, el slice SIEMPRE tiene `len == len(lista)` y los elementos
  siguen orden alfabetico determinista por `Task` (independiente del orden de
  aparicion en el JSON).
- Una lista vacia (`[]`) devuelve un slice de longitud 0 (NO nil) y error nil:
  el caller itera sin nil-check extra.
- Un elemento con claves EXTRA (mas alla de `task`/`lifecycle`) es valido: se
  acepta con tal de tener AL MENOS `task` y `lifecycle` como string.
- 100% stdlib de Go (`encoding/json`, `fmt`, `sort`); cero modulos externos,
  cero I/O, cero red. SIN Bubble Tea (este paquete `kdd` no lo necesita).

## Examples
- `ParseContractsStatus([]byte(`[{"task":"zeta","lifecycle":"draft"},{"task":"alpha","lifecycle":"verified"}]`))` -> `[]ContractStatus{{"alpha","verified"},{"zeta","draft"}}` (orden alfabetico).
- `ParseContractsStatus([]byte(`[]`))` -> `[]ContractStatus{}` (slice vacio, no nil), error nil.
- `ParseContractsStatus([]byte(`[{"task":"a","lifecycle":"draft","extra":42}]`))` -> `[]ContractStatus{{"a","draft"}}` (claves extra se aceptan).
- `ParseContractsStatus([]byte(`{"task":"a","lifecycle":"draft"}`))` -> `(nil, err)` (top-level objeto, no lista).
- `ParseContractsStatus([]byte(`null`))` -> `(nil, err)` (top-level null).
- `ParseContractsStatus([]byte(`[1,2,3]`))` -> `(nil, err)` (elemento no objeto).
- `ParseContractsStatus([]byte(`[{"lifecycle":"draft"}]`))` -> `(nil, err)` (falta task).
- `ParseContractsStatus([]byte(`[{"task":1,"lifecycle":"draft"}]`))` -> `(nil, err)` (task no string).
- `ParseContractsStatus([]byte(`[{"task":null,"lifecycle":"draft"}]`))` -> `(nil, err)` (task null no es string).
- `ParseContractsStatus([]byte(`not json`))` -> `(nil, err)` (JSON invalido, sin panic).

## Do / Don't
- DO: dos pasadas de `json.Unmarshal` — primero sobre `[]json.RawMessage`
  para validar que el top-level sea una lista (unmarshal sobre slice rechaza
  objeto/numero/string/bool), luego por cada elemento sobre
  `map[string]json.RawMessage` para detectar presencia de `task`/`lifecycle`
  y validar que cada una sea string. Mismo patron que `SummarizeContractsStatus`.
- DO: detectar `null` explicitamente en tres niveles (top-level via
  `raws == nil`, elemento via `obj == nil`, campo via puntero `*string` que
  queda nil al deserializar `null`): null nunca es lista / objeto / string
  valido. Mismo criterio defensivo que `Summarize`.
- DO: deserializar `task`/`lifecycle` con `*string` (no `string`): distingue
  `null` (nil, error) de un string vacio legitimo `""` (valido), y rechaza
  numero/bool/objeto/array via error nativo de `json`.
- DO: ordenar las entradas con `sort.Slice` por `Task` antes de devolver
  (determinismo).
- DO: devolver `make([]ContractStatus, 0, len(raws))` para que la lista vacia
  sea un slice de longitud 0 (no nil), no un slice nil.
- DON'T: inventar un tipo de error custom; usa `fmt.Errorf` (con `%w` donde
  envuelvas un error de `json`) o el error nativo de `encoding/json`.
- DON'T: agregar Bubble Tea, I/O, ni mas funciones de las estrictamente
  necesarias. Solo `ContractStatus` y `ParseContractsStatus`.
- DON'T: tocar `tui/internal/kdd/contracts.go`, `contracts_test.go`, su
  contrato `kdd-contracts-status-summarize.md`, `tui/internal/kdd/gates.go`,
  `scripts/`, ni nada fuera de `touch_only`. La logica de parseo se DUPLICA de
  `SummarizeContractsStatus` (trade-off documentado en el REPORT): no se
  extrae un parser comun porque eso exigiria tocar `contracts.go` y re-sellar
  su contrato, fuera de alcance.

## Tests
(Los tests estan en `tui/internal/kdd/contracts_list_test.go`, oraculo
congelado sellado por `tests_sha256`: el implementador no los escribe ni los
modifica. Son 100% Go puro (`testing` stdlib), literales de bytes JSON como
input — validos (orden distinto al esperado para probar el ordenamiento
alfabetico, lista vacia -> slice vacio no nil, un solo elemento, varios con
distintos `lifecycle`, elemento con claves extra, tasks duplicados listados
todos), invalidos (los MISMOS casos que el oraculo de
`SummarizeContractsStatus`, para paridad: JSON malformado, top-level
objeto/numero/string/null/bool, elemento numero/string/null/bool, elemento sin
`task` o sin `lifecycle`, `task`/`lifecycle` numero/null/bool, segundo elemento
invalido) — sin I/O real, sin shellear nada. Cada caso valido aserta `len` y
cada `ContractStatus` EXACTO; cada caso invalido aserta `err != nil` y primer
retorno `nil`; un caso extra verifica con `recover` que el garbage no
paniquea. `test_command: "go test -C tui ./..."` corre desde la RAIZ del repo
(forzado por `test_cwd: ../..`): el flag `-C tui` cambia a `tui/` antes de
correr y encuentra `tui/go.mod` hacia abajo, funcione desde el cwd que sea
SIEMPRE Y CUANDO el cwd de partida sea la raiz del repo. Exactamente el patron
de `kdd-contracts-status-summarize.md`/`tui-gates-summarize.md` (el Nivel 1
propio `validate_test_commands` corre TODOS los `test_command` SIEMPRE con cwd
= raiz del repo, sin override, y el gate CCDD externo `run_integration_gate`
respeta `test_cwd`).

## Constraints
- PARAR y reportar si necesitas conectarte a la red o invocar un LLM.
- PARAR y reportar si el `intent` exige tocar un archivo fuera de
  `touch_only` (probablemente signifique que la spec esta mal escrita).
- PARAR y reportar si necesitas una dependencia externa de Go (modulo fuera de
  la stdlib) para esta tarea puntual — no deberia pasar:
  `ParseContractsStatus` es JSON + sort, todo stdlib.

## Budget note
`ParseContractsStatus` real mide `cyclomatic = 12` (las mismas ramas de
validacion defensiva que `SummarizeContractsStatus`: top-level, null
top-level, elemento, null elemento, presencia de dos claves, tipo de dos
claves con null-check de puntero) y `function_length = 46` sin comments (~64
con comments internos, que es lo que cuenta el gate). El budget declarado
(`cyclomatic_max: 14`, `lines_max: 70`) deja un margen chico sobre lo medido
real y esta bajo los topes globales firmados (cyclomatic 20, lines 80).
`nesting_max: 3` (medido 2) y `params_max: 1` (medido 1) son conservadores.
Identicos al budget de `kdd-contracts-status-summarize.md` (funciones
hermanas con la misma estructura de validacion).