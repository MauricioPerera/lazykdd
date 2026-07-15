---
type: 'Task Contract'
title: 'TUI: Bubble Tea Model (capa interactiva, dos paneles navegables + detalle + refresh + scaffolding)'
description: 'Capa interactiva de la Piel 3: un programa Bubble Tea (arquitectura Elm) que shellea al CLI Python, muestra el panel de GATES navegable (flechas mueven cursor, Enter corre ESE gate via gates run <name> --json, Esc vuelve) O la lista NAVEGABLE de contratos (Enter abre el .md completo), recarga con r, y crea contratos nuevos con un modo de scaffolding interactivo (tecla n). Logica pura UpdateModel/View (target, dispatcher delgado, testeable) separada del wrapper tea.Model (wiring, no testeado).'
tags: ['ccdd', 'tui', 'lazykdd', 'go']

task: tui-bubbletea-model
intent: "Gobernar la transicion de estado del TUI (gates navegable + contracts navegable + detalle + refresh + scaffolding) con una funcion UpdateModel pura."
language: go
target: tui/internal/ui/model.go
signature: "func UpdateModel(m Model, msg tea.Msg) (Model, tea.Cmd)"
test_command: "go test -C tui ./..."
test_cwd: ../..
budget:
  cyclomatic_max: 8
  nesting_max: 3
  params_max: 2
  lines_max: 40
tests: "tui/internal/ui/model_test.go"
tests_sha256: "a1dbc70f1e7f2e2305a83405a5b802725d330da864c8845c1af51805718746ac"
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
[tui-gates-list-parse](./tui-gates-list-parse.md),
[kdd-contracts-status-summarize](./kdd-contracts-status-summarize.md) Y
[kdd-contracts-list-parse](./kdd-contracts-list-parse.md)), muestra el panel de
GATES navegable O la lista NAVEGABLE de contratos (el usuario alterna con
`g`/`c`). En AMBOS paneles: flechas arriba/abajo mueven un cursor, `Enter` abre
el detalle (en gates corre ESE gate individual via `gates run <name> --json` y
muestra su exit_code + stdout + stderr; en contracts muestra el `.md` completo
leido de disco), `Esc` vuelve a la lista. Recarga ambos paneles con `r`, y crea
contratos nuevos via un modo de scaffolding interactivo (`n` entra, `Enter`
confirma y dispara `contracts scaffold`, `Esc` cancela). La funcion que gobierna
este contrato es `UpdateModel(m Model, msg tea.Msg) (Model, tea.Cmd)`: PURA (sin
I/O, sin red, sin goroutines, sin llamar a Bubble Tea real mas alla de sus
TIPOS), separada del wiring de I/O real (el wrapper `tea.Model` en `program.go`,
glue, no testeado). `View(m Model) string` tambien es pura y esta cubierta por
el mismo oraculo congelado, pero NO es el target principal del gate de
complejidad. Esta actualizacion EXTIENDE el comportamiento previo (gates +
contracts navegable + detalle de contrato + refresh + scaffolding) con la lista
navegable de GATES + el detalle de gate; la `signature` de `UpdateModel` NO
cambio (sigue siendo `(m Model, msg tea.Msg) (Model, tea.Cmd)`).

## Interface
```go
type Model struct {
    // --- gates ---
    Summary  string  // el string de kdd.Summarize, vacio si no cargo aun (View ya NO lo renderiza)
    Err      error   // error de kdd.Summarize o del shell-out de gates, nil si ok
    Loading  bool    // true hasta que llega el primer resultado de gates
    // --- gates lista navegable ---
    GateItems          []kdd.GateResult  // lista estructurada que alimenta la lista navegable de gates (pobla gatesLoadedMsg)
    GatesSelectedIndex int               // cursor 0-based sobre GateItems (clampeado si la lista se achica); SEPARADO de SelectedIndex
    // --- contracts ---
    Contracts        string  // el string de kdd.SummarizeContractsStatus (se sigue poblando; View ya NO lo renderiza)
    ContractsErr     error   // error de contracts status o del shell-out, nil si ok
    ContractsLoading bool    // true hasta que llega contractsLoadedMsg
    ContractItems    []kdd.ContractStatus  // lista estructurada que alimenta la lista navegable (pobla contractsLoadedMsg)
    SelectedIndex    int     // cursor 0-based sobre ContractItems (clampeado si la lista se achica)
    // --- detalle (generico: contrato o gate) ---
    ViewingDetail  bool    // true mientras se muestra un detalle (tras Enter); Esc lo vuelve a false
    Detail         string  // contenido (.md de contrato o string de kdd.SummarizeGateDetail); "" si no cargo o se salio
    DetailErr      error   // error de loadDetail/loadGateDetail, nil si ok
    DetailLoading  bool    // true desde el Enter que abre el detalle hasta contractDetailMsg/gateDetailMsg
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
    items   []kdd.GateResult  // lista estructurada (kdd.ParseGatesResults sobre el mismo stdout que summary)
    err     error
}

type contractsLoadedMsg struct {
    summary string
    items   []kdd.ContractStatus
    err     error
}

type contractDetailMsg struct {
    content string
    err     error
}

type gateDetailMsg struct {
    content string  // string de kdd.SummarizeGateDetail (exit_code + stdout + stderr)
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
hacer). Es un DISPATCHER DELGADO: un type-switch corto delega TODO el trabajo
real a handlers separadas (mismo archivo `model.go`, helpers sin contrato propio,
mismo criterio que `handleScaffoldKey`). Comportamiento:
- `msg` es `gatesLoadedMsg`: delega a `handleGatesLoaded` -> setea `Summary`/`Err`,
  `Loading: false`, `GateItems: msg.items`, y CLAMPEA `GatesSelectedIndex` a
  `len(items)-1` (o `0` si la lista quedo vacia) si quedo fuera de rango tras la
  carga; resto sin cambios; cmd nil.
- `msg` es `contractsLoadedMsg`: delega a `handleContractsLoaded` -> setea
  `Contracts`/`ContractsErr`, `ContractsLoading: false`, `ContractItems:
  msg.items`, y CLAMPEA `SelectedIndex` a `len(items)-1` (o `0` si vacia) si
  quedo fuera de rango; resto sin cambios; cmd nil.
- `msg` es `contractDetailMsg`: delega a `handleContractDetail` -> setea
  `Detail`/`DetailErr`, `DetailLoading: false`; `ViewingDetail` YA era true
  (desde el Enter) y se PRESERVA; cmd nil.
- `msg` es `gateDetailMsg` (nuevo): delega a `handleGateDetail` -> setea
  `Detail`/`DetailErr`, `DetailLoading: false` (MISMOS campos genericos que
  `handleContractDetail`); `ViewingDetail` YA era true y se PRESERVA; cmd nil.
- `msg` es `scaffoldDoneMsg`: delega a `handleScaffoldDone` -> setea `ScaffoldMsg`
  a `"creado: " + msg.path` si `msg.err == nil`, o `"error: " + msg.err.Error()`
  si no; `ScaffoldInput` se conserva; cmd nil. (Historico, sin cambios.)
- `msg` es `tea.KeyMsg`: delega a `handleKey(m, msg)`, que despacha por modo:
  - `m.Scaffolding` true -> `handleScaffoldKey(m, msg)` (modo input, precedencia
    sobre TODO; "g"/"c"/"r"/"q" son texto, no comandos). (Historico, sin cambios.)
  - `m.ViewingDetail` true -> `handleDetailKey(m, msg)`: `tea.KeyEsc` vuelve a
    la lista (`ViewingDetail: false`, `Detail: ""`, `DetailErr: nil`,
    `SelectedIndex`/`GatesSelectedIndex` PRESERVADOS); CUALQUIER otra tecla
    (incluidas "q"/"g"/"c"/"r"/"n") NO hace nada — decision de UX explicita, evita
    que "q" salga del programa cuando el usuario solo quiere volver atras. El
    detalle es GENERICO: funciona igual venga de un contrato o de un gate (usa
    los mismos campos `Detail`/`DetailErr`/`DetailLoading`). cmd nil.
  - else (lista/normal) -> `handleListKey(m, msg)`:
    - si `ViewMode == "contracts"`: `tea.KeyUp` decrementa `SelectedIndex`
      clampeado a 0; `tea.KeyDown` incrementa clampeado a `len(ContractItems)-1`
      (lista vacia: sin cambio); `tea.KeyEnter` con `len(ContractItems) > 0` pone
      `ViewingDetail: true`, `DetailLoading: true`, `Detail: ""`, `DetailErr: nil`
      (Enter con lista vacia no hace nada). cmd nil.
    - si `ViewMode == "gates"` o `""` (zero-value == gates): `tea.KeyUp`/`KeyDown`
      mueven `GatesSelectedIndex` clampeado a `[0, len(GateItems)-1]` (lista vacia:
      sin cambio, nunca -1); `tea.KeyEnter` con `len(GateItems) > 0` pone
      `ViewingDetail: true`, `DetailLoading: true`, `Detail: ""`, `DetailErr: nil`
      (MISMOS campos genericos que el detalle de contrato; Enter con GateItems
      vacia no hace nada). cmd nil.
    - las teclas de comando funcionan en AMBAS vistas (gates y contracts) igual
      que antes: `"q"`/`"ctrl+c"` -> `Quitting: true` + `tea.Quit`; `"g"` ->
      `ViewMode: "gates"`; `"c"` -> `ViewMode: "contracts"`; `"r"` -> refresh
      (`Loading`/`ContractsLoading` true, `Err`/`ContractsErr` nil, resto sin
      cambios); `"n"` -> scaffolding (`Scaffolding` true, `ScaffoldInput`/
      `ScaffoldMsg` ""); cualquier otra tecla: sin cambios. cmd nil salvo
      "q"/"ctrl+c".
- Cualquier otro `msg`: devuelve `m` SIN CAMBIOS, cmd nil. Nunca panic (type
  switch con default, sin type assertion sin `, ok`).

`handleKey`/`handleGatesLoaded`/`handleContractsLoaded`/`handleContractDetail`/
`handleGateDetail`/`handleScaffoldDone`/`handleListKey`/`handleDetailKey`/
`handleScaffoldKey`/`renderContractList`/`renderGateList`/`viewDetail` son
helpers P UROS en el MISMO archivo `model.go`, NO targets del gate (el gate mide
solo `UpdateModel` via `signature`) y NO tienen contrato CCDD propio (mismo
criterio que un helper de la funcion contratada), pero SI tienen sus propios
casos de test en el oraculo congelado (`model_test.go`).

`View` renderiza la `Model` a un string. Precedencia (mayor a menor):
`Quitting` > `Scaffolding` > `ViewingDetail` > vista normal (gates/contracts
segun `ViewMode`):
- `m.Quitting` true: `""` (precedencia sobre todo).
- `m.Scaffolding` true: el prompt exacto
  `"nuevo contrato (kebab-case), enter confirma, esc cancela:\n> " +
  m.ScaffoldInput` (sin trailing newline, sin helpLine).
- `m.ViewingDetail` true: `viewDetail(m)` -> `DetailErr != nil` -> `"error: " +
  DetailErr.Error()`; `DetailLoading` -> `"cargando contrato...\n"`; si no, el
  contenido de `Detail` tal cual (el `.md` crudo o el string del gate, SIN
  modificar) + `"\n[esc] volver"`. Generico: funciona igual para contrato o gate.
  Sin helpLine normal.
- vista normal: `ViewMode == "contracts"` -> `ContractsErr != nil` -> `"error:
  " + ... + "\n"`; `ContractsLoading` -> `"cargando contratos...\n"`; si no,
  `renderContractList(m) + "\n"` (la lista desde `ContractItems` con cursor "> "
  en `SelectedIndex`, "  " en las demas, header "contracts=<N>"; NO el string
  plano `Contracts`). Cualquier otro `ViewMode` (incluido `""` == "gates") ->
  `Err != nil` -> `"error: ..."`; `Loading` -> `"cargando gates...\n"`; si no,
  `renderGateList(m) + "\n"` (la lista desde `GateItems` con cursor "> " en
  `GatesSelectedIndex`, "  " en las demas, header "overall_ok=<bool> pass=<N>
  fail=<M>" con overall_ok derivado de `fail==0`, y "[PASS] <name>"/"[FAIL]
  <name>" por fila segun `ExitCode`; NO el string plano `Summary`).
- Si `m.ScaffoldMsg != ""` (vista normal, no detalle): se agrega `"\n" +
  m.ScaffoldMsg` ANTES de la linea de ayuda. Si esta vacio, no se agrega nada.
- Al cuerpo de la vista normal se le agrega SIEMPRE al final la linea de ayuda
  EXACTA: `"\n[g]ates [c]ontracts [r]efresh [n]ew [q]uit"` (un `\n` + el literal).

## Invariants
- `UpdateModel` es PURA: sin I/O, sin red, sin goroutines, sin `os/exec`, sin
  `os.Exit`, nunca paniquea. Todos los handlers tambien son puros.
- `UpdateModel` es un DISPATCHER DELGADO: su unica logica es el type-switch que
  delega; la complejidad real vive en los handlers. (Ver Budget note.)
- Para `gatesLoadedMsg`, `Loading` queda SIEMPRE false, `Summary`/`Err` son los
  del msg, `GateItems` es `msg.items`, y `GatesSelectedIndex` NUNCA queda fuera
  de rango (0 si vacia, <= len-1 si no); `Quitting`/`ViewMode`/contracts se
  preservan.
- Para `contractsLoadedMsg`, `ContractsLoading` queda SIEMPRE false,
  `Contracts`/`ContractsErr` son los del msg, `ContractItems` es `msg.items`, y
  `SelectedIndex` NUNCA queda fuera de rango (0 si vacia, <= len-1 si no).
- Para `contractDetailMsg`/`gateDetailMsg`, `DetailLoading` queda SIEMPRE false,
  `Detail`/`DetailErr` son los del msg, `ViewingDetail` se preserva (true). Los
  dos mensajes usan los MISMOS campos genericos (`Detail`/`DetailErr`/
  `DetailLoading`); el detalle no distingue su origen.
- Para "q"/"ctrl+c", el `tea.Cmd` devuelto ES `tea.Quit`; para cualquier otra
  tecla o msg (incluida la navegacion, el Enter que abre detalle de contrato o
  gate, Esc, y "r"/"n" en modo normal), el cmd es nil. (El refresh, el scaffold,
  el loadDetail y el loadGateDetail reales los dispara el wiring en
  `program.Update`, no `UpdateModel`.)
- La navegacion (flechas/Enter) en contracts SOLO aplica cuando `ViewMode ==
  "contracts"` Y `!Scaffolding` Y `!ViewingDetail`; en gates SOLO aplica cuando
  `ViewMode == "gates"` o `""` Y `!Scaffolding` Y `!ViewingDetail`. Los dos
  cursores (`SelectedIndex` y `GatesSelectedIndex`) son INDEPENDIENTES: navegar
  un panel no mueve el cursor del otro (evita bugs de cursor cruzado al cambiar
  de panel con `g`/`c`).
- Durante `ViewingDetail`, SOLO `Esc` muta el estado (vuelve a la lista
  preservando `SelectedIndex`/`GatesSelectedIndex`); cualquier otra tecla
  (incluida "q") deja el model sin cambios y cmd nil. Generico: aplica igual si
  el detalle vino de un contrato o de un gate.
- `View` nunca devuelve un string con doble `\n` FINAL en la vista normal; al
  salir devuelve `""`; en scaffolding devuelve el prompt sin trailing newline;
  en detalle devuelve `viewDetail` (que tampoco termina en doble newline salvo el
  caso loading `"cargando contrato...\n"`).
- El zero-value de `ViewMode` (`""`) se comporta en `View` y en `handleListKey`
  IGUAL que `"gates"` (navegacion de gates + render de la lista de gates).
- 100% del comportamiento gobernable es reproducible desde el oraculo congelado
  (`model_test.go`) construyendo `Model`/`tea.Msg` a mano, sin shellear nada.

## Examples
- `UpdateModel(Model{Loading:true}, gatesLoadedMsg{summary:"overall_ok=true pass=1 fail=0", err:nil})` -> `Model{Summary:"overall_ok=true pass=1 fail=0", Loading:false}` con cmd nil.
- `UpdateModel(Model{Loading:true, GatesSelectedIndex:9}, gatesLoadedMsg{summary:"x", items:[]GateResult{{"a",0},{"b",1}}, err:nil})` -> `Model{GateItems:{{"a",0},{"b",1}}, GatesSelectedIndex:1}` (clamp a len-1), cmd nil.
- `UpdateModel(Model{Loading:true, GatesSelectedIndex:3}, gatesLoadedMsg{items:nil, err:nil})` -> `Model{GatesSelectedIndex:0}` (lista vacia -> 0).
- `UpdateModel(Model{ContractsLoading:true,ViewMode:"gates"}, contractsLoadedMsg{summary:"contracts=1\na: draft", items:[]ContractStatus{{"a","draft"}}, err:nil})` -> `Model{Contracts:"contracts=1\na: draft", ContractsLoading:false, ContractItems:{{"a","draft"}}, ViewMode:"gates"}` con cmd nil.
- `UpdateModel(Model{ContractsLoading:true, SelectedIndex:5}, contractsLoadedMsg{items:[]ContractStatus{{"a","draft"},{"b","verified"}}, err:nil})` -> `Model{ContractItems:{{"a","draft"},{"b","verified"}}, SelectedIndex:1}` (clamp a len-1).
- `UpdateModel(Model{ViewingDetail:true, DetailLoading:true}, contractDetailMsg{content:"---\nx", err:nil})` -> `Model{Detail:"---\nx", DetailLoading:false, ViewingDetail:true}` con cmd nil.
- `UpdateModel(Model{ViewingDetail:true, DetailLoading:true, GatesSelectedIndex:1}, gateDetailMsg{content:"exit_code=0\n--- stdout ---\nok\n--- stderr ---\n", err:nil})` -> `Model{Detail:"exit_code=0\n...", DetailLoading:false, ViewingDetail:true, GatesSelectedIndex:1}` con cmd nil.
- `UpdateModel(Model{ViewingDetail:true, DetailLoading:true}, gateDetailMsg{content:"", err:errors.New("unknown gate: foo")})` -> `Model{DetailErr:<unknown gate: foo>, DetailLoading:false, ViewingDetail:true}` con cmd nil.
- `UpdateModel(Model{ViewMode:"gates", GateItems:{{"a",0},{"b",0},{"c",1}}, GatesSelectedIndex:1}, tea.KeyMsg{Type: tea.KeyDown})` -> `Model{GatesSelectedIndex:2}` con cmd nil.
- `UpdateModel(Model{ViewMode:"gates", GateItems:{{"a",0},{"b",0}}, GatesSelectedIndex:1}, tea.KeyMsg{Type: tea.KeyDown})` -> `Model{GatesSelectedIndex:1}` (clamp al fondo).
- `UpdateModel(Model{ViewMode:"gates", GateItems:{{"a",0},{"b",0}}, GatesSelectedIndex:0}, tea.KeyMsg{Type: tea.KeyUp})` -> `Model{GatesSelectedIndex:0}` (clamp al tope).
- `UpdateModel(Model{ViewMode:"gates", GateItems:{{"a",0},{"b",1}}, GatesSelectedIndex:1}, tea.KeyMsg{Type: tea.KeyEnter})` -> `Model{ViewingDetail:true, DetailLoading:true, Detail:"", DetailErr:nil, GatesSelectedIndex:1}` con cmd nil.
- `UpdateModel(Model{ViewMode:"gates", GateItems:nil}, tea.KeyMsg{Type: tea.KeyEnter})` -> model sin cambios (lista vacia), cmd nil.
- `UpdateModel(Model{ViewMode:"contracts", ContractItems:{{"a","draft"},{"b","verified"},{"c","impl"}}, SelectedIndex:1}, tea.KeyMsg{Type: tea.KeyDown})` -> `Model{SelectedIndex:2}` con cmd nil.
- `UpdateModel(Model{ViewMode:"contracts", ContractItems:{{"a","draft"},{"b","verified"}}, SelectedIndex:1}, tea.KeyMsg{Type: tea.KeyEnter})` -> `Model{ViewingDetail:true, DetailLoading:true, Detail:"", DetailErr:nil, SelectedIndex:1}` con cmd nil.
- `UpdateModel(Model{ViewingDetail:true, GatesSelectedIndex:1, ViewMode:"gates"}, tea.KeyMsg{Type: tea.KeyEsc})` -> `Model{ViewingDetail:false, Detail:"", DetailErr:nil, GatesSelectedIndex:1, ViewMode:"gates"}` con cmd nil.
- `UpdateModel(Model{ViewingDetail:true}, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("q")})` -> model sin cambios (q ignorada durante detalle), cmd nil (NO tea.Quit).
- `UpdateModel(Model{}, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("q")})` -> `Model{Quitting:true}` con cmd = `tea.Quit`.
- `View(Model{Quitting:true, ViewingDetail:true})` -> `""`.
- `View(Model{ViewingDetail:true, DetailLoading:true})` -> `"cargando contrato...\n"`.
- `View(Model{ViewingDetail:true, Detail:"exit_code=0\n--- stdout ---\nok\n--- stderr ---\n"})` -> `"exit_code=0\n--- stdout ---\nok\n--- stderr ---\n\n[esc] volver"`.
- `View(Model{ViewMode:"gates", GateItems:{{"alpha",0},{"zeta",1}}, GatesSelectedIndex:0})` -> `"overall_ok=false pass=1 fail=1\n> [PASS] alpha\n  [FAIL] zeta\n\n[g]ates [c]ontracts [r]efresh [n]ew [q]uit"`.
- `View(Model{ViewMode:"gates", GateItems:nil})` -> `"overall_ok=true pass=0 fail=0\n\n[g]ates [c]ontracts [r]efresh [n]ew [q]uit"`.
- `View(Model{ViewMode:"contracts", ContractItems:{{"a","draft"},{"b","verified"}}, SelectedIndex:1})` -> `"contracts=2\n  a: draft\n> b: verified\n\n[g]ates [c]ontracts [r]efresh [n]ew [q]uit"`.
- `View(Model{Err:errors.New("boom"), Loading:true})` -> `"error: boom\n\n[g]ates [c]ontracts [r]efresh [n]ew [q]uit"`.
- `View(Model{ViewMode:"gates", GateItems:{{"a",0},{"b",0}}, ScaffoldMsg:"creado: knowledge/contracts/foo.md"})` -> `"overall_ok=true pass=2 fail=0\n> [PASS] a\n  [PASS] b\n\ncreado: knowledge/contracts/foo.md\n[g]ates [c]ontracts [r]efresh [n]ew [q]uit"`.

## Do / Don't
- DO: mantener `UpdateModel` como un DISPATCHER DELGADO — un type-switch sobre
  `msg` (`switch msg := msg.(type)`) con `case gatesLoadedMsg` /
  `contractsLoadedMsg` / `contractDetailMsg` / `gateDetailMsg` / `scaffoldDoneMsg`
  / `tea.KeyMsg` / `default`, donde cada case delega con una linea a un handler.
  La complejidad real vive en los handlers chicos, NO en `UpdateModel`. Nada de
  type assertion sin `, ok`.
- DO: `handleKey` despacha por modo (`if m.Scaffolding { ... }`; `if
  m.ViewingDetail { ... }`; `return handleListKey(...)`), cada modo a su propio
  handler.
- DO: `handleListKey` primero atiende la navegacion de contracts SOLO si
  `ViewMode == "contracts"`, DESPUES la navegacion de gates SOLO si `ViewMode ==
  "gates"` o `""` (cada uno un switch sobre `msg.Type`: `KeyUp`/`KeyDown`/
  `KeyEnter` con return temprano, clampeando el cursor respectivo a
  `[0, len-1]`), y DESPUES el switch de comandos sobre `msg.String()`
  (`"q","ctrl+c"`/`"g"`/`"c"`/`"r"`/`"n"`/`default`) que aplica en AMBAS vistas.
  Los dos cursores son campos SEPARADOS (`SelectedIndex`/`GatesSelectedIndex`).
- DO: `handleGatesLoaded` ADEMAS de setear `Summary`/`Err`/`Loading`, setea
  `GateItems: msg.items` y clampea `GatesSelectedIndex` (0 si vacia, len-1 si
  fuera de rango). Simetrico a `handleContractsLoaded`.
- DO: `handleGateDetail` setea los MISMOS campos genericos que
  `handleContractDetail` (`Detail`/`DetailErr`/`DetailLoading`); no crea campos
  separados `GateDetailLoading` etc. El detalle es generico.
- DO: `handleDetailKey` SOLO actua en `tea.KeyEsc` (vuelve a la lista
  preservando AMBOS cursores); cualquier otra tecla devuelve el model sin
  cambios. Generico (contrato o gate).
- DO: `renderContractList`/`renderGateList` arman la lista desde los items con
  cursor "> " / "  " y su header, uniendo con `\n` prefijado (sin trailing
  newline, View lo agrega). `renderGateList` deriva `overall_ok` como `fail==0`,
  cuenta pass/fail de `GateItems`, y marca cada fila `[PASS]`/`[FAIL]` segun
  `ExitCode`. Puras.
- DO: `viewDetail` con la precedencia `DetailErr` > `DetailLoading` > contenido
  + `"\n[esc] volver"`. Generico (contrato o gate). El contenido se muestra SIN
  modificar.
- DO: separar la logica pura (`model.go`) del wiring (`program.go`).
- DO: el wrapper `Init()` shellea AMBAS cargas en paralelo con `tea.Batch`.
  `loadGates` llama a `kdd.Summarize` (-> summary) Y `kdd.ParseGatesResults`
  (-> items) sobre el MISMO stdout; `loadContracts` llama a
  `kdd.SummarizeContractsStatus` (-> summary) Y `kdd.ParseContractsStatus`
  (-> items). Si una da error y la otra no, se propaga el no-nil. Un
  `*exec.ExitError` NO es error de shell-out.
- DO: nuevo metodo `func (p program) loadGateDetail(name string) tea.Cmd` en
  `program.go` que shellea `python scripts/kdd_cli.py gates run <name> --json`
  (mismo patron `os/exec` que `loadScaffold`), parsea el stdout con
  `kdd.SummarizeGateDetail` (funcion pura de [tui-gates-list-parse](./tui-gates-list-parse.md)),
  y devuelve `gateDetailMsg{content, err}`. Un `*exec.ExitError` NO es error de
  shell-out (se conserva stdout y se parsea igual).
- DO: el wrapper `Update(msg)` PRIMERO delega a `UpdateModel` (capturando ANTES
  del Model ENTRANTE `wasScaffolding`/`wasViewingDetail`/`input`/`inViewMode`/
  `inItems`/`inSelected`/`inGateItems`/`inGatesSelected`), y DESPUES detecta
  CUATRO casos: (1) Enter que confirma scaffolding -> `loadScaffold(input)`;
  (2) Enter que abre detalle de contrato (`inViewMode=="contracts"` &&
  `len(inItems)>0` -> `loadDetail(inItems[inSelected].Task)`); (3) Enter que
  corre un gate (`(inViewMode=="gates"||inViewMode=="")` && `len(inGateItems)>0`
  -> `loadGateDetail(inGateItems[inGatesSelected].Name)`); (4) "r" refresh ->
  `tea.Batch(loadGates, loadContracts)`. Los casos (2) y (3) son mutuamente
  excluyentes por `ViewMode`. Para cualquier otro msg, el cmd es el que devolvio
  `UpdateModel`. Es wiring (no testeado por el oraculo congelado).
- DON'T: incluir `subprocess`/`os.exec` en `forbids` — `UpdateModel`/`View`/los
  handlers son puros y no los usan; el wrapper y `main.go` si shellean/leen
  disco, pero son glue fuera del target y fuera del oraculo. `forbids` es
  `['network','llm']`.
- DON'T: agregar scroll/`bubbles/viewport` dentro del detalle (LIMITACION
  ACEPTADA: si el contenido es mas largo que la terminal, Bubble Tea truncaria o
  desbordaria — tarea futura), ni busqueda/filtro en la lista, ni colores/
  `lipgloss`, ni mas paneles alla de gates + contracts + detalle + scaffolding.
  Tampoco auto-refresco del detalle de gate ni indicador de "corriendo..." distinto
  al `DetailLoading` generico.
- DON'T: tocar `tui/internal/kdd/gates.go`, `gates_list.go`, `contracts.go`,
  `contracts_list.go`, sus `_test.go`, sus contratos, `tui/main.go`, `scripts/`,
  ni `.agents/`.
- DON'T: correr `tea.NewProgram(...).Run()` dentro de los tests (bloqueante). El
  oraculo congelado solo ejercita `UpdateModel`/`View`/los handlers como
  funciones puras; los pipes end-to-end viven en `pipe_test.go` como tests
  ADICIONALES opt-in (`LAZYKDD_RUN_PIPE=1`), fuera del oraculo sellado.

## Tests
(Los tests estan en `tui/internal/ui/model_test.go`, oraculo congelado sellado
por `tests_sha256`: el implementador no los escribe ni los modifica. Son 100%
Go puro (`testing` stdlib + tipos de `bubbletea` + `kdd.ContractStatus` +
`kdd.GateResult`), construyendo `Model` y `tea.Msg` a mano — sin I/O real, sin
shellear nada, sin `tea.NewProgram`. Preserva TODOS los casos viejos (gatesLoadedMsg,
contractsLoadedMsg exito/error, scaffoldDoneMsg exito/error, teclas
q/ctrl+c/g/c/r/n, otra tecla, WindowSizeMsg, unknown, modo scaffolding con
delegacion a handleScaffoldKey, handleScaffoldKey directo, View
quitting/scaffolding/error/loading/contracts-lista-con-cursor/ScaffoldMsg) y
AGREGA: gatesLoadedMsg con items (setea GateItems, clampea GatesSelectedIndex
alto, lista vacia/nil -> 0); gateDetailMsg exito (setea Detail, baja
DetailLoading, preserva ViewingDetail/GatesSelectedIndex) y error; navegacion de
gates (KeyDown incrementa, clamp al fondo, lista vacia sin cambio; KeyUp
decrementa, clamp al tope; flechas navegan con zero-value ViewMode; flechas en
gates view no mueven SelectedIndex de contracts y viceversa); Enter en gates
lista vacia no hace nada, Enter lista no vacia entra en ViewingDetail+DetailLoading
(limpia Detail/DetailErr, preserva GatesSelectedIndex); detalle de gate: Esc
vuelve a la lista preservando GatesSelectedIndex y ViewMode; teclas de comando
("r"/"n") funcionan desde gates view; View gates-lista-con-cursor (medio/tope/
fondo/vacia/single/zero-value-ViewMode, [PASS]/[FAIL] markers, ignora Summary),
View gates-lista con ScaffoldMsg (con y vacio). El literal de helpLine se
congela como `wantHelpLine = "\n[g]ates [c]ontracts [r]efresh [n]ew [q]uit"` y el
de detalle como `wantDetailHelpLine = "\n[esc] volver"` (declarados aparte de
los const del paquete). `test_command: "go test -C tui ./..."` corre desde la
RAIZ del repo (forzado por `test_cwd: ../..`). Exactamente el patron de
`tui-gates-summarize.md`/`kdd-contracts-list-parse.md`.)

El test ADICIONAL `tui/internal/ui/pipe_test.go` (NO sellado, NO en `tests:`)
ejercita los `tea.Cmd` reales de `Init()`/`loadScaffold()`/`loadDetail()`/
`loadGateDetail()` del wrapper llamandolos como funciones — eso SI shellea a
python de verdad (`loadGates`/`loadContracts`/`loadScaffold`/`loadGateDetail`)
o lee disco (`loadDetail`). Es OPT-IN: se saltea por defecto (`LAZYKDD_RUN_PIPE`
vacio) para que el `go test ./...` default sea 100% puro y para ROMPER la
recursion con `validate_test_commands` (el `go test -C tui ./...` de este
contrato, corrido por `gates run-all`, dispararia `loadGates` que shellea
`gates run-all` otra vez). `TestLoadGateDetail_RealGate` corre un gate REAL de
solo lectura (`lint_ascii`, rapido y sin side effects): shellea `gates run
lint_ascii --json`, verifica que el `gateDetailMsg` resultante tiene err == nil
y `content` contiene `"exit_code="`. `lint_ascii` NO dispara `validate_test_commands`
(no corre go test), asi que NO hay recursion; igual usa `maybeSkipPipe` (que
consume el flag antes de shellerar para romper la recursion en profundidad 1 y
hace chdir al repo root). Para correrlo de verdad:
`LAZYKDD_RUN_PIPE=1 go test -C tui -run TestLoadGateDetail_RealGate -v
./internal/ui/`. El test consume (`os.Unsetenv`) el flag antes de shellerar,
asi el `go test` anidado lo ve vacio y saltea — recursion rota en profundidad 1.

## Constraints
- PARAR y reportar si necesitas conectarte a la red o invocar un LLM.
- PARAR y reportar si el `intent` exige tocar un archivo fuera de
  `touch_only` (probablemente signifique que la spec esta mal escrita).
- PARAR y reportar si extender `UpdateModel`/handlers/`View`/`program.Update`
  sin romper ningun test viejo resulta imposible (los tests viejos se preservan
  intactos: "q"/"ctrl+c" siguen igual, "x"/WindowSizeMsg/unknown siguen sin
  cambios, contracts-lista/detalle de contrato siguen igual; solo `View` de
  gates cambia a renderizar la lista con cursor y se agrega el detalle de gate,
  y esos tests se actualizan con el nuevo esperado — re-sellados via
  `tests_sha256`).

## Budget note
Tras el refactor a dispatcher delgado, `UpdateModel` real mide `cyclomatic = 7`
(un type-switch con 6 cases + default, cada uno una linea de delegacion; cero
logica de rama extra — el case nuevo `gateDetailMsg` es una linea mas) y
`function_length` ~30 con comments internos (el doc comment del dispatcher + el
switch). El budget declarado (`cyclomatic_max: 8`, `lines_max: 40`) deja margen
chico sobre lo medido real y esta MUY por debajo de los topes globales firmados
(cyclomatic 20, lines 80) — ese es el punto del refactor: la complejidad real
(navegacion de dos paneles, detalle generico, clamping de dos cursores, modo
scaffolding) vive en los handlers chicos (`handleListKey`/`handleDetailKey`/
`handleGatesLoaded`/`handleGateDetail`/etc.), que el gate NO mide (no son el
target via `signature`), mismo criterio que `handleScaffoldKey`. `nesting_max: 3`
(medido 1) y `params_max: 2` (medido 2) sin cambios. `handleListKey` es el
handler mas complejo (~cyclomatic 12 por sus tres switches + clamps para dos
paneles), pero NO la mide el gate; sus tests propios lo cubren.