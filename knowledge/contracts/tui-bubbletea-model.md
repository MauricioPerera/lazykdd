---
type: 'Task Contract'
title: 'TUI: Bubble Tea Model (capa interactiva)'
description: 'Primera capa interactiva de la Piel 3: un programa Bubble Tea (arquitectura Elm) que shellea al CLI Python, muestra el resumen de gates y sale con q/Ctrl+C. Logica pura UpdateModel/View (target, testeable) separada del wrapper tea.Model (wiring, no testeado).'
tags: ['ccdd', 'tui', 'lazykdd', 'go']

task: tui-bubbletea-model
intent: "Gobernar la transicion de estado del TUI de gates con una funcion UpdateModel pura."
language: go
target: tui/internal/ui/model.go
signature: "func UpdateModel(m Model, msg tea.Msg) (Model, tea.Cmd)"
test_command: "go test -C tui ./..."
test_cwd: ../..
budget:
  cyclomatic_max: 9
  nesting_max: 3
  params_max: 2
  lines_max: 30
tests: "tui/internal/ui/model_test.go"
tests_sha256: "11b99caabf3bf05c7613bff1cbef36413b1eba2b3b08d49c27f93f4003064719"
touch_only: ['tui/internal/ui/model.go', 'tui/internal/ui/program.go', 'tui/internal/ui/pipe_test.go', 'tui/main.go', 'tui/go.mod', 'tui/go.sum']
deps_allowed: ['github.com/charmbracelet/bubbletea']
forbids: ['network', 'llm']
---

# Contract: TUI Bubble Tea `UpdateModel` (Piel 3, Go)

## Intent
Primera capa INTERACTIVA de la Piel 3 de lazykdd: un programa Bubble Tea
(`github.com/charmbracelet/bubbletea`, arquitectura Elm) en el paquete nuevo
`tui/internal/ui` que al arrancar shellea al CLI Python reusando la logica
existente ([tui-gates-summarize](./tui-gates-summarize.md)), muestra el resumen
de gates y sale con 'q' o Ctrl+C. La funcion que gobierna este contrato es
`UpdateModel(m Model, msg tea.Msg) (Model, tea.Cmd)`: PURA (sin I/O, sin red,
sin goroutines, sin llamar a Bubble Tea real mas alla de sus TIPOS), separada
del wiring de I/O real (el wrapper `tea.Model` en `program.go`, glue, no
testeado, mismo criterio que `main.go`). `View(m Model) string` tambien es pura
y esta cubierta por el mismo oraculo congelado, pero NO es el target principal
del gate de complejidad (ver seccion Do/Don't: decision de un solo contrato).

## Interface
```go
type Model struct {
    Summary  string  // el string de kdd.Summarize, vacio si no cargo aun
    Err      error   // error de kdd.Summarize o del shell-out, nil si ok
    Loading  bool    // true hasta que llega el primer resultado
    Quitting bool    // true una vez que el usuario pidio salir
}

type gatesLoadedMsg struct {
    summary string
    err     error
}

func UpdateModel(m Model, msg tea.Msg) (Model, tea.Cmd)
func View(m Model) string
```
`UpdateModel` recibe el estado actual `m` y un mensaje `msg` (cualquier
`tea.Msg`), y devuelve la nueva `Model` y un `tea.Cmd` (nil = nada mas que
hacer). Comportamiento:
- `msg` es `gatesLoadedMsg`: devuelve un `Model` con `Summary`/`Err` seteados
  desde el mensaje, `Loading: false` (el resto de los campos de `m` sin
  cambios), `tea.Cmd` nil.
- `msg` es `tea.KeyMsg` y `msg.String()` es `"q"` o `"ctrl+c"`: devuelve `m`
  con `Quitting: true` y como `tea.Cmd` devuelve `tea.Quit` (funcion del
  paquete `bubbletea`, no se inventa).
- Cualquier otro `msg` (otras teclas, `tea.WindowSizeMsg`, lo que sea):
  devuelve `m` SIN CAMBIOS, `tea.Cmd` nil.
- Nunca panic con ningun `tea.Msg`, tipado o no (type switch con default, sin
  type assertion sin `, ok`).

`View` renderiza la `Model` a un string. Precedencia: `Quitting` > `Err` >
`Loading` > `Summary`:
- `m.Quitting` true: `""` (Bubble Tea limpia la pantalla al salir).
- `m.Err != nil`: `"error: " + m.Err.Error() + "\n"`.
- `m.Loading` true (sin error): `"cargando gates...\n"`.
- si no: `m.Summary + "\n"` (`kdd.Summarize` NO trae trailing newline por
  diseno, asi que `View` es quien lo agrega).

## Invariants
- `UpdateModel` es PURA: sin I/O, sin red, sin goroutines, sin `os/exec`, sin
  `os.Exit`, nunca paniquea (type switch con default; un msg no reconocido
  deja el model igual).
- Para `gatesLoadedMsg`, `Loading` queda SIEMPRE false y `Summary`/`Err` son
  EXACTAMENTE los del msg; `Quitting` se preserva del model entrante.
- Para "q"/"ctrl+c", el `tea.Cmd` devuelto ES `tea.Quit` (cmd() produce un
  `tea.QuitMsg`); para cualquier otra tecla o msg, el cmd es nil.
- `View` nunca devuelve un string con doble `\n` final; el unico newline es
  el que agrega al final del resumen/mensaje.
- 100% del comportamiento gobernable es reproducible desde el oraculo congelado
  (`model_test.go`) construyendo `Model`/`tea.Msg` a mano, sin shellear nada.

## Examples
- `UpdateModel(Model{Loading:true}, gatesLoadedMsg{summary:"overall_ok=true pass=1 fail=0", err:nil})` -> `Model{Summary:"overall_ok=true pass=1 fail=0", Loading:false}` con cmd nil.
- `UpdateModel(Model{Loading:true}, gatesLoadedMsg{summary:"", err:errors.New("boom")})` -> `Model{Err:<boom>, Loading:false}` con cmd nil.
- `UpdateModel(Model{}, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("q")})` -> `Model{Quitting:true}` con cmd = `tea.Quit`.
- `UpdateModel(Model{}, tea.KeyMsg{Type: tea.KeyCtrlC})` -> `Model{Quitting:true}` con cmd = `tea.Quit`.
- `UpdateModel(Model{Loading:true}, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("x")})` -> model sin cambios, cmd nil (NO quita).
- `UpdateModel(Model{Loading:true}, tea.WindowSizeMsg{Width:80, Height:24})` -> model sin cambios, cmd nil.
- `View(Model{Quitting:true, Err:errors.New("e"), Loading:true})` -> `""`.
- `View(Model{Err:errors.New("boom"), Loading:true})` -> `"error: boom\n"`.
- `View(Model{Loading:true})` -> `"cargando gates...\n"`.
- `View(Model{Summary:"overall_ok=true pass=0 fail=0"})` -> `"overall_ok=true pass=0 fail=0\n"`.

## Do / Don't
- DO: type switch sobre `msg` (`switch msg := msg.(type)`) con `case gatesLoadedMsg`,
  `case tea.KeyMsg` (con un nested switch sobre `msg.String()`), y `default`.
  Nada de type assertion sin `, ok`.
- DO: devolver `tea.Quit` (la funcion del paquete) para "q"/"ctrl+c", no
  inventar un cmd propio.
- DO: separar la logica pura (`model.go`: `Model`, `gatesLoadedMsg`,
  `UpdateModel`, `View`) del wiring (`program.go`: el wrapper `tea.Model` que
  shellea en `Init()`). Mismo criterio que `gates.go` (pura) vs `main.go`
  (glue) en la tarea anterior.
- DO: el wrapper `Init()` shellea `python scripts/kdd_cli.py gates run-all
  --json` con el mismo patron de `os/exec` que `main.go` (path relativo,
  asume cwd = repo root) y envuelve el stdout en `kdd.Summarize`; un
  `*exec.ExitError` (gates fallando -> overall_ok=false) NO es error de
  shell-out (se conserva stdout y se resume igual).
- DO: `main.go` lanza `tea.NewProgram(ui.NewProgram()).Run()`; si `Run()`
  devuelve error, stderr + exit 1; si no, exit 0. El exit-code-refleja-
  overall_ok del modo viejo SE PIERDE (trade-off aceptado: un TUI interactivo
  no tiene un "resultado" que devolver por exit code igual que un comando
  no-interactivo).
- DO: un solo contrato para `UpdateModel` (target del gate) y `View` (pura,
  cubierta por el mismo oraculo pero NO target principal). Decision: ambas
  viven en el mismo archivo `model.go` y el mismo oraculo `model_test.go`
  porque son co-dependientes (el Elm las usa junta) y ambas son triviales de
  complejidad; un segundo contrato solo para `View` aniadiria overhead
  administrativo sin aislar riesgo real (documentado en el REPORT).
- DON'T: incluir `subprocess`/`os.exec` en `forbids` — `UpdateModel`/`View`
  son puras y no los usan; el wrapper `Init()` y `main.go` si shellean
  (analogeo a `subprocess` de Python, mismo matiz que `tui-gates-summarize.md`
  y el CLI Python), pero son glue fuera del target y fuera del oraculo
  congelado. `forbids` es `['network','llm']`: `network` sigue prohibido para
  el TARGET mismo (UpdateModel no hace red ni I/O), aunque el modulo `Init()`
  del wrapper si shellea (subprocess local, no red), igual que `main.go`.
- DON'T: agregar navegacion, scroll, paneles multiples, refresco periodico, ni
  colores/estilos con `lipgloss` (viene como dependencia transitiva de
  bubbletea, no se usa directo). Un solo "screen" que carga y muestra.
- DON'T: correr `tea.NewProgram(...).Run()` dentro de los tests (es
  bloqueante y ocupa la terminal). El oraculo congelado solo ejercita
  `UpdateModel`/`View` como funciones puras; el pipe end-to-end (que SI
  shellea a python) vive en `pipe_test.go` como test ADICIONAL opt-in
  (salteado por defecto via `LAZYKDD_RUN_PIPE=1`), fuera del oraculo sellado.
- DON'T: tocar `tui/internal/kdd/gates.go`, su contrato
  `tui-gates-summarize.md`, `scripts/`, ni `.agents/`.

## Tests
(Los tests estan en `tui/internal/ui/model_test.go`, oraculo congelado sellado
por `tests_sha256`: el implementador no los escribe ni los modifica. Son 100%
Go puro (`testing` stdlib + tipos de `bubbletea`), construyendo `Model` y
`tea.Msg` a mano — sin I/O real, sin shellear nada, sin `tea.NewProgram`.
Casos de `UpdateModel`: `gatesLoadedMsg` con summary+err nil, `gatesLoadedMsg`
con err no nil, `tea.KeyMsg` "q" (quita + cmd es tea.Quit), "ctrl+c" (idem),
otra tecla "x" (NO quita, cmd nil), `tea.WindowSizeMsg` (no cambia, cmd nil),
y un msg propio no reconocido (no cambia, cmd nil, sin panic). Casos de
`View`: quitting (-> ""), error (-> "error: ...\n"), loading (-> "cargando
gates...\n") y resumen normal (-> summary + "\n", sin doble newline final).
`test_command: "go test -C tui ./..."` corre desde la RAIZ del repo (forzado
por `test_cwd: ../..`): el flag `-C tui` cambia a `tui/` antes de correr y
encuentra `tui/go.mod` hacia abajo, funcione desde el cwd que sea SIEMPRE Y
CUANDO el cwd de partida sea la raiz del repo. Asi el mismo `test_command`
pasa para el gate CCDD externo (`run_integration_gate`, que por default usaria
el directorio del target como cwd salvo `test_cwd`) Y para el Nivel 1 propio
del repo (`scripts/validate_test_commands.py`, que corre TODOS los
`test_command` SIEMPRE con cwd = raiz del repo, sin override). Exactamente el
patron de `tui-gates-summarize.md`.)

El test ADICIONAL `tui/internal/ui/pipe_test.go` (NO sellado, NO en `tests:`)
ejercita el `tea.Cmd` real de `Init()` llamandolo como funcion — eso SI shellea
a python de verdad (unica forma de probar el pipe end-to-end sin lanzar la
TUI). Es OPT-IN: se saltea por defecto (`LAZYKDD_RUN_PIPE` vacio) para que el
`go test ./...` default sea 100% puro (HECHO 2) y para ROMPER la recursion con
`validate_test_commands` (el `go test -C tui ./...` de este contrato, corrido
por `gates run-all`, dispararia este test que shellea `gates run-all` otra
vez). Para correrlo de verdad: `LAZYKDD_RUN_PIPE=1 go test -C tui -run
TestInitPipelineShellsOutToPython -v ./internal/ui/`. El test consume
(`os.Unsetenv`) el flag antes de shellerar, asi el `go test` anidado que
dispara `validate_test_commands` (dentro del `gates run-all`) lo ve vacio y
saltea — recursion rota en profundidad 1.

## Constraints
- PARAR y reportar si necesitas conectarte a la red o invocar un LLM.
- PARAR y reportar si el `intent` exige tocar un archivo fuera de
  `touch_only` (probablemente signifique que la spec esta mal escrita).
- PARAR y reportar si `go get github.com/charmbracelet/bubbletea` falla por
  falta de red (no deberia pasar; la red esta disponible).