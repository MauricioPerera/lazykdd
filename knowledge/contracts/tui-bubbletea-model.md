---
type: 'Task Contract'
title: 'TUI: Bubble Tea Model (capa interactiva, dos vistas)'
description: 'Capa interactiva de la Piel 3: un programa Bubble Tea (arquitectura Elm) que shellea al CLI Python, muestra el resumen de gates O de contratos (alterna con g/c) y sale con q/Ctrl+C. Logica pura UpdateModel/View (target, testeable) separada del wrapper tea.Model (wiring, no testeado).'
tags: ['ccdd', 'tui', 'lazykdd', 'go']

task: tui-bubbletea-model
intent: "Gobernar la transicion de estado del TUI (gates + contracts) con una funcion UpdateModel pura."
language: go
target: tui/internal/ui/model.go
signature: "func UpdateModel(m Model, msg tea.Msg) (Model, tea.Cmd)"
test_command: "go test -C tui ./..."
test_cwd: ../..
budget:
  cyclomatic_max: 9
  nesting_max: 3
  params_max: 2
  lines_max: 45
tests: "tui/internal/ui/model_test.go"
tests_sha256: "424fa5d1fe967e4d332b2bc125cbf8bb55c345a5bb3d01163a1961982eaecc45"
touch_only: ['tui/internal/ui/model.go', 'tui/internal/ui/program.go', 'tui/internal/ui/pipe_test.go', 'tui/main.go', 'tui/go.mod', 'tui/go.sum']
deps_allowed: ['github.com/charmbracelet/bubbletea']
forbids: ['network', 'llm']
---

# Contract: TUI Bubble Tea `UpdateModel` (Piel 3, Go)

## Intent
Capa INTERACTIVA de la Piel 3 de lazykdd: un programa Bubble Tea
(`github.com/charmbracelet/bubbletea`, arquitectura Elm) en el paquete
`tui/internal/ui` que al arrancar shellea al CLI Python reusando la logica
existente ([tui-gates-summarize](./tui-gates-summarize.md) Y la nueva
[kdd-contracts-status-summarize](./kdd-contracts-status-summarize.md)), muestra
el resumen de gates O de contratos (el usuario alterna con `g`/`c`) y sale con
'q' o Ctrl+C. La funcion que gobierna este contrato es `UpdateModel(m Model,
msg tea.Msg) (Model, tea.Cmd)`: PURA (sin I/O, sin red, sin goroutines, sin
llamar a Bubble Tea real mas alla de sus TIPOS), separada del wiring de I/O
real (el wrapper `tea.Model` en `program.go`, glue, no testeado, mismo criterio
que `main.go`). `View(m Model) string` tambien es pura y esta cubierta por el
mismo oraculo congelado, pero NO es el target principal del gate de
complejidad (ver seccion Do/Don't: decision de un solo contrato). Esta
actualizacion EXTIENDE el comportamiento previo (un solo screen de gates) con
un segundo panel de contratos; la `signature` de `UpdateModel` NO cambio
(sigue siendo `(m Model, msg tea.Msg) (Model, tea.Cmd)`).

## Interface
```go
type Model struct {
    // --- gates ---
    Summary  string  // el string de kdd.Summarize, vacio si no cargo aun
    Err      error   // error de kdd.Summarize o del shell-out de gates, nil si ok
    Loading  bool    // true hasta que llega el primer resultado de gates
    // --- contracts ---
    Contracts        string  // el string de kdd.SummarizeContractsStatus, vacio si no cargo
    ContractsErr     error   // error de contracts status o del shell-out, nil si ok
    ContractsLoading bool    // true hasta que llega contractsLoadedMsg
    // --- comunes ---
    ViewMode  string  // "gates" (default) o "contracts"; zero-value "" == "gates"
    Quitting  bool    // true una vez que el usuario pidio salir
}

type gatesLoadedMsg struct {
    summary string
    err     error
}

type contractsLoadedMsg struct {
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
  cambios), `tea.Cmd` nil. (Comportamiento historico, sin cambios.)
- `msg` es `contractsLoadedMsg`: devuelve un `Model` con `Contracts`/
  `ContractsErr` seteados desde el mensaje, `ContractsLoading: false` (el
  resto de los campos de `m` sin cambios, incluidos los de gates y
  `ViewMode`/`Quitting`), `tea.Cmd` nil.
- `msg` es `tea.KeyMsg` y `msg.String()` es `"q"` o `"ctrl+c"`: devuelve `m`
  con `Quitting: true` y como `tea.Cmd` devuelve `tea.Quit` (funcion del
  paquete `bubbletea`, no se inventa). (Comportamiento historico, sin cambios.)
- `msg` es `tea.KeyMsg` y `msg.String()` es `"g"`: devuelve `m` con
  `ViewMode: "gates"`, resto sin cambios, `tea.Cmd` nil.
- `msg` es `tea.KeyMsg` y `msg.String()` es `"c"`: devuelve `m` con
  `ViewMode: "contracts"`, resto sin cambios, `tea.Cmd` nil.
- Cualquier otro `msg` (otras teclas, `tea.WindowSizeMsg`, lo que sea):
  devuelve `m` SIN CAMBIOS, `tea.Cmd` nil.
- Nunca panic con ningun `tea.Msg`, tipado o no (type switch con default, sin
  type assertion sin `, ok`).

`View` renderiza la `Model` a un string. Precedencia: `Quitting` > (segun
`ViewMode`) `Err/ContractsErr` > `Loading/ContractsLoading` > resumen, y la
linea de ayuda al final:
- `m.Quitting` true: `""` (Bubble Tea limpia la pantalla al salir). Tiene
  precedencia sobre todo, incluida la linea de ayuda (no se agrega al salir).
- Si no esta quitting, el cuerpo depende de `ViewMode`:
  - `ViewMode == "contracts"`: usa los campos de contracts. `ContractsErr !=
    nil` -> `"error: " + ContractsErr.Error() + "\n"`; si no, `ContractsLoading`
    -> `"cargando contratos...\n"` (texto ELEGIDO para diferenciarlo del de
    gates, documentado); si no, `Contracts + "\n"`.
  - cualquier otro valor de `ViewMode` (incluido el zero-value `""`, que se
    trata IGUAL que `"gates"`): usa los campos de gates. `Err != nil` ->
    `"error: " + Err.Error() + "\n"`; si no, `Loading` -> `"cargando
    gates...\n"`; si no, `Summary + "\n"` (`kdd.Summarize` NO trae trailing
    newline por diseno, asi que `View` es quien lo agrega).
- Al cuerpo se le agrega SIEMPRE al final la linea de ayuda EXACTA:
  `"\n[g]ates [c]ontracts [q]uit"` (un `\n` + el literal). El resultado es
  `<cuerpo>` + `"\n[g]ates [c]ontracts [q]uit"`.

## Invariants
- `UpdateModel` es PURA: sin I/O, sin red, sin goroutines, sin `os/exec`, sin
  `os.Exit`, nunca paniquea (type switch con default; un msg no reconocido
  deja el model igual).
- Para `gatesLoadedMsg`, `Loading` queda SIEMPRE false y `Summary`/`Err` son
  EXACTAMENTE los del msg; `Quitting`/`ViewMode`/los campos de contracts se
  preservan del model entrante.
- Para `contractsLoadedMsg`, `ContractsLoading` queda SIEMPRE false y
  `Contracts`/`ContractsErr` son EXACTAMENTE los del msg; los campos de gates
  y `ViewMode`/`Quitting` se preservan.
- Para "q"/"ctrl+c", el `tea.Cmd` devuelto ES `tea.Quit` (cmd() produce un
  `tea.QuitMsg`); para "g"/"c" y cualquier otra tecla o msg, el cmd es nil.
- `View` nunca devuelve un string con doble `\n` FINAL (el unico newline al
  final es el del cuerpo; la linea de ayuda no termina en `\n`); cuando esta
  quitting devuelve `""` (sin linea de ayuda).
- El zero-value de `ViewMode` (`""`) se comporta en `View` IGUAL que `"gates"`
  (el primer render muestra gates, default historico; no hace falta setearlo
  explicito al construir la Model inicial en `program.go`).
- 100% del comportamiento gobernable es reproducible desde el oraculo
  congelado (`model_test.go`) construyendo `Model`/`tea.Msg` a mano, sin
  shellear nada.

## Examples
- `UpdateModel(Model{Loading:true}, gatesLoadedMsg{summary:"overall_ok=true pass=1 fail=0", err:nil})` -> `Model{Summary:"overall_ok=true pass=1 fail=0", Loading:false}` con cmd nil.
- `UpdateModel(Model{Loading:true}, gatesLoadedMsg{summary:"", err:errors.New("boom")})` -> `Model{Err:<boom>, Loading:false}` con cmd nil.
- `UpdateModel(Model{ContractsLoading:true,ViewMode:"gates"}, contractsLoadedMsg{summary:"contracts=1\na: draft", err:nil})` -> `Model{Contracts:"contracts=1\na: draft", ContractsLoading:false, ViewMode:"gates"}` con cmd nil (gates y ViewMode preservados).
- `UpdateModel(Model{ContractsLoading:true}, contractsLoadedMsg{summary:"", err:errors.New("boom")})` -> `Model{ContractsErr:<boom>, ContractsLoading:false}` con cmd nil.
- `UpdateModel(Model{}, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("q")})` -> `Model{Quitting:true}` con cmd = `tea.Quit`.
- `UpdateModel(Model{}, tea.KeyMsg{Type: tea.KeyCtrlC})` -> `Model{Quitting:true}` con cmd = `tea.Quit`.
- `UpdateModel(Model{ViewMode:"contracts"}, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("g")})` -> `Model{ViewMode:"gates"}` con cmd nil.
- `UpdateModel(Model{ViewMode:"gates"}, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("c")})` -> `Model{ViewMode:"contracts"}` con cmd nil.
- `UpdateModel(Model{Loading:true,ViewMode:"contracts"}, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("x")})` -> model sin cambios (ViewMode queda "contracts"), cmd nil.
- `UpdateModel(Model{Loading:true}, tea.WindowSizeMsg{Width:80, Height:24})` -> model sin cambios, cmd nil.
- `View(Model{Quitting:true, Err:errors.New("e"), Loading:true})` -> `""`.
- `View(Model{Quitting:true, ViewMode:"contracts", ContractsErr:errors.New("e")})` -> `""` (quitting gana sobre contracts).
- `View(Model{Err:errors.New("boom"), Loading:true})` -> `"error: boom\n\n[g]ates [c]ontracts [q]uit"`.
- `View(Model{Loading:true})` -> `"cargando gates...\n\n[g]ates [c]ontracts [q]uit"`.
- `View(Model{Summary:"overall_ok=true pass=0 fail=0"})` -> `"overall_ok=true pass=0 fail=0\n\n[g]ates [c]ontracts [q]uit"`.
- `View(Model{ViewMode:"", Loading:true, ContractsLoading:true})` -> `"cargando gates...\n\n[g]ates [c]ontracts [q]uit"` (zero-value ViewMode == gates).
- `View(Model{ViewMode:"contracts", ContractsErr:errors.New("boom"), ContractsLoading:true})` -> `"error: boom\n\n[g]ates [c]ontracts [q]uit"`.
- `View(Model{ViewMode:"contracts", ContractsLoading:true})` -> `"cargando contratos...\n\n[g]ates [c]ontracts [q]uit"`.
- `View(Model{ViewMode:"contracts", Contracts:"contracts=2\na: draft\nb: verified"})` -> `"contracts=2\na: draft\nb: verified\n\n[g]ates [c]ontracts [q]uit"`.

## Do / Don't
- DO: type switch sobre `msg` (`switch msg := msg.(type)`) con `case gatesLoadedMsg`,
  `case contractsLoadedMsg`, `case tea.KeyMsg` (con un nested switch sobre
  `msg.String()` con cases `"q","ctrl+c"` / `"g"` / `"c"` / `default`), y
  `default` externo. Nada de type assertion sin `, ok`.
- DO: devolver `tea.Quit` (la funcion del paquete) para "q"/"ctrl+c", no
  inventar un cmd propio. Para "g"/"c" devolver cmd nil (solo cambian ViewMode).
- DO: separar la logica pura (`model.go`: `Model`, `gatesLoadedMsg`,
  `contractsLoadedMsg`, `UpdateModel`, `View`, `helpLine`) del wiring
  (`program.go`: el wrapper `tea.Model` que shellea en `Init()`). Mismo
  criterio que `gates.go` (pura) vs `main.go` (glue).
- DO: el wrapper `Init()` shellea AMBAS cargas en paralelo con `tea.Batch`:
  `python scripts/kdd_cli.py gates run-all --json` (envuelto en
  `kdd.Summarize` -> `gatesLoadedMsg`) Y `python scripts/kdd_cli.py contracts
  status --json` (envuelto en `kdd.SummarizeContractsStatus` ->
  `contractsLoadedMsg`). Mismo patron de `os/exec` que `main.go` (path
  relativo, asume cwd = repo root). Un `*exec.ExitError` (gates fallando ->
  overall_ok=false, o contracts status saliendo 1 si el dir no existe) NO es
  error de shell-out (se conserva stdout y se resume igual); solo falla si no
  arranca el proceso. La `Model` inicial en `NewProgram()` arranca con
  `Loading: true` Y `ContractsLoading: true` (ViewMode queda en zero-value "",
  que View trata como "gates").
- DO: `main.go` lanza `tea.NewProgram(ui.NewProgram()).Run()`; si `Run()`
  devuelve error, stderr + exit 1; si no, exit 0. (Sin cambios respecto del
  contrato previo: un TUI interactivo no tiene un "resultado" que devolver por
  exit code igual que un comando no-interactivo.)
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
  congelado. `forbids` es `['network','llm']`.
- DON'T: agregar scroll, refresco periodico, colores/estilos con `lipgloss`
  (viene como dependencia transitiva de bubbletea, no se usa directo), ni mas
  paneles alla de gates + contracts. Dos "screens" que se alternan con g/c, un
  solo "screen" visible a la vez.
- DON'T: correr `tea.NewProgram(...).Run()` dentro de los tests (es
  bloqueante y ocupa la terminal). El oraculo congelado solo ejercita
  `UpdateModel`/`View` como funciones puras; el pipe end-to-end (que SI
  shellea a python) vive en `pipe_test.go` como test ADICIONAL opt-in
  (salteado por defecto via `LAZYKDD_RUN_PIPE=1`), fuera del oraculo sellado.
- DON'T: tocar `tui/internal/kdd/gates.go`, su contrato `tui-gates-summarize.md`,
  `scripts/`, ni `.agents/`.

## Tests
(Los tests estan en `tui/internal/ui/model_test.go`, oraculo congelado sellado
por `tests_sha256`: el implementador no los escribe ni los modifica. Son 100%
Go puro (`testing` stdlib + tipos de `bubbletea`), construyendo `Model` y
`tea.Msg` a mano — sin I/O real, sin shellear nada, sin `tea.NewProgram`.
Casos de `UpdateModel`: `gatesLoadedMsg` con summary+err nil, `gatesLoadedMsg`
con err no nil, `contractsLoadedMsg` con summary+err nil (verifica que gates y
ViewMode/Quitting se preservan), `contractsLoadedMsg` con err no nil, `tea.KeyMsg`
"q" (quita + cmd es tea.Quit), "ctrl+c" (idem), "g" (setea ViewMode="gates",
cmd nil, resto sin cambios), "c" (setea ViewMode="contracts", cmd nil, resto
sin cambios), otra tecla "x" (NO cambia nada, incluido ViewMode, cmd nil),
`tea.WindowSizeMsg` (no cambia, cmd nil), y un msg propio no reconocido (no
cambia, cmd nil, sin panic). Casos de `View`: quitting (-> "", sin linea de
ayuda), quitting-gana-sobre-contracts (-> ""), error gates (-> "error:
...\n" + helpLine), loading gates (-> "cargando gates...\n" + helpLine), resumen
gates normal (-> summary + "\n" + helpLine, sin doble newline FINAL), zero-
value ViewMode es gates (-> "cargando gates...\n" + helpLine ignorando campos
de contracts), error contracts (-> "error: ...\n" + helpLine), loading
contracts (-> "cargando contratos...\n" + helpLine), resumen contracts normal
(-> Contracts + "\n" + helpLine), y gates-ignora-campos-de-contracts. El
literal exacto de la linea de ayuda se congela en el test como `wantHelpLine`
(declarado aparte del const del paquete `helpLine`, para que el oraculo sea
independiente del target). `test_command: "go test -C tui ./..."` corre desde
la RAIZ del repo (forzado por `test_cwd: ../..`): el flag `-C tui` cambia a
`tui/` antes de correr y encuentra `tui/go.mod` hacia abajo, funcione desde el
cwd que sea SIEMPRE Y CUANDO el cwd de partida sea la raiz del repo. Asi el
mismo `test_command` pasa para el gate CCDD externo (`run_integration_gate`,
que por default usaria el directorio del target como cwd salvo `test_cwd`) Y
para el Nivel 1 propio del repo (`scripts/validate_test_commands.py`, que
corre TODOS los `test_command` SIEMPRE con cwd = raiz del repo, sin override).
Exactamente el patron de `tui-gates-summarize.md`/`kdd-contracts-status-summarize.md`.)

El test ADICIONAL `tui/internal/ui/pipe_test.go` (NO sellado, NO en `tests:`)
ejercita los `tea.Cmd` reales devueltos por `Init()` del wrapper llamandolos
como funciones — eso SI shellea a python de verdad (unica forma de probar los
pipes end-to-end sin lanzar la TUI). Es OPT-IN: se saltea por defecto
(`LAZYKDD_RUN_PIPE` vacio) para que el `go test ./...` default sea 100% puro
(HECHO 2) y para ROMPER la recursion con `validate_test_commands` (el
`go test -C tui ./...` de este contrato, corrido por `gates run-all`,
dispararia este test que shellea `gates run-all`/`contracts status` otra vez).
Para correrlo de verdad: `LAZYKDD_RUN_PIPE=1 go test -C tui -run
TestInitPipeline -v ./internal/ui/`. El test consume (`os.Unsetenv`) el flag
antes de shellerar, asi el `go test` anidado que dispara `validate_test_commands`
(dentro del `gates run-all`) lo ve vacio y saltea — recursion rota en
profundidad 1. Cubre AMBOS pipes (gates -> `gatesLoadedMsg` con
`"overall_ok="`, contracts -> `contractsLoadedMsg` con `"contracts="`).

## Constraints
- PARAR y reportar si necesitas conectarte a la red o invocar un LLM.
- PARAR y reportar si el `intent` exige tocar un archivo fuera de
  `touch_only` (probablemente signifique que la spec esta mal escrita).
- PARAR y reportar si extender `UpdateModel` sin romper ninguno de los tests
  viejos resulta imposible (los tests viejos de `UpdateModel` se preservan
  intactos: "q"/"ctrl+c" siguen igual, "x"/WindowSizeMsg/unknown siguen sin
  cambios; solo `View` cambia al agregar la linea de ayuda, y esos tests se
  actualizan con el nuevo esperado — re-sellado via `tests_sha256`).

## Budget note
`UpdateModel` extendida mide `cyclomatic = 7` (un case mas `contractsLoadedMsg`
y dos cases mas `"g"`/`"c"` en el nested switch) y `function_length = 30` (la
metrica del gate cuenta un poco mas por los comments; el budget `lines_max:
45` deja margen). El budget declarado sube de los `cyclomatic_max: 9` /
`lines_max: 30` del contrato previo a `cyclomatic_max: 9` / `lines_max: 45`
(cyclomatic no crecio lo suficiente para mover el tope, lines si por la
rama nueva de contracts y los comments); `nesting_max: 3` (medido 2) y
`params_max: 2` (medido 2) sin cambios. Todo bajo los topes globales firmados
(cyclomatic 20, nesting 4, params 5, lines 80).