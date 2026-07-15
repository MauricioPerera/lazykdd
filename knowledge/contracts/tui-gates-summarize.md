---
type: 'Task Contract'
title: 'TUI: Summarize gates run-all JSON'
description: 'Primera pieza de la Piel 3 (TUI Go) de lazykdd: una funcion pura Summarize que parsea el JSON de gates run-all y arma un resumen determinista, mas el wiring minimo de main.go que shellea al CLI Python.'
tags: ['ccdd', 'tui', 'lazykdd', 'go']

task: tui-gates-summarize
intent: "Resumir el JSON de gates run-all en un reporte determinista de pass/fail por gate."
language: go
target: tui/internal/kdd/gates.go
signature: "func Summarize(data []byte) (string, error)"
test_command: "go test -C tui ./..."
test_cwd: ../..
budget:
  cyclomatic_max: 13
  nesting_max: 3
  params_max: 1
  lines_max: 65
tests: "tui/internal/kdd/gates_test.go"
tests_sha256: "e1129931e70e7720fb5301b3cec7d75c90f256067da7c28a624cadeec1a17ac5"
touch_only: ['tui/internal/kdd/gates.go', 'tui/main.go']
deps_allowed: []
forbids: ['network', 'llm']
---

# Contract: TUI `Summarize` (Piel 3, Go)

## Intent
Primera pieza de la Piel 3 (TUI en Go) del proyecto lazykdd: una unica
funcion pura `Summarize(data []byte) (string, error)` en el paquete `kdd`
que consume el JSON crudo que emite `python scripts/kdd_cli.py gates
run-all --json` ([kdd-gates-run-all-json](./kdd-gates-run-all-json.md)) y
arma un resumen determinista de pass/fail por gate. Deliberadamente SIN
Bubble Tea, SIN interactividad, SIN loop de eventos: primero se prueba el
pipe completo (un binario Go que shellea al CLI Python, parsea su JSON e
imprime un resumen). Ademas reemplaza el placeholder `tui/main.go` por el
wiring minimo que conecta el binario al CLI (glue, fuera de los tests
congelados, mismo patron que el `if __name__ == '__main__':` del CLI
Python).

## Interface
```go
func Summarize(data []byte) (string, error)
```
`data` es el JSON crudo de `gates run-all --json`: un objeto
`{"overall_ok": bool, "results": {<nombre_gate>: {"exit_code": int,
"stdout": string, "stderr": string}, ...}}`.

- Si `data` NO es JSON valido, o no matchea la forma esperada (falta
  `overall_ok` o `results`, o `results` no es un objeto, o `results` es
  `null`): devuelve `("", err)` con `err` no nil (se usa `fmt.Errorf` o el
  error nativo de `encoding/json`; sin tipo de error custom).
- Si `data` es valido: devuelve un string con la forma EXACTA:

      overall_ok=<true|false> pass=<N> fail=<M>
      [PASS] <nombre_gate_1>
      [FAIL] <nombre_gate_2>
      ...

  - Primera linea: `overall_ok=` + el valor literal de Go para bool en
    `%v` (`true`/`false`), un espacio, `pass=<N>` (gates con
    `exit_code == 0`), un espacio, `fail=<M>` (gates con `exit_code != 0`;
    un `exit_code` ausente se decodifica como `0` por default de Go y
    cuenta como pass, sin crashear).
  - Una linea por gate, en orden ALFABETICO por nombre (`sort.Strings`:
    un map de Go no itera en orden estable), `[PASS] <nombre>` si
    `exit_code == 0`, `[FAIL] <nombre>` si no.
  - Las lineas se unen con `\n` SIN trailing newline. Un `results` vacio
    (`{}`) es valido: solo el header `overall_ok=... pass=0 fail=0`, sin
    lineas de gate.
- La funcion es PURA: sin I/O, sin red, sin `os.Exit`, nunca paniquea (un
  JSON malformado es un `error` devuelto, NUNCA un panic).

## Invariants
- Para input invalido (no JSON, forma inesperada, `results` no objeto o
  `null`), el primer retorno es SIEMPRE `""` y el segundo no nil; nunca
  panic.
- Para input valido, el string SIEMPRE empieza con
  `overall_ok=<true|false> pass=<N> fail=<M>`; los gates siguen en orden
  alfabetico determinista (independiente del orden de aparicion en el
  JSON ni del orden de iteracion del map de Go).
- Sin trailing newline: el string no termina en `\n`; un `results` vacio
  produce exactamente el header y nada mas.
- `pass + fail == len(results)` para todo input valido (cada gate cae en
  exactamente uno de los dos conteos).
- 100% stdlib de Go (`encoding/json`, `fmt`, `sort`, `strings`); cero
  modulos externos, cero I/O, cero red.

## Examples
- `Summarize([]byte(`{"overall_ok": false, "results": {"zeta": {"exit_code": 0}, "alpha": {"exit_code": 1}}}`))` -> `"overall_ok=false pass=1 fail=1\n[FAIL] alpha\n[PASS] zeta"` (orden alfabetico: alpha antes que zeta aunque el JSON traiga zeta primero).
- `Summarize([]byte(`{"overall_ok": true, "results": {}}`))` -> `"overall_ok=true pass=0 fail=0"` (results vacio: solo header, sin newline final).
- `Summarize([]byte(`{"overall_ok": false, "results": {"g": {"stdout": "s"}}}`))` -> `"overall_ok=false pass=1 fail=0\n[PASS] g"` (exit_code ausente -> 0 -> pass).
- `Summarize([]byte(`{"results": {}}`))` -> `("", err)` (falta overall_ok).
- `Summarize([]byte(`{"overall_ok": true, "results": [1,2]}`))` -> `("", err)` (results no es un objeto).
- `Summarize([]byte(`not json`))` -> `("", err)` (JSON invalido, sin panic).

## Do / Don't
- DO: dos pasadas de `json.Unmarshal` — primero sobre
  `map[string]json.RawMessage` para detectar presencia de `overall_ok`/
  `results` y validar que `results` sea un objeto (unmarshal sobre map
  rechaza arrays/strings/numeros), luego sobre los structs tipados para
  extraer `overall_ok` (bool) y cada `exit_code` (int).
- DO: ordenar las claves de `results` con `sort.Strings` antes de armar
  las lineas (determinismo).
- DO: detectar `results: null` explicitamente (unmarshal de `null` sobre
  un map lo deja nil sin error) y devolver error en ese caso.
- DO: armar el string con `strings.Builder` y `fmt.Fprintf`, uniendo con
  `\n` prefijado en cada linea de gate (sin trailing newline).
- DON'T: inventar un tipo de error custom; usa `fmt.Errorf` (con `%w`
  donde envuelvas un error de `json`) o el error nativo de
  `encoding/json`.
- DON'T: incluir `subprocess`/`os.exec` en `forbids` — `Summarize` es
  pura y no los usa; `main.go` si usa `os/exec` (analogeo a `subprocess`
  de Python, mismo matiz que los contratos del CLI Python de este repo),
  pero `main.go` es glue fuera del target y fuera de los tests congelados.
  `forbids` es `['network','llm']`.
- DON'T: agregar Bubble Tea, flags de linea de comandos, ni mas funciones
  de las estrictamente necesarias. Solo `Summarize` + el wiring minimo de
  `main.go`.
- DON'T: tocar `scripts/`, el CLI Python, `.agents/`, ni ningun archivo
  fuera de `touch_only`.

## Tests
(Los tests estan en `tui/internal/kdd/gates_test.go`, oraculo congelado
sellado por `tests_sha256`: el implementador no los escribe ni los
modifica. Son 100% Go puro (`testing` stdlib), literales de bytes JSON
como input — validos (gates en orden distinto al esperado para probar el
ordenamiento alfabetico, `results` vacio, gate sin `exit_code`, todos
pass, todos fail, single gate), invalidos (JSON malformado, falta
`overall_ok`, falta `results`, `results` array/string/numero/null,
`overall_ok` de tipo equivocado, top-level array/numero/null/string,
bytes vacios, garbage no ASCII) — sin I/O real, sin shellear nada. Cada
caso valido aserta el string EXACTO; cada caso invalido aserta `err !=
nil` y primer retorno `""`; un caso extra verifica con `recover` que el
garbage no paniquea. `test_command: "go test ./..."` corre con `cwd` = el
directorio del target (`tui/internal/kdd/`): target y tests estan en el
mismo directorio, y Go encuentra `go.mod` hacia arriba (`tui/go.mod`), asi
que el default alcanza y NO se declara `test_cwd`.)

## Constraints
- PARAR y reportar si necesitas conectarte a la red o invocar un LLM.
- PARAR y reportar si el `intent` exige tocar un archivo fuera de
  `touch_only` (probablemente signifique que la spec esta mal escrita).
- PARAR y reportar si necesitas una dependencia externa de Go (modulo
  fuera de la stdlib) para esta tarea puntual — no deberia pasar:
  `Summarize` es JSON + string + sort, todo stdlib.