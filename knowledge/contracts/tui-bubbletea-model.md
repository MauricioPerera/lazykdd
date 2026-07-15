---
type: 'Task Contract'
title: 'TUI: Bubble Tea Model (capa interactiva, dos vistas + scaffolding)'
description: 'Capa interactiva de la Piel 3: un programa Bubble Tea (arquitectura Elm) que shellea al CLI Python, muestra el resumen de gates O de contratos (alterna con g/c), recarga con r, y crea contratos nuevos con un modo de scaffolding interactivo (tecla n, enter confirma, esc cancela). Logica pura UpdateModel/View (target, testeable) separada del wrapper tea.Model (wiring, no testeado).'
tags: ['ccdd', 'tui', 'lazykdd', 'go']

task: tui-bubbletea-model
intent: "Gobernar la transicion de estado del TUI (gates + contracts + refresh + scaffolding) con una funcion UpdateModel pura."
language: go
target: tui/internal/ui/model.go
signature: "func UpdateModel(m Model, msg tea.Msg) (Model, tea.Cmd)"
test_command: "go test -C tui ./..."
test_cwd: ../..
budget:
  cyclomatic_max: 14
  nesting_max: 3
  params_max: 2
  lines_max: 70
tests: "tui/internal/ui/model_test.go"
tests_sha256: "0cc3b91a860f581f679d1616673363cff6fd66a3fb92ead183b7d4b26b108393"
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
el resumen de gates O de contratos (el usuario alterna con `g`/`c`), recarga
ambos paneles con `r` (refresh) sin reiniciar el programa, y crea contratos
nuevos via un modo de scaffolding interactivo: `n` entra en modo input, el
usuario tipea un nombre kebab-case, `Enter` confirma y dispara `contracts
scaffold <nombre> --json` de verdad, `Esc` cancela. La funcion que gobierna este
contrato es `UpdateModel(m Model, msg tea.Msg) (Model, tea.Cmd)`: PURA (sin I/O,
sin red, sin goroutines, sin llamar a Bubble Tea real mas alla de sus TIPOS),
separada del wiring de I/O real (el wrapper `tea.Model` en `program.go`, glue,
no testeado, mismo criterio que `main.go`). `View(m Model) string` tambien es
pura y esta cubierta por el mismo oraculo congelado, pero NO es el target
principal del gate de complejidad (ver seccion Do/Don't: decision de un solo
contrato). Esta actualizacion EXTIENDE el comportamiento previo (gates +
contracts + refresh) con el modo scaffolding; la `signature` de `UpdateModel`
NO cambio (sigue siendo `(m Model, msg tea.Msg) (Model, tea.Cmd)`).

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
    // --- scaffolding ---
    Scaffolding   bool    // true mientras el usuario tipea un nombre (modo input)
    ScaffoldInput string  // buffer de texto tipeado hasta ahora
    ScaffoldMsg   string  // resultado del ultimo intento (exito o error), "" si ninguno
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

type scaffoldDoneMsg struct {
    path string
    err  error
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
- `msg` es `scaffoldDoneMsg` (nuevo): setea `ScaffoldMsg` a `"creado: " +
  msg.path` si `msg.err == nil`, o `"error: " + msg.err.Error()` si no. El
  resto de los campos sin cambios (`Scaffolding` ya era `false` desde que se
  apreto Enter; `ScaffoldInput` NO se limpia -- se pisa la proxima vez que se
  entra en modo scaffolding con "n"), `tea.Cmd` nil.
- `msg` es `tea.KeyMsg` Y `m.Scaffolding` es `true` (MODO INPUT, precedencia
  sobre TODO lo demas -- en este modo "g"/"c"/"r"/"q" son texto a tipear, NO
  comandos): `UpdateModel` delega a `handleScaffoldKey(m, msg)` (una sola linea
  de delegacion, bajo costo). El comportamiento por `msg.Type`:
  - `tea.KeyEsc`: `Scaffolding: false`, `ScaffoldInput: ""`, resto sin cambios
    (incluido `ScaffoldMsg`, que NO se toca al cancelar). `tea.Cmd` nil.
  - `tea.KeyEnter`: `Scaffolding: false` (sale del modo input), `ScaffoldInput`
    se CONSERVA sin cambios en el `Model` que devuelve (el wiring en
    `program.go` lo lee para saber que nombre scaffoldear), `tea.Cmd` nil (la
    funcion pura no shellea).
  - `tea.KeyBackspace`: si `ScaffoldInput` no esta vacio, le saca el ULTIMO
    RUNE (no el ultimo byte -- `[]rune` para ser seguro con UTF-8); si ya esta
    vacio, sin cambios. `tea.Cmd` nil.
  - `tea.KeyRunes`: appendea `string(msg.Runes)` a `ScaffoldInput`. NO valida
    kebab-case aca (lo hace el CLI Python del lado del shell-out; un nombre
    invalido llega como `ScaffoldMsg` de error via `scaffoldDoneMsg`). `tea.Cmd`
    nil.
  - cualquier otro `tea.KeyMsg` (flechas, tab, etc.): sin cambios. `tea.Cmd` nil.
- `msg` es `tea.KeyMsg` Y `m.Scaffolding` es `false` (modo normal):
  - `msg.String()` es `"q"` o `"ctrl+c"`: devuelve `m` con `Quitting: true` y
    como `tea.Cmd` devuelve `tea.Quit`. (Comportamiento historico, sin cambios.)
  - `msg.String()` es `"g"`: devuelve `m` con `ViewMode: "gates"`, resto sin
    cambios, `tea.Cmd` nil. (Sin cambios.)
  - `msg.String()` es `"c"`: devuelve `m` con `ViewMode: "contracts"`, resto
    sin cambios, `tea.Cmd` nil. (Sin cambios.)
  - `msg.String()` es `"r"` (refresh): devuelve `m` con `Loading: true` y
    `ContractsLoading: true`, `Err: nil` y `ContractsErr: nil` (limpia los
    errores viejos), el resto (`Summary`/`Contracts`/`ViewMode`/`Quitting`) SIN
    CAMBIOS, `tea.Cmd` nil. La funcion pura NO sabe shellear: el refresh real
    (`tea.Batch` de `loadGates`/`loadContracts`) lo dispara el wiring en
    `program.Update` al ver esta misma tecla. (Sin cambios.)
  - `msg.String()` es `"n"` (nuevo): devuelve `m` con `Scaffolding: true`,
    `ScaffoldInput: ""`, `ScaffoldMsg: ""` (limpia el resultado del intento
    anterior), resto sin cambios, `tea.Cmd` nil.
  - Cualquier otra tecla: devuelve `m` SIN CAMBIOS, `tea.Cmd` nil.
- Cualquier otro `msg` (`tea.WindowSizeMsg`, lo que sea): devuelve `m` SIN
  CAMBIOS, `tea.Cmd` nil.
- Nunca panic con ningun `tea.Msg`, tipado o no (type switch con default, sin
  type assertion sin `, ok`).

`handleScaffoldKey(m Model, key tea.KeyMsg) (Model, tea.Cmd)` es el helper
PURO extraido de `UpdateModel` por presupuesto de complejidad (ver Budget note y
trade-offs en el REPORT). Vive en el MISMO archivo `model.go`, NO es el target
del gate (el gate sigue midiendo solo `UpdateModel` via `signature`) y NO tiene
su propio contrato CCDD separado (mismo criterio que un helper de la funcion
contratada), pero SI tiene sus propios casos de test en el oraculo congelado
(`model_test.go`). Es pura: sin I/O, sin shellear (el shell-out real lo dispara
el wiring en `program.Update` al ver el Enter confirmado).

`View` renderiza la `Model` a un string. Precedencia: `Quitting` > `Scaffolding`
> (segun `ViewMode`) `Err/ContractsErr` > `Loading/ContractsLoading` > resumen, y
la linea de ayuda al final (salvo en quitting y scaffolding, que devuelven
vistas propias):
- `m.Quitting` true: `""` (Bubble Tea limpia la pantalla al salir). Tiene
  precedencia sobre todo, incluida la linea de ayuda y el modo scaffolding.
- `m.Scaffolding` true (sin estar quitting): devuelve una vista DISTINTA que
  reemplaza TODO lo demas (sin linea de ayuda, sin newline final -- decision
  documentada: consistente con `kdd.Summarize`/`kdd.SummarizeContractsStatus`
  que tampoco lo llevan). Formato EXACTO:
  `"nuevo contrato (kebab-case), enter confirma, esc cancela:\n> " +
  m.ScaffoldInput`.
- Si no esta quitting ni scaffolding, el cuerpo depende de `ViewMode`:
  - `ViewMode == "contracts"`: usa los campos de contracts. `ContractsErr !=
    nil` -> `"error: " + ContractsErr.Error() + "\n"`; si no, `ContractsLoading`
    -> `"cargando contratos...\n"`; si no, `Contracts + "\n"`.
  - cualquier otro valor de `ViewMode` (incluido el zero-value `""`, que se
    trata IGUAL que `"gates"`): usa los campos de gates. `Err != nil` ->
    `"error: " + Err.Error() + "\n"`; si no, `Loading` -> `"cargando
    gates...\n"`; si no, `Summary + "\n"`.
- Si `m.ScaffoldMsg != ""` (vista normal, no scaffolding): se agrega una linea
  `"\n" + m.ScaffoldMsg` ANTES de la linea de ayuda. Si `ScaffoldMsg` esta
  vacio, no se agrega nada (el layout queda byte-identico al comportamiento
  previo a esta tarea).
- Al cuerpo se le agrega SIEMPRE al final la linea de ayuda EXACTA:
  `"\n[g]ates [c]ontracts [r]efresh [n]ew [q]uit"` (un `\n` + el literal).

## Invariants
- `UpdateModel` es PURA: sin I/O, sin red, sin goroutines, sin `os/exec`, sin
  `os.Exit`, nunca paniquea (type switch con default; un msg no reconocido
  deja el model igual). `handleScaffoldKey` tambien es pura.
- Para `gatesLoadedMsg`, `Loading` queda SIEMPRE false y `Summary`/`Err` son
  EXACTAMENTE los del msg; `Quitting`/`ViewMode`/los campos de contracts se
  preservan del model entrante.
- Para `contractsLoadedMsg`, `ContractsLoading` queda SIEMPRE false y
  `Contracts`/`ContractsErr` son EXACTAMENTE los del msg; los campos de gates
  y `ViewMode`/`Quitting` se preservan.
- Para `scaffoldDoneMsg`, `ScaffoldMsg` queda seteado al formato exacto
  (`"creado: <path>"` o `"error: <err>"`); `Scaffolding` queda false, `ScaffoldInput`
  se preserva del model entrante (NO se limpia), cmd nil.
- Para "q"/"ctrl+c", el `tea.Cmd` devuelto ES `tea.Quit`; para cualquier otra
  tecla o msg (incluida "n", el Enter/Esc/Backspace/Runes en modo scaffolding, y
  "r" en modo normal), el cmd es nil. (El refresh real y el scaffold real los
  dispara el wiring en `program.Update`, no `UpdateModel`.)
- Para "r" (refresh), `Loading` y `ContractsLoading` quedan SIEMPRE true y
  `Err`/`ContractsErr` quedan SIEMPRE nil; `Summary`/`Contracts`/`ViewMode`/
  `Quitting` se preservan EXACTAMENTE del model entrante.
- Para "n", `Scaffolding` queda SIEMPRE true, `ScaffoldInput` y `ScaffoldMsg`
  quedan SIEMPRE ""; el resto del model se preserva.
- En modo scaffolding (`m.Scaffolding` true), TODA `tea.KeyMsg` se delega a
  `handleScaffoldKey` ANTES del switch de comandos: "g"/"c"/"r"/"q" son texto
  (se appendean a `ScaffoldInput`), NO comandos (no cambian `ViewMode`, no
  ponen `Quitting`, no disparan `tea.Quit`). Esc cancela (limpia input, preserva
  `ScaffoldMsg`); Enter confirma (conserva input); Backspace saca el ultimo
  rune; Runes appendea.
- `View` nunca devuelve un string con doble `\n` FINAL (el unico newline al
  final es el del cuerpo; la linea de ayuda no termina en `\n`); cuando esta
  quitting devuelve `""` (sin linea de ayuda); cuando esta scaffolding devuelve
  el prompt SIN trailing newline y SIN linea de ayuda.
- El zero-value de `ViewMode` (`""`) se comporta en `View` IGUAL que `"gates"`.
- 100% del comportamiento gobernable es reproducible desde el oraculo
  congelado (`model_test.go`) construyendo `Model`/`tea.Msg` a mano, sin
  shellear nada.

## Examples
- `UpdateModel(Model{Loading:true}, gatesLoadedMsg{summary:"overall_ok=true pass=1 fail=0", err:nil})` -> `Model{Summary:"overall_ok=true pass=1 fail=0", Loading:false}` con cmd nil.
- `UpdateModel(Model{Loading:true}, gatesLoadedMsg{summary:"", err:errors.New("boom")})` -> `Model{Err:<boom>, Loading:false}` con cmd nil.
- `UpdateModel(Model{ContractsLoading:true,ViewMode:"gates"}, contractsLoadedMsg{summary:"contracts=1\na: draft", err:nil})` -> `Model{Contracts:"contracts=1\na: draft", ContractsLoading:false, ViewMode:"gates"}` con cmd nil.
- `UpdateModel(Model{ContractsLoading:true}, contractsLoadedMsg{summary:"", err:errors.New("boom")})` -> `Model{ContractsErr:<boom>, ContractsLoading:false}` con cmd nil.
- `UpdateModel(Model{ScaffoldInput:"my-task"}, scaffoldDoneMsg{path:"knowledge/contracts/my-task.md", err:nil})` -> `Model{ScaffoldMsg:"creado: knowledge/contracts/my-task.md", ScaffoldInput:"my-task"}` con cmd nil.
- `UpdateModel(Model{ScaffoldInput:"bad"}, scaffoldDoneMsg{path:"", err:errors.New("invalid name")})` -> `Model{ScaffoldMsg:"error: invalid name", ScaffoldInput:"bad"}` con cmd nil.
- `UpdateModel(Model{}, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("q")})` -> `Model{Quitting:true}` con cmd = `tea.Quit`.
- `UpdateModel(Model{}, tea.KeyMsg{Type: tea.KeyCtrlC})` -> `Model{Quitting:true}` con cmd = `tea.Quit`.
- `UpdateModel(Model{ViewMode:"contracts"}, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("g")})` -> `Model{ViewMode:"gates"}` con cmd nil.
- `UpdateModel(Model{ViewMode:"gates"}, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("c")})` -> `Model{ViewMode:"contracts"}` con cmd nil.
- `UpdateModel(Model{Summary:"old gates", Err:errors.New("e"), Loading:false, Contracts:"old contracts", ContractsErr:errors.New("ce"), ContractsLoading:false, ViewMode:"contracts"}, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("r")})` -> `Model{Summary:"old gates", Err:nil, Loading:true, Contracts:"old contracts", ContractsErr:nil, ContractsLoading:true, ViewMode:"contracts"}` con cmd nil.
- `UpdateModel(Model{ViewMode:"contracts", ScaffoldMsg:"prev"}, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("n")})` -> `Model{Scaffolding:true, ScaffoldInput:"", ScaffoldMsg:"", ViewMode:"contracts"}` con cmd nil.
- `UpdateModel(Model{Scaffolding:true, ScaffoldInput:"ab"}, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("cde")})` -> `Model{Scaffolding:true, ScaffoldInput:"abcde"}` con cmd nil.
- `UpdateModel(Model{Scaffolding:true, ScaffoldInput:"abc"}, tea.KeyMsg{Type: tea.KeyBackspace})` -> `Model{Scaffolding:true, ScaffoldInput:"ab"}` con cmd nil.
- `UpdateModel(Model{Scaffolding:true, ScaffoldInput:"typed", ScaffoldMsg:"prev"}, tea.KeyMsg{Type: tea.KeyEsc})` -> `Model{Scaffolding:false, ScaffoldInput:"", ScaffoldMsg:"prev"}` con cmd nil (ScaffoldMsg preservado al cancelar).
- `UpdateModel(Model{Scaffolding:true, ScaffoldInput:"my-task"}, tea.KeyMsg{Type: tea.KeyEnter})` -> `Model{Scaffolding:false, ScaffoldInput:"my-task"}` con cmd nil (input conservado para el wiring).
- `UpdateModel(Model{Scaffolding:true, ScaffoldInput:"x", ViewMode:"contracts"}, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("g")})` -> `Model{Scaffolding:true, ScaffoldInput:"xg", ViewMode:"contracts"}` con cmd nil (g es texto en modo input, NO cambia ViewMode).
- `UpdateModel(Model{Loading:true,ViewMode:"contracts"}, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("x")})` -> model sin cambios, cmd nil.
- `UpdateModel(Model{Loading:true}, tea.WindowSizeMsg{Width:80, Height:24})` -> model sin cambios, cmd nil.
- `View(Model{Quitting:true, Err:errors.New("e")})` -> `""`.
- `View(Model{Quitting:true, Scaffolding:true, ScaffoldInput:"x"})` -> `""` (quitting gana sobre scaffolding).
- `View(Model{Scaffolding:true, ScaffoldInput:"my-task"})` -> `"nuevo contrato (kebab-case), enter confirma, esc cancela:\n> my-task"`.
- `View(Model{Scaffolding:true, ScaffoldInput:""})` -> `"nuevo contrato (kebab-case), enter confirma, esc cancela:\n> "`.
- `View(Model{Err:errors.New("boom"), Loading:true})` -> `"error: boom\n\n[g]ates [c]ontracts [r]efresh [n]ew [q]uit"`.
- `View(Model{Loading:true})` -> `"cargando gates...\n\n[g]ates [c]ontracts [r]efresh [n]ew [q]uit"`.
- `View(Model{Summary:"overall_ok=true pass=0 fail=0"})` -> `"overall_ok=true pass=0 fail=0\n\n[g]ates [c]ontracts [r]efresh [n]ew [q]uit"`.
- `View(Model{Summary:"s", ScaffoldMsg:"creado: knowledge/contracts/foo.md"})` -> `"s\n\ncreado: knowledge/contracts/foo.md\n[g]ates [c]ontracts [r]efresh [n]ew [q]uit"`.
- `View(Model{Summary:"s", ScaffoldMsg:""})` -> `"s\n\n[g]ates [c]ontracts [r]efresh [n]ew [q]uit"` (ScaffoldMsg vacio no agrega nada).
- `View(Model{ViewMode:"contracts", Contracts:"contracts=2\na: draft"})` -> `"contracts=2\na: draft\n\n[g]ates [c]ontracts [r]efresh [n]ew [q]uit"`.

## Do / Don't
- DO: type switch sobre `msg` (`switch msg := msg.(type)`) con `case gatesLoadedMsg`,
  `case contractsLoadedMsg`, `case scaffoldDoneMsg`, `case tea.KeyMsg` (con una
  guarda `if m.Scaffolding { return handleScaffoldKey(m, msg) }` al inicio del
  case, seguida de un nested switch sobre `msg.String()` con cases
  `"q","ctrl+c"` / `"g"` / `"c"` / `"r"` / `"n"` / `default`), y `default`
  externo. Nada de type assertion sin `, ok`.
- DO: extraer la logica de teclas en modo scaffolding a `handleScaffoldKey(m
  Model, key tea.KeyMsg) (Model, tea.Cmd)` (switch sobre `key.Type` con cases
  `tea.KeyEsc` / `tea.KeyEnter` / `tea.KeyBackspace` / `tea.KeyRunes` /
  `default`) y que `UpdateModel` la llame con una sola linea de delegacion cuando
  `m.Scaffolding` es true. `handleScaffoldKey` es pura, vive en `model.go`, no
  es target del gate (el gate mide solo `UpdateModel` via `signature`) ni tiene
  contrato propio, pero tiene sus propios tests en el oraculo congelado.
- DO: devolver `tea.Quit` (la funcion del paquete) para "q"/"ctrl+c", no
  inventar un cmd propio. Para "g"/"c"/"r"/"n" y cualquier otra tecla o msg
  (incluido Esc/Enter/Backspace/Runes en modo scaffolding), devolver cmd nil.
- DO: separar la logica pura (`model.go`: `Model`, `gatesLoadedMsg`,
  `contractsLoadedMsg`, `scaffoldDoneMsg`, `UpdateModel`, `handleScaffoldKey`,
  `View`, `helpLine`) del wiring (`program.go`: el wrapper `tea.Model` que
  shellea en `Init()` y en `loadScaffold`). Mismo criterio que `gates.go`
  (pura) vs `main.go` (glue).
- DO: el wrapper `Init()` shellea AMBAS cargas en paralelo con `tea.Batch`
  (`gates run-all --json` -> `gatesLoadedMsg` Y `contracts status --json` ->
  `contractsLoadedMsg`). Mismo patron de `os/exec` que `main.go` (path
  relativo, asume cwd = repo root). Un `*exec.ExitError` NO es error de
  shell-out (se conserva stdout y se resume igual); solo falla si no arranca el
  proceso. La `Model` inicial en `NewProgram()` arranca con `Loading: true` y
  `ContractsLoading: true` (ViewMode queda en zero-value "", que View trata como
  "gates").
- DO: nuevo metodo `func (p program) loadScaffold(name string) tea.Cmd` en
  `program.go` que shellea `python scripts/kdd_cli.py contracts scaffold <name>
  --json` (mismo patron `os/exec` que `loadGates`/`loadContracts`), parsea el
  stdout con `encoding/json` directo en `program.go` (es glue, no una funcion
  pura separada ni contrato propio) y devuelve `scaffoldDoneMsg{path, err}`: si
  el JSON trae `"error"`, `err = fmt.Errorf(...)`; si trae `"created":true`,
  `err` es nil y `path` es el valor de `"path"`. Un `*exec.ExitError` (exit 1
  del CLI por nombre no kebab-case o contrato ya existente) NO es error de
  shell-out: se conserva stdout y se parsea igual.
- DO: el wrapper `Update(msg)` en `program.go` PRIMERO delega a `UpdateModel`
  (capturando ANTES `wasScaffolding := p.Model.Scaffolding` y `input :=
  p.Model.ScaffoldInput` del Model ENTRANTE), y DESPUES detecta DOS casos
  puntuales: (1) si `msg` es `tea.KeyMsg` con `key.Type == tea.KeyEnter` Y
  `wasScaffolding` Y `input != ""`, el `tea.Cmd` que devuelve `Update` es
  `next.loadScaffold(input)` (NO el nil que devolvio `UpdateModel`); un Enter
  con buffer vacio NO dispara scaffold (ahorra shell-out inutil) pero el modo
  input igual se cierra. (2) si `msg` es `tea.KeyMsg` con `key.String() == "r"`
  Y `!wasScaffolding` (en modo input "r" es texto, no comando), el `tea.Cmd` es
  `tea.Batch(next.loadGates(), next.loadContracts())`. Para cualquier otro msg,
  el cmd es el que devolvio `UpdateModel` tal cual. Es wiring (glue, no testeado
  por el oraculo congelado).
- DO: `main.go` lanza `tea.NewProgram(ui.NewProgram()).Run()`; si `Run()`
  devuelve error, stderr + exit 1; si no, exit 0. (Sin cambios.)
- DO: un solo contrato para `UpdateModel` (target del gate) y `View` (pura,
  cubierta por el mismo oraculo pero NO target principal) y `handleScaffoldKey`
  (helper, target secundario con sus propios tests pero NO target del gate).
  Decision: las tres viven en el mismo archivo `model.go` y el mismo oraculo
  `model_test.go` porque son co-dependientes (el Elm las usa juntas) y triviales
  de complejidad; contratos separados aniadirian overhead administrativo sin
  aislar riesgo real (documentado en el REPORT).
- DON'T: incluir `subprocess`/`os.exec` en `forbids` — `UpdateModel`/`View`/
  `handleScaffoldKey` son puras y no los usan; el wrapper `Init()`/`loadScaffold`
  y `main.go` si shellean (analogeo a `subprocess` de Python), pero son glue
  fuera del target y fuera del oraculo congelado. `forbids` es `['network','llm']`.
- DON'T: agregar scroll, refresco periodico, colores/estilos con `lipgloss`, ni
  mas paneles alla de gates + contracts. Dos "screens" que se alternan con g/c,
  un solo "screen" visible a la vez, mas el overlay de scaffolding.
- DON'T: auto-refrescar el panel de contracts despues de un scaffold exitoso
  (queda para una tarea futura; el usuario aprieta "r" a mano). Tampoco valides
  kebab-case en Go (lo hace el CLI Python) ni agregues un indicador visual de
  "creando..." (el shell-out de scaffold es rapido).
- DON'T: correr `tea.NewProgram(...).Run()` dentro de los tests (es bloqueante y
  ocupa la terminal). El oraculo congelado solo ejercita `UpdateModel`/`View`/
  `handleScaffoldKey` como funciones puras; el pipe end-to-end (que SI shellea a
  python) vive en `pipe_test.go` como test ADICIONAL opt-in (salteado por defecto
  via `LAZYKDD_RUN_PIPE=1`), fuera del oraculo sellado.
- DON'T: resolver las carreras de refrescos repetidos en esta version (varios
  "r" seguidos pueden cruzar respuestas viejas con nuevas -- LIMITACION
  ACEPTADA, documentada en el REPORT). Tampoco agregues un indicador visual de
  "refrescando" distinto al "cargando..." que ya existe.
- DON'T: tocar `tui/internal/kdd/gates.go`, su contrato `tui-gates-summarize.md`,
  `scripts/`, ni `.agents/`.

## Tests
(Los tests estan en `tui/internal/ui/model_test.go`, oraculo congelado sellado
por `tests_sha256`: el implementador no los escribe ni los modifica. Son 100%
Go puro (`testing` stdlib + tipos de `bubbletea`), construyendo `Model` y
`tea.Msg` a mano — sin I/O real, sin shellear nada, sin `tea.NewProgram`.
Casos de `UpdateModel`: `gatesLoadedMsg` con summary+err nil, `gatesLoadedMsg`
con err no nil, `contractsLoadedMsg` con summary+err nil (verifica que gates y
ViewMode/Quitting se preservan), `contractsLoadedMsg` con err no nil,
`scaffoldDoneMsg` exito (ScaffoldMsg = "creado: <path>", ScaffoldInput
conservado), `scaffoldDoneMsg` error (ScaffoldMsg = "error: <err>"), `tea.KeyMsg`
"q" (quita + cmd es tea.Quit), "ctrl+c" (idem), "g" (ViewMode="gates", cmd nil),
"c" (ViewMode="contracts", cmd nil), "r" (refresh: Loading/ContractsLoading true,
Err/ContractsErr nil incluso con error previo, resto sin cambios, cmd nil), "r"
desde estado limpio, "n" (Scaffolding true, ScaffoldInput "", ScaffoldMsg "
limpiado, resto sin cambios, cmd nil), otra tecla "x" (no cambia nada, cmd nil),
`tea.WindowSizeMsg` (no cambia, cmd nil), y un msg propio no reconocido (no
cambia, cmd nil, sin panic). Modo scaffolding (delegacion a handleScaffoldKey):
KeyRunes appendea, KeyBackspace saca el ultimo rune, KeyBackspace con buffer
vacio no cambia, KeyEsc cancela (limpia input, preserva ScaffoldMsg), KeyEnter
con buffer no vacio conserva input y deja Scaffolding false, KeyEnter con buffer
vacio deja Scaffolding false sin crashear, otra tecla (KeyUp) no cambia, y un
test EXPLICITO de que "g"/"c"/"r"/"q" mientras Scaffolding es true se tratan
como texto (appendean, no cambian ViewMode, no ponen Quitting, cmd nil).
Casos directos de `handleScaffoldKey`: Runes appendea, Backspace saca ultimo
rune, Backspace seguro con UTF-8 ('é' = 2 bytes -> saca 1 rune), Esc limpia y
preserva ScaffoldMsg, Enter conserva input, otra tecla (KeyDown) no cambia.
Casos de `View`: quitting (-> ""), quitting-gana-sobre-contracts (-> ""),
quitting-gana-sobre-scaffolding (-> ""), scaffolding prompt exacto (con input y
con buffer vacio, sin trailing newline), error gates, loading gates, resumen
gates normal (sin doble newline FINAL), zero-value ViewMode es gates, error
contracts, loading contracts, resumen contracts normal, gates-ignora-campos-de-
contracts, normal con ScaffoldMsg no vacio agrega la linea extra (gates y
contracts), y normal con ScaffoldMsg vacio NO agrega nada (byte-identico al
comportamiento previo). El literal exacto de la linea de ayuda se congela en el
test como `wantHelpLine = "\n[g]ates [c]ontracts [r]efresh [n]ew [q]uit"`
(declarado aparte del const del paquete `helpLine`, para que el oraculo sea
independiente del target). `test_command: "go test -C tui ./..."` corre desde
la RAIZ del repo (forzado por `test_cwd: ../..`): el flag `-C tui` cambia a
`tui/` antes de correr y encuentra `tui/go.mod` hacia abajo, funcione desde el
cwd que sea SIEMPRE Y CUANDO el cwd de partida sea la raiz del repo. Asi el
mismo `test_command` pasa para el gate CCDD externo (`run_integration_gate`, que
por default usaria el directorio del target como cwd salvo `test_cwd`) Y para el
Nivel 1 propio del repo (`scripts/validate_test_commands.py`, que corre TODOS
los `test_command` SIEMPRE con cwd = raiz del repo, sin override). Exactamente
el patron de `tui-gates-summarize.md`/`kdd-contracts-status-summarize.md`.)

El test ADICIONAL `tui/internal/ui/pipe_test.go` (NO sellado, NO en `tests:`)
ejercita los `tea.Cmd` reales devueltos por `Init()`/`loadScaffold()` del
wrapper llamandolos como funciones — eso SI shellea a python de verdad (unica
forma de probar los pipes end-to-end sin lanzar la TUI). Es OPT-IN: se saltea
por defecto (`LAZYKDD_RUN_PIPE` vacio) para que el `go test ./...` default sea
100% puro (HECHO 2) y para ROMPER la recursion con `validate_test_commands`
(el `go test -C tui ./...` de este contrato, corrido por `gates run-all`,
dispararia este test que shellea `gates run-all`/`contracts status` otra vez).
`TestInitPipelineScaffold` shellea `contracts scaffold` con un nombre
DESCARTABLE (`zz-pipe-test-scaffold-tmp`), verifica que crea el archivo y lo
BORRA al final (`t.Cleanup`, registrado ANTES de shellerar para que corra incluso
si el test falla); scaffold NO dispara go test, asi que no hay recursion, pero
igual usa el opt-in para el chdir al repo root. Para correrlo de verdad:
`LAZYKDD_RUN_PIPE=1 go test -C tui -run TestInitPipeline -v ./internal/ui/`. El
test consume (`os.Unsetenv`) el flag antes de shellerar, asi el `go test` anidado
que dispara `validate_test_commands` lo ve vacio y saltea — recursion rota en
profundidad 1.

## Constraints
- PARAR y reportar si necesitas conectarte a la red o invocar un LLM.
- PARAR y reportar si el `intent` exige tocar un archivo fuera de
  `touch_only` (probablemente signifique que la spec esta mal escrita).
- PARAR y reportar si extender `UpdateModel` sin romper ninguno de los tests
  viejos resulta imposible (los tests viejos de `UpdateModel` se preservan
  intactos: "q"/"ctrl+c" siguen igual, "x"/WindowSizeMsg/unknown siguen sin
  cambios; solo `View` cambia al actualizar la linea de ayuda a `[n]ew` y
  agregar el prompt de scaffolding + la linea de ScaffoldMsg, y esos tests se
  actualizan con el nuevo esperado — re-sellados via `tests_sha256`).

## Budget note
`UpdateModel` extendida (con el case `scaffoldDoneMsg`, la guarda `if
m.Scaffolding` de delegacion a `handleScaffoldKey`, y el case `"n"`) mide
`cyclomatic = 12` (un case `scaffoldDoneMsg` con su `if msg.err != nil`, la
guarda `if m.Scaffolding`, y un case `"n"` mas, sobre los 8 previos de
gates+contracts+refresh). La logica de input (Esc/Enter/Backspace/Runes/other,
5 cases) se EXTRAE a `handleScaffoldKey` para no sumarlos a `UpdateModel`; sin
esa extraccion `UpdateModel` llegaria a ~17. `function_length` con comments
internos incluidos mide 66 (la metrica del gate cuenta los comments internos;
`measure_complexity` sin comments reporta 51). El budget sube a
`cyclomatic_max: 14` (medido 12, margen 2) y `lines_max: 70` (medido 66, margen
4). `nesting_max: 3` (medido 2) y `params_max: 2` (medido 2) sin cambios. Todo
bajo los topes globales firmados (cyclomatic 20, nesting 4, params 5, lines 80).
La subida de `cyclomatic_max` de 9 a 14 y de `lines_max` de 50 a 70 es el costo
de extender `UpdateModel` con el modo scaffolding + el resultado del shell-out;
es informacion util documentada en el REPORT, no un bloqueo. `handleScaffoldKey`
NO la mide el gate (no es el target), pero su complejidad es baja (un switch
sobre `key.Type` con 5 cases, cyclomatic ~5, ~18 lineas).