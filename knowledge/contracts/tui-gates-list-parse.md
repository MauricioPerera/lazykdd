---
type: 'Task Contract'
title: 'TUI: Parse gates run-all JSON a struct + detalle de gate individual (lista navegable)'
description: 'Variante estructurada de Summarize (ParseGatesResults -> overallOK + []GateResult ordenado por name) y sumarizador del JSON de un gate individual (SummarizeGateDetail), para alimentar el panel de GATES navegable del TUI.'
tags: ['ccdd', 'tui', 'lazykdd', 'go', 'gates']

task: tui-gates-list-parse
intent: "Parsear el JSON de gates run-all a un slice estructurado de GateResult ordenado por name mas el bool overall_ok."
language: go
target: tui/internal/kdd/gates_list.go
signature: "func ParseGatesResults(data []byte) (bool, []GateResult, error)"
target_line: 45
test_command: "go test -C tui ./..."
test_cwd: ../..
budget:
  cyclomatic_max: 14
  nesting_max: 3
  params_max: 1
  lines_max: 70
tests: "tui/internal/kdd/gates_list_test.go"
tests_sha256: "e151dab3a5a3fadb7de19cd81d8050ee4cb5e05637b7a011fe16d206fc2a1521"
touch_only: ['tui/internal/kdd/gates_list.go']
deps_allowed: []
forbids: ['network', 'llm']
---

# Contract: TUI `ParseGatesResults` + `SummarizeGateDetail` (Piel 3, Go)

## Intent
Pieza del panel de GATES navegable del TUI de lazykdd (Piel 3, Go): dos
funciones puras en el paquete `kdd` (archivo NUEVO `gates_list.go`, mismo
paquete, NO toca `gates.go` ni su contrato sellado). `ParseGatesResults` es la
variante ESTRUCTURADA de
[Summarize](./tui-gates-summarize.md) (que arma un string plano): mismo
parseo/validacion, mismo orden defensivo, mismo `results`-vacio-es-valido, pero
devuelve el bool `overall_ok` y un slice de `GateResult` (Name + ExitCode)
ordenado alfabeticamente por Name, para que `UpdateModel`/`View` en
[tui-bubbletea-model](./tui-bubbletea-model.md) armen la lista NAVEGABLE de
gates (cursor arriba/abajo, Enter corre ESE gate via `gates run <name> --json`,
Esc vuelve). `SummarizeGateDetail` parsea el JSON de UN gate individual emitido
por [kdd-gates-run-single-json](./kdd-gates-run-single-json.md)
(`{"exit_code":int,"stdout":string,"stderr":string}` o `{"error":string}`) y arma
un string legible con exit_code + stdout + stderr (o un error si vino en forma
de error). El gate de complejidad gobierna `ParseGatesResults` (la mas compleja,
via `signature`); `SummarizeGateDetail` es un helper sin contrato propio (mismo
criterio que `renderContractList` en `model.go`). No usa Bubble Tea.

## Interface
```go
type GateResult struct {
    Name     string
    ExitCode int
}

// ParseGatesResults parsea el JSON crudo de `gates run-all --json`:
// {"overall_ok": bool, "results": {<name>: {"exit_code": int, ...}, ...}}.
// Devuelve (overallOK, items, err): overallOK es el bool del JSON, items es un
// slice de GateResult ordenado alfabeticamente por Name. Un results vacio ({})
// es valido: items vacio (no nil), overallOK tal cual, err nil.
//
// Devuelve (false, nil, err) si data no es JSON valido o no matchea la forma
// esperada (falta overall_ok o results, results no es un objeto o es null,
// overall_ok de tipo equivocado, top-level no objeto). Pura: sin I/O, sin red,
// sin os.Exit, nunca paniquea.
func ParseGatesResults(data []byte) (overallOK bool, items []GateResult, err error)

// SummarizeGateDetail parsea el JSON de UN gate individual:
// {"exit_code": int, "stdout": string, "stderr": string} o {"error": string}.
//
// Si la clave "error" esta presente: devuelve ("", errors.New(<valor>)). El
// valor se decodifica como string (null -> "").
//
// Si la clave "exit_code" esta presente (y no "error"): arma el string EXACTO
//
//     exit_code=<N>
//     --- stdout ---
//     <stdout>
//     --- stderr ---
//     <stderr>
//
// (stdout/stderr se decodifican como string, default "" si ausentes; sin
// trailing newline extra mas alla del que ya traiga stderr). JSON invalido o
// sin ninguna de las 2 formas esperadas -> ("", err). Pura, nunca paniquea.
func SummarizeGateDetail(data []byte) (string, error)
```

## Invariants
- Para input invalido de `ParseGatesResults` (no JSON, forma inesperada, results
  no objeto o null), los tres retornos son `(false, nil, err)` con err no nil;
  nunca panic. (Paridad con el oraculo de `Summarize`.)
- Para input valido de `ParseGatesResults`, `items` SIEMPRE tiene
  `len == len(results)` y los elementos siguen orden alfabetico determinista
  por `Name` (independiente del orden de aparicion en el JSON ni del orden de
  iteracion del map de Go).
- Un `results` vacio (`{}`) devuelve un slice de longitud 0 (NO nil) y error
  nil: el caller itera sin nil-check extra. `overallOK` se copia del JSON tal
  cual (true/false).
- `pass + fail == len(results)` NO se calcula aca (a diferencia de `Summarize`):
  `ParseGatesResults` solo colecciona `Name`+`ExitCode`, no cuenta pass/fail.
  Cada gate aporta exactamente un item.
- Para `SummarizeGateDetail`, la forma de error (clave "error" presente) SIEMPRE
  devuelve `("", err)` con `err.Error()` == el valor string de "error"; la forma
  exitosa (clave "exit_code" presente, sin "error") SIEMPRE devuelve el string
  con el formato documentado y err nil. JSON invalido o ninguna de las 2 formas
  -> `("", err)`. Nunca panic.
- 100% stdlib de Go (`encoding/json`, `fmt`, `sort`, `errors`); cero modulos
  externos, cero I/O, cero red. SIN Bubble Tea.

## Examples
- `ParseGatesResults([]byte(`{"overall_ok": false, "results": {"zeta": {"exit_code": 0}, "alpha": {"exit_code": 1}}}`))` -> `(false, []GateResult{{"alpha",1},{"zeta",0}}, nil)` (orden alfabetico).
- `ParseGatesResults([]byte(`{"overall_ok": true, "results": {}}`))` -> `(true, []GateResult{}, nil)` (results vacio: slice vacio no nil).
- `ParseGatesResults([]byte(`{"overall_ok": false, "results": {"g": {"stdout": "s"}}}`))` -> `(false, []GateResult{{"g",0}}, nil)` (exit_code ausente -> 0).
- `ParseGatesResults([]byte(`{"results": {}}`))` -> `(false, nil, err)` (falta overall_ok).
- `ParseGatesResults([]byte(`{"overall_ok": true, "results": [1,2]}`))` -> `(false, nil, err)` (results no es un objeto).
- `ParseGatesResults([]byte(`not json`))` -> `(false, nil, err)` (JSON invalido, sin panic).
- `SummarizeGateDetail([]byte(`{"exit_code": 1, "stdout": "hello\nworld", "stderr": "boom"}`))` -> `("exit_code=1\n--- stdout ---\nhello\nworld\n--- stderr ---\nboom", nil)`.
- `SummarizeGateDetail([]byte(`{"exit_code": 0, "stdout": "hi", "stderr": ""}`))` -> `("exit_code=0\n--- stdout ---\nhi\n--- stderr ---\n", nil)`.
- `SummarizeGateDetail([]byte(`{"error": "unknown gate: foo"}`))` -> `("", error("unknown gate: foo"))`.
- `SummarizeGateDetail([]byte(`{"stdout": "x"}`))` -> `("", err)` (ninguna de las 2 formas).
- `SummarizeGateDetail([]byte(`not json`))` -> `("", err)` (JSON invalido, sin panic).

## Do / Don't
- DO: dos pasadas de `json.Unmarshal` en `ParseGatesResults` — primero sobre
  `map[string]json.RawMessage` para detectar presencia de `overall_ok`/
  `results` y validar que `results` sea un objeto (unmarshal sobre map rechaza
  arrays/strings/numeros), luego sobre los structs tipados para extraer
  `overall_ok` (bool) y cada `exit_code` (int). Mismo patron que `Summarize`.
- DO: detectar `results: null` explicitamente (unmarshal de `null` sobre un map
  lo deja nil sin error) y devolver error en ese caso. Mismo criterio que
  `Summarize`.
- DO: ordenar los nombres de `results` con `sort.Strings` antes de armar items
  (determinismo); iterar los nombres ordenados y coleccionar
  `GateResult{Name, ExitCode}`.
- DO: devolver `make([]GateResult, 0, len(results))` para que un results vacio
  sea un slice de longitud 0 (no nil), no un slice nil.
- DO: en `SummarizeGateDetail`, parsear el top-level como
  `map[string]json.RawMessage`; si la clave `"error"` esta presente, decodificar
  su valor a string (usar `*string` para distinguir null de "") y devolver
  `("", errors.New(value))`. Si no, si `"exit_code"` esta presente, decodificar
  exit_code (int), stdout (string, default ""), stderr (string, default "") y
  armar el string con `fmt.Sprintf("exit_code=%d\n--- stdout ---\n%s\n--- stderr
  ---\n%s", ...)`. Si ninguna de las 2 claves esta -> error.
- DON'T: inventar tipos de error custom; usa `fmt.Errorf` (con `%w` donde
  envuelvas un error de `json`), el error nativo de `encoding/json`, o
  `errors.New` para el valor de `"error"`.
- DON'T: tocar `tui/internal/kdd/gates.go`, `gates_test.go`, su contrato
  `tui-gates-summarize.md`, `contracts.go`, `contracts_list.go`, sus tests/contratos,
  `scripts/`, ni nada fuera de `touch_only`. La logica de parseo de
  `ParseGatesResults` se DUPLICA de `Summarize` (trade-off documentado en el
  REPORT): no se extrae un parser comun porque eso exigiria tocar `gates.go` y
  re-sellar su contrato, fuera de alcance. Mismo criterio que
  `kdd-contracts-list-parse.md` duplico de `SummarizeContractsStatus`.
- DON'T: agregar Bubble Tea, I/O, ni mas funciones de las estrictamente
  necesarias. Solo `GateResult`, `ParseGatesResults` y `SummarizeGateDetail`.

## Tests
(Los tests estan en `tui/internal/kdd/gates_list_test.go`, oraculo congelado
sellado por `tests_sha256`: el implementador no los escribe ni los modifica. Son
100% Go puro (`testing` stdlib), literales de bytes JSON como input. Para
`ParseGatesResults`: validos (mezcla pass/fail con orden alfabetico, results
vacio -> slice vacio no nil, single, all pass, all fail, gate sin exit_code ->
0), invalidos (los MISMOS casos que el oraculo de `Summarize`, para paridad:
JSON malformado, falta overall_ok/results, results array/string/numero/null,
overall_ok tipo equivocado, top-level array/numero/null/string/bool, bytes
vacios), y garbage no ASCII sin panic. Para `SummarizeGateDetail`: exito con
stdout/stderr no vacios, exito con stderr vacio, exito con stdout vacio, exito
sin claves stdout/stderr (default ""), forma de error (valor exacto), forma de
error con valor vacio, JSON invalido, ninguna de las 2 formas, garbage sin
panic. Sin I/O real, sin shellear nada. `test_command: "go test -C tui ./..."`
corre desde la RAIZ del repo (forzado por `test_cwd: ../..`): el flag `-C tui`
cambia a `tui/` antes de correr. Exactamente el patron de
`tui-gates-summarize.md`/`kdd-contracts-list-parse.md`.)

## Constraints
- PARAR y reportar si necesitas conectarte a la red o invocar un LLM.
- PARAR y reportar si el `intent` exige tocar un archivo fuera de `touch_only`
  (probablemente signifique que la spec esta mal escrita).
- PARAR y reportar si necesitas una dependencia externa de Go (modulo fuera de
  la stdlib) para esta tarea puntual — no deberia pasar: `ParseGatesResults` y
  `SummarizeGateDetail` son JSON + sort + string, todo stdlib.

## Budget note
`ParseGatesResults` real mide ~`cyclomatic = 12` (las mismas ramas de validacion
defensiva que `Summarize`: top-level, presencia de overall_ok, presencia de
results, tipo de overall_ok, tipo de results, results null, loop + unmarshal por
gate) pero SIN las ramas de conteo pass/fail ni el string building de
`Summarize` (aca solo se colecciona Name+ExitCode), asi que ligeiramente mas
simple. `function_length` ~45 con comments internos. El budget declarado
(`cyclomatic_max: 14`, `lines_max: 70`) deja margen chico sobre lo medido real y
esta bajo los topes globales firmados (cyclomatic 20, lines 80). `nesting_max: 3`
(medido 2) y `params_max: 1` (medido 1) conservadores. Identicos al budget de
`kdd-contracts-list-parse.md` (funcion hermana con la misma estructura de
validacion). `SummarizeGateDetail` es un helper sin contrato propio: el gate NO
la mide (no es el target via `signature`), mismo criterio que `renderContractList`
en `model.go`; sus tests propios en el oraculo la cubren.