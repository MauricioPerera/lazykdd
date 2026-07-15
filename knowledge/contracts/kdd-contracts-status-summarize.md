---
type: 'Task Contract'
title: 'TUI: Summarize contracts status JSON'
description: 'Segundo panel del TUI (Piel 3, Go): una funcion pura SummarizeContractsStatus que parsea el JSON de contracts status --json y arma un listado determinista de contratos por etapa, para browsear knowledge/contratos desde el TUI.'
tags: ['ccdd', 'tui', 'lazykdd', 'go', 'contracts']

task: kdd-contracts-status-summarize
intent: "Resumir el JSON de contracts status --json en un listado determinista de contratos por etapa."
language: go
target: tui/internal/kdd/contracts.go
signature: "func SummarizeContractsStatus(data []byte) (string, error)"
test_command: "go test -C tui ./..."
test_cwd: ../..
budget:
  cyclomatic_max: 14
  nesting_max: 3
  params_max: 1
  lines_max: 70
tests: "tui/internal/kdd/contracts_test.go"
tests_sha256: "df9b4a0508930b82179b1ada4de1021ffc5f8bdad3be54ea33c352880fc9763d"
touch_only: ['tui/internal/kdd/contracts.go']
deps_allowed: []
forbids: ['network', 'llm']
---

# Contract: TUI `SummarizeContractsStatus` (Piel 3, Go)

## Intent
Pieza del segundo panel del TUI de lazykdd (Piel 3, Go): una unica funcion
pura `SummarizeContractsStatus(data []byte) (string, error)` en el paquete
`kdd` (mismo paquete que `Summarize` en `gates.go`, NO lo modifica) que consume
el JSON crudo que emite `python scripts/kdd_cli.py contracts status --json`
([kdd-contracts-status-json](./kdd-contracts-status-json.md)) y arma un listado
determinista de contratos por etapa de ciclo de vida. Deliberadamente SIN
Bubble Tea, SIN interactividad: primero se prueba el parseo puro (la vista de
contratos del TUI la arma `UpdateModel`/`View` en
[tui-bubbletea-model](./tui-bubbletea-model.md)). Es la primera vez que la
capacidad "browsing de knowledge/contratos" de `DEFINITION.md` llega al TUI
(ya existe en el CLI Python).

## Interface
```go
func SummarizeContractsStatus(data []byte) (string, error)
```
`data` es el JSON crudo de `contracts status --json`: una lista de objetos
`{"task": string, "lifecycle": string}` (una entrada por contrato real del
repo; `lifecycle` es uno de `draft`/`validated`/`implemented`/`verified`).

- Si `data` NO es JSON valido, o el top-level NO es una lista, o algun
  elemento de la lista NO es un objeto con AL MENOS las claves `task` y
  `lifecycle` como string: devuelve `("", err)` con `err` no nil (se usa
  `fmt.Errorf` o el error nativo de `encoding/json`; sin tipo de error custom).
- Si `data` es valido (incluida una lista VACIA, que es exito): devuelve un
  string con la forma EXACTA:

      contracts=<N>
      <task_1>: <lifecycle_1>
      <task_2>: <lifecycle_2>
      ...

  - Primera linea: `contracts=` + la cantidad de elementos de la lista.
  - Una linea por contrato, formato `<task>: <lifecycle>` EXACTO (dos puntos,
    un espacio).
  - Las lineas de contrato siguen en orden ALFABETICO por `task` (no confiar en
    que el JSON ya venga ordenado — se ordena uno mismo con `sort.Slice` sobre
    una slice de structs, mismo criterio defensivo que `Summarize`).
  - Las lineas se unen con `\n` SIN trailing newline. Una lista vacia (`[]`) es
    valida: solo el header `contracts=0`, sin lineas despues.
- La funcion es PURA: sin I/O, sin red, sin `os.Exit`, nunca paniquea (un JSON
  malformado es un `error` devuelto, NUNCA un panic).

## Invariants
- Para input invalido (no JSON, top-level no lista o `null`, elemento no objeto
  o `null`, elemento sin `task` o sin `lifecycle`, o `task`/`lifecycle` de tipo
  no-string incluido `null`), el primer retorno es SIEMPRE `""` y el segundo
  no nil; nunca panic.
- Para input valido, el string SIEMPRE empieza con `contracts=<N>` donde
  `<N>` == `len(lista)`; los contratos siguen en orden alfabetico determinista
  por `task` (independiente del orden de aparicion en el JSON).
- Sin trailing newline: el string no termina en `\n`; una lista vacia produce
  exactamente `contracts=0` y nada mas.
- Un elemento con claves EXTRA (mas alla de `task`/`lifecycle`) es valido: se
  acepta con tal de tener AL MENOS `task` y `lifecycle` como string.
- 100% stdlib de Go (`encoding/json`, `fmt`, `sort`, `strings`); cero modulos
  externos, cero I/O, cero red. SIN Bubble Tea (este paquete `kdd` no lo
  necesita).

## Examples
- `SummarizeContractsStatus([]byte(`[{"task":"zeta","lifecycle":"draft"},{"task":"alpha","lifecycle":"verified"}]`))` -> `"contracts=2\nalpha: verified\nzeta: draft"` (orden alfabetico: alpha antes que zeta aunque el JSON traiga zeta primero).
- `SummarizeContractsStatus([]byte(`[]`))` -> `"contracts=0"` (lista vacia: solo header, sin newline final).
- `SummarizeContractsStatus([]byte(`[{"task":"a","lifecycle":"draft","extra":42}]`))` -> `"contracts=1\na: draft"` (claves extra se aceptan).
- `SummarizeContractsStatus([]byte(`{"task":"a","lifecycle":"draft"}`))` -> `("", err)` (top-level objeto, no lista).
- `SummarizeContractsStatus([]byte(`null`))` -> `("", err)` (top-level null).
- `SummarizeContractsStatus([]byte(`[1,2,3]`))` -> `("", err)` (elemento no objeto).
- `SummarizeContractsStatus([]byte(`[{"lifecycle":"draft"}]`))` -> `("", err)` (falta task).
- `SummarizeContractsStatus([]byte(`[{"task":1,"lifecycle":"draft"}]`))` -> `("", err)` (task no string).
- `SummarizeContractsStatus([]byte(`[{"task":null,"lifecycle":"draft"}]`))` -> `("", err)` (task null no es string).
- `SummarizeContractsStatus([]byte(`not json`))` -> `("", err)` (JSON invalido, sin panic).

## Do / Don't
- DO: dos pasadas de `json.Unmarshal` — primero sobre `[]json.RawMessage`
  para validar que el top-level sea una lista (unmarshal sobre slice rechaza
  objeto/numero/string/bool), luego por cada elemento sobre
  `map[string]json.RawMessage` para detectar presencia de `task`/`lifecycle`
  y validar que cada una sea string.
- DO: detectar `null` explicitamente en tres niveles (top-level via
  `raws == nil`, elemento via `obj == nil`, campo via puntero `*string` que
  queda nil al deserializar `null`): null nunca es lista / objeto / string
  valido. Mismo criterio defensivo que `Summarize` usa para `results: null`.
- DO: deserializar `task`/`lifecycle` con `*string` (no `string`): distingue
  `null` (nil, error) de un string vacio legitimo `""` (valido), y rechaza
  numero/bool/objeto/array via error nativo de `json`.
- DO: ordenar las entradas con `sort.Slice` por `task` antes de armar las lineas
  (determinismo).
- DO: armar el string con `strings.Builder` y `fmt.Fprintf`, uniendo con `\n`
  prefijado en cada linea de contrato (sin trailing newline).
- DON'T: inventar un tipo de error custom; usa `fmt.Errorf` (con `%w` donde
  envuelvas un error de `json`) o el error nativo de `encoding/json`.
- DON'T: agregar Bubble Tea, I/O, ni mas funciones de las estrictamente
  necesarias. Solo `SummarizeContractsStatus`.
- DON'T: tocar `tui/internal/kdd/gates.go`, `gates_test.go`, el contrato
  `tui-gates-summarize.md`, `scripts/`, ni nada fuera de `touch_only`.

## Tests
(Los tests estan en `tui/internal/kdd/contracts_test.go`, oraculo congelado
sellado por `tests_sha256`: el implementador no los escribe ni los modifica.
Son 100% Go puro (`testing` stdlib), literales de bytes JSON como input —
validos (contratos en orden distinto al esperado para probar el ordenamiento
alfabetico, lista vacia, un solo elemento, varios con distintos `lifecycle`,
elemento con claves extra, tasks duplicados), invalidos (JSON malformado,
top-level objeto/numero/string/null/bool, elemento numero/string/null/bool,
elemento sin `task` o sin `lifecycle`, `task`/`lifecycle` numero/null/bool,
segundo elemento invalido) — sin I/O real, sin shellear nada. Cada caso valido
aserta el string EXACTO; cada caso invalido aserta `err != nil` y primer retorno
`""`; un caso extra verifica con `recover` que el garbage no paniquea.
`test_command: "go test -C tui ./..."` corre desde la RAIZ del repo (forzado
por `test_cwd: ../..`): el flag `-C tui` cambia a `tui/` antes de correr y
encuentra `tui/go.mod` hacia abajo, funcione desde el cwd que sea SIEMPRE Y
CUANDO el cwd de partida sea la raiz del repo. Exactamente el patron de
`tui-gates-summarize.md`/`tui-bubbletea-model.md` (el Nivel 1 propio
`validate_test_commands` corre TODOS los `test_command` SIEMPRE con cwd = raiz
del repo, sin override, y el gate CCDD externo `run_integration_gate` respeta
`test_cwd`).

## Constraints
- PARAR y reportar si necesitas conectarte a la red o invocar un LLM.
- PARAR y reportar si el `intent` exige tocar un archivo fuera de
  `touch_only` (probablemente signifique que la spec esta mal escrita).
- PARAR y reportar si necesitas una dependencia externa de Go (modulo fuera de
  la stdlib) para esta tarea puntual — no deberia pasar:
  `SummarizeContractsStatus` es JSON + string + sort, todo stdlib.

## Budget note
`SummarizeContractsStatus` real mide `cyclomatic = 13` (muchas ramas de
validacion: top-level, elemento, presencia de dos claves, tipo de dos claves)
y `function_length = 58`. El budget declarado (`cyclomatic_max: 14`,
`lines_max: 70`) deja un margen chico sobre lo medido real y esta bajo los
topes globales firmados (cyclomatic 20, lines 80). `nesting_max: 3` (medido 2)
y `params_max: 1` (medido 1) son conservadores.