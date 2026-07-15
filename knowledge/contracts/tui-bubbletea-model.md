---
type: 'Task Contract'
title: 'TUI: Bubble Tea Model (capa interactiva, dos vistas + scaffolding + lista navegable con detalle)'
description: 'Capa interactiva de la Piel 3: un programa Bubble Tea (arquitectura Elm) que shellea al CLI Python, muestra el resumen de gates O la lista NAVEGABLE de contratos (flechas mueven cursor, Enter abre el .md completo, Esc vuelve), recarga con r, y crea contratos nuevos con un modo de scaffolding interactivo (tecla n). Logica pura UpdateModel/View (target, dispatcher delgado, testeable) separada del wrapper tea.Model (wiring, no testeado).'
tags: ['ccdd', 'tui', 'lazykdd', 'go']

task: tui-bubbletea-model
intent: "Gobernar la transicion de estado del TUI (gates + contracts navegable + detalle + refresh + scaffolding) con una funcion UpdateModel pura."
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
tests_sha256: "2539346a9102fd8a3afddfce00993ea91b208a33677e81565f4ede78ebeaa686"
touch_only: ['tui/internal/ui/model.go', 'tui/internal/ui/program.go', 'tui/internal/ui/pipe_test.go', 'tui/main.go', 'tui/go.mod', 'tui/go.sum']
deps_allowed: ['github.com/charmbracelet/bubbletea']
forbids: ['network', 'llm']
---

# Contract: TUI Bubble Tea `UpdateModel` (Piel 3, Go)

## Intent
Capa INTERACTIVA de la Piel 3 de lazykdd: un programa Bubble Tea
(`github.com/charmbracelet/bubbletea`, arquitectura Elm) en el paquete
`tui/internal/ui` que al arrancar shellea al CLI Python reusando la logica
existente ([tui-gates-summarize](./tui-gates-summarize.md),
[kdd-contracts-status-summarize](./kdd-contracts-status-summarize.md) Y la nueva
[kdd-contracts-list-parse](./kdd-contracts-list-parse.md)), muestra el resumen
de gates O la lista NAVEGABLE de contratos (el usuario alterna con `g`/`c`;
flechas arriba/abajo mueven un cursor, `Enter` sobre un contrato muestra su
contenido COMPLETO —el `.md` real leido de disco—, `Esc` vuelve a la lista),
recarga ambos paneles con `r`, y crea contratos nuevos via un modo de
scaffolding interactivo (`n` entra, `Enter` confirma y dispara `contracts
scaffold`, `Esc` cancela). La funcion que gobierna este contrato es
`UpdateModel(m Model, msg tea.Msg) (Model, tea.Cmd)`: PURA (sin I/O, sin red, sin
goroutines, sin llamar a Bubble Tea real mas alla de sus TIPOS), separada del
wiring de I/O real (el wrapper `tea.Model` en `program.go`, glue, no testeado).
`View(m Model) string` tambien es pura y esta cubierta por el mismo oraculo
congelado, pero NO es el target principal del gate de complejidad. Esta
actualizacion EXTIENDE el comportamiento previo (gates + contracts + refresh +
scaffolding) con la lista navegable + la vista de detalle; la `signature` de
`UpdateModel` NO cambio (sigue siendo `(m Model, msg tea.Msg) (Model, tea.Cmd)`).

## Interface
```go
type Model struct {
    // --- gates ---
    Summary  string  // el string de kdd.Summarize, vacio si no cargo aun
    Err      error   // error de kdd.Summarize o del shell-out de gates, nil si ok
    Loading  bool    // true hasta que llega el primer resultado de gates
    // --- contracts ---
    Contracts        string  // el string de kdd.SummarizeContractsStatus (se sigue poblando; View ya NO lo renderiza)
    ContractsErr     error   // error de contracts status o del shell-out, nil si ok
    ContractsLoading bool    // true hasta que llega contractsLoadedMsg
    ContractItems    []kdd.ContractStatus  // lista estructurada que alimenta la lista navegable (pobla contractsLoadedMsg)
    SelectedIndex    int     // cursor 0-based sobre ContractItems (clampeado si la lista se achica)
    // --- detalle de contrato ---
    ViewingDetail  bool    // true mientras se muestra el .md de un contrato (tras Enter); Esc lo vuelve a false
    Detail         string  // contenido del .md leido por loadDetail; "" si no cargo o se salio del detalle
    DetailErr      error   // error de loadDetail (ej. archivo inexistente), nil si ok
    DetailLoading  bool    // true desde el Enter que abre el detalle hasta contractDetailMsg
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
    items   []kdd.ContractStatus
    err     error
}

type contractDetailMsg struct {
    content string
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
  `Loading: false` (resto sin cambios), `tea.Cmd` nil. (Historico, sin cambios.)
- `msg` es `contractsLoadedMsg`: delega a `handleContractsLoaded` -> setea
  `Contracts`/`ContractsErr`, `ContractsLoading: false`, `ContractItems:
  msg.items`, y CLAMPEA `SelectedIndex` a `len(items)-1` (o `0` si la lista
  quedo vacia) si quedo fuera de rango tras la carga; resto sin cambios; cmd nil.
- `msg` es `contractDetailMsg` (nuevo): delega a `handleContractDetail` -> setea
  `Detail`/`DetailErr`, `DetailLoading: false`; `ViewingDetail` YA era true
  (desde el Enter) y se PRESERVA; cmd nil.
- `msg` es `scaffoldDoneMsg`: delega a `handleScaffoldDone` -> setea `ScaffoldMsg`
  a `"creado: " + msg.path` si `msg.err == nil`, o `"error: " + msg.err.Error()`
  si no; `ScaffoldInput` se conserva; cmd nil. (Historico, sin cambios.)
- `msg` es `tea.KeyMsg`: delega a `handleKey(m, msg)`, que despacha por modo:
  - `m.Scaffolding` true -> `handleScaffoldKey(m, msg)` (modo input, precedencia
    sobre TODO; "g"/"c"/"r"/"q" son texto, no comandos). (Historico, sin cambios.)
  - `m.ViewingDetail` true -> `handleDetailKey(m, msg)`: `tea.KeyEsc` vuelve a
    la lista (`ViewingDetail: false`, `Detail: ""`, `DetailErr: nil`,
    `SelectedIndex` PRESERVADO); CUALQUIER otra tecla (incluidas "q"/"g"/"c"/"r"/
    "n") NO hace nada — decision de UX explicita, evita que "q" salga del
    programa cuando el usuario solo quiere volver atras. cmd nil.
  - else (lista/normal) -> `handleListKey(m, msg)`:
    - si `ViewMode == "contracts"`: `tea.KeyUp` decrementa `SelectedIndex`
      clampeado a 0; `tea.KeyDown` incrementa clampeado a `len(ContractItems)-1`
      (lista vacia: sin cambio, nunca -1); `tea.KeyEnter` con
      `len(ContractItems) > 0` pone `ViewingDetail: true`, `DetailLoading: true`,
      `Detail: ""`, `DetailErr: nil` (Enter con lista vacia no hace nada). cmd nil.
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
`handleScaffoldDone`/`handleListKey`/`handleDetailKey`/`handleScaffoldKey`/
`renderContractList`/`viewDetail` son helpers P UROS en el MISMO archivo
`model.go`, NO targets del gate (el gate mide solo `UpdateModel` via
`signature`) y NO tienen contrato CCDD propio (mismo criterio que un helper de
la funcion contratada), pero SI tienen sus propios casos de test en el oraculo
congelado (`model_test.go`).

`View` renderiza la `Model` a un string. Precedencia (mayor a menor):
`Quitting` > `Scaffolding` > `ViewingDetail` > vista normal (gates/contracts
segun `ViewMode`):
- `m.Quitting` true: `""` (precedencia sobre todo).
- `m.Scaffolding` true: el prompt exacto
  `"nuevo contrato (kebab-case), enter confirma, esc cancela:\n> " +
  m.ScaffoldInput` (sin trailing newline, sin helpLine).
- `m.ViewingDetail` true: `viewDetail(m)` -> `DetailErr != nil` -> `"error: " +
  DetailErr.Error()`; `DetailLoading` -> `"cargando contrato...\n"`; si no, el
  contenido de `Detail` tal cual (el `.md` crudo, SIN modificar) +
  `"\n[esc] volver"`. Sin helpLine normal.
- vista normal: `ViewMode == "contracts"` -> `ContractsErr != nil` -> `"error:
  " + ... + "\n"`; `ContractsLoading` -> `"cargando contratos...\n"`; si no,
  `renderContractList(m) + "\n"` (la lista desde `ContractItems` con cursor ">
  " en `SelectedIndex`, "  " en las demas, header "contracts=<N>"; NO el string
  plano `Contracts`). Cualquier otro `ViewMode` (incluido `""` == "gates") ->
  `Err != nil` -> `"error: ..."`; `Loading` -> `"cargando gates...\n"`; si no,
  `Summary + "\n"`.
- Si `m.ScaffoldMsg != ""` (vista normal, no detalle): se agrega `"\n" +
  m.ScaffoldMsg` ANTES de la linea de ayuda. Si esta vacio, no se agrega nada.
- Al cuerpo de la vista normal se le agrega SIEMPRE al final la linea de ayuda
  EXACTA: `"\n[g]ates [c]ontracts [r]efresh [n]ew [q]uit"` (un `\n` + el literal;
  NO se agrega el hint de navegacion opcional — decision documentada en el
  REPORT: mantener helpLine byte-identico y .go ASCII-clean).

## Invariants
- `UpdateModel` es PURA: sin I/O, sin red, sin goroutines, sin `os/exec`, sin
  `os.Exit`, nunca paniquea. Todos los handlers tambien son puros.
- `UpdateModel` es un DISPATCHER DELGADO: su unica logica es el type-switch que
  delega; la complejidad real vive en los handlers. (Ver Budget note.)
- Para `gatesLoadedMsg`, `Loading` queda SIEMPRE false y `Summary`/`Err` son
  EXACTAMENTE los del msg; `Quitting`/`ViewMode`/contracts se preservan.
- Para `contractsLoadedMsg`, `ContractsLoading` queda SIEMPRE false,
  `Contracts`/`ContractsErr` son los del msg, `ContractItems` es `msg.items`, y
  `SelectedIndex` NUNCA queda fuera de rango (0 si vacia, <= len-1 si no).
- Para `contractDetailMsg`, `DetailLoading` queda SIEMPRE false, `Detail`/
  `DetailErr` son los del msg, `ViewingDetail` se preserva (true).
- Para `scaffoldDoneMsg`, `ScaffoldMsg` queda al formato exacto; `Scaffolding`
  false, `ScaffoldInput` conservado, cmd nil.
- Para "q"/"ctrl+c", el `tea.Cmd` devuelto ES `tea.Quit`; para cualquier otra
  tecla o msg (incluida la navegacion, el Enter que abre detalle, Esc, y "r"/"n"
  en modo normal), el cmd es nil. (El refresh, el scaffold y el loadDetail reales
  los dispara el wiring en `program.Update`, no `UpdateModel`.)
- La navegacion (flechas/Enter) SOLO aplica cuando `ViewMode == "contracts"` Y
  `!Scaffolding` Y `!ViewingDetail`. Fuera de ahi, flechas/Enter no hacen nada
  (gates view) o se ignoran (detalle: solo Esc).
- Durante `ViewingDetail`, SOLO `Esc` muta el estado (vuelve a la lista
  preservando `SelectedIndex`); cualquier otra tecla (incluida "q") deja el
  model sin cambios y cmd nil.
- `View` nunca devuelve un string con doble `\n` FINAL en la vista normal; al
  salir devuelve `""`; en scaffolding devuelve el prompt sin trailing newline;
  en detalle devuelve `viewDetail` (que tampoco termina en doble newline salvo el
  caso loading `"cargando contrato...\n"`).
- El zero-value de `ViewMode` (`""`) se comporta en `View` IGUAL que `"gates"`.
- 100% del comportamiento gobernable es reproducible desde el oraculo congelado
  (`model_test.go`) construyendo `Model`/`tea.Msg` a mano, sin shellear nada.

## Examples
- `UpdateModel(Model{Loading:true}, gatesLoadedMsg{summary:"overall_ok=true pass=1 fail=0", err:nil})` -> `Model{Summary:"overall_ok=true pass=1 fail=0", Loading:false}` con cmd nil.
- `UpdateModel(Model{ContractsLoading:true,ViewMode:"gates"}, contractsLoadedMsg{summary:"contracts=1\na: draft", items:[]ContractStatus{{"a","draft"}}, err:nil})` -> `Model{Contracts:"contracts=1\na: draft", ContractsLoading:false, ContractItems:{{"a","draft"}}, ViewMode:"gates"}` con cmd nil.
- `UpdateModel(Model{ContractsLoading:true, SelectedIndex:5}, contractsLoadedMsg{items:[]ContractStatus{{"a","draft"},{"b","verified"}}, err:nil})` -> `Model{ContractItems:{{"a","draft"},{"b","verified"}}, SelectedIndex:1}` (clamp a len-1).
- `UpdateModel(Model{ContractsLoading:true, SelectedIndex:3}, contractsLoadedMsg{items:nil, err:nil})` -> `Model{SelectedIndex:0}` (lista vacia -> 0).
- `UpdateModel(Model{ViewingDetail:true, DetailLoading:true}, contractDetailMsg{content:"---\nx", err:nil})` -> `Model{Detail:"---\nx", DetailLoading:false, ViewingDetail:true}` con cmd nil.
- `UpdateModel(Model{ViewingDetail:true, DetailLoading:true}, contractDetailMsg{content:"", err:errors.New("no such")})` -> `Model{DetailErr:<no such>, DetailLoading:false, ViewingDetail:true}` con cmd nil.
- `UpdateModel(Model{ViewMode:"contracts", ContractItems:{{"a","draft"},{"b","verified"},{"c","impl"}}, SelectedIndex:1}, tea.KeyMsg{Type: tea.KeyDown})` -> `Model{SelectedIndex:2}` con cmd nil.
- `UpdateModel(Model{ViewMode:"contracts", ContractItems:{{"a","draft"},{"b","verified"}}, SelectedIndex:1}, tea.KeyMsg{Type: tea.KeyDown})` -> `Model{SelectedIndex:1}` (clamp al fondo).
- `UpdateModel(Model{ViewMode:"contracts", ContractItems:{{"a","draft"},{"b","verified"}}, SelectedIndex:0}, tea.KeyMsg{Type: tea.KeyUp})` -> `Model{SelectedIndex:0}` (clamp al tope).
- `UpdateModel(Model{ViewMode:"contracts", ContractItems:{{"a","draft"},{"b","verified"}}, SelectedIndex:1}, tea.KeyMsg{Type: tea.KeyEnter})` -> `Model{ViewingDetail:true, DetailLoading:true, Detail:"", DetailErr:nil, SelectedIndex:1}` con cmd nil.
- `UpdateModel(Model{ViewMode:"contracts", ContractItems:nil}, tea.KeyMsg{Type: tea.KeyEnter})` -> model sin cambios (lista vacia), cmd nil.
- `UpdateModel(Model{ViewingDetail:true, SelectedIndex:1, ViewMode:"contracts"}, tea.KeyMsg{Type: tea.KeyEsc})` -> `Model{ViewingDetail:false, Detail:"", DetailErr:nil, SelectedIndex:1}` con cmd nil.
- `UpdateModel(Model{ViewingDetail:true}, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("q")})` -> model sin cambios (q ignorada durante detalle), cmd nil (NO tea.Quit).
- `UpdateModel(Model{}, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("q")})` -> `Model{Quitting:true}` con cmd = `tea.Quit`.
- `UpdateModel(Model{ViewMode:"gates"}, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("c")})` -> `Model{ViewMode:"contracts"}` con cmd nil.
- `UpdateModel(Model{Scaffolding:true, ScaffoldInput:"ab"}, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("cde")})` -> `Model{Scaffolding:true, ScaffoldInput:"abcde"}` con cmd nil.
- `View(Model{Quitting:true, ViewingDetail:true})` -> `""`.
- `View(Model{Scaffolding:true, ScaffoldInput:"x", ViewingDetail:true})` -> `"nuevo contrato (kebab-case), enter confirma, esc cancela:\n> x"`.
- `View(Model{ViewingDetail:true, DetailLoading:true})` -> `"cargando contrato...\n"`.
- `View(Model{ViewingDetail:true, DetailErr:errors.New("e")})` -> `"error: e"`.
- `View(Model{ViewingDetail:true, Detail:"---\nx"})` -> `"---\nx\n[esc] volver"`.
- `View(Model{ViewMode:"contracts", ContractItems:{{"a","draft"},{"b","verified"}}, SelectedIndex:1})` -> `"contracts=2\n  a: draft\n> b: verified\n\n[g]ates [c]ontracts [r]efresh [n]ew [q]uit"`.
- `View(Model{ViewMode:"contracts", ContractItems:nil})` -> `"contracts=0\n\n[g]ates [c]ontracts [r]efresh [n]ew [q]uit"`.
- `View(Model{Err:errors.New("boom"), Loading:true})` -> `"error: boom\n\n[g]ates [c]ontracts [r]efresh [n]ew [q]uit"`.
- `View(Model{Summary:"s", ScaffoldMsg:"creado: knowledge/contracts/foo.md"})` -> `"s\n\ncreado: knowledge/contracts/foo.md\n[g]ates [c]ontracts [r]efresh [n]ew [q]uit"`.

## Do / Don't
- DO: mantener `UpdateModel` como un DISPATCHER DELGADO — un type-switch sobre
  `msg` (`switch msg := msg.(type)`) con `case gatesLoadedMsg` /
  `contractsLoadedMsg` / `contractDetailMsg` / `scaffoldDoneMsg` / `tea.KeyMsg`
  / `default`, donde cada case delega con una linea a un handler
  (`handleGatesLoaded`/`handleContractsLoaded`/`handleContractDetail`/
  `handleScaffoldDone`/`handleKey`). La complejidad real vive en los handlers
  chicos, NO en `UpdateModel`. Nada de type assertion sin `, ok`.
- DO: `handleKey` despacha por modo (`if m.Scaffolding { return
  handleScaffoldKey(...) }`; `if m.ViewingDetail { return handleDetailKey(...)
  }`; `return handleListKey(...)`), cada modo a su propio handler.
- DO: `handleListKey` primero atiende la navegacion SOLO si `ViewMode ==
  "contracts"` (switch sobre `msg.Type`: `KeyUp`/`KeyDown`/`KeyEnter`, con
  return temprano) y DESPUES el switch de comandos sobre `msg.String()`
  (`"q","ctrl+c"`/`"g"`/`"c"`/`"r"`/`"n"`/`default`) que aplica en AMBAS vistas.
  Las teclas de comando (g/c/r/n/q) SIGUEN funcionando igual que antes en la
  lista de contracts (caen al switch de comandos al no matchear KeyUp/KeyDown/
  KeyEnter).
- DO: `handleDetailKey` SOLO actua en `tea.KeyEsc` (vuelve a la lista
  preservando `SelectedIndex`); cualquier otra tecla devuelve el model sin
  cambios. Decision de UX explicita: durante el detalle, "q"/"g"/"c"/"r"/"n" no
  hacen nada (evita salir/saltar mientras se lee un contrato).
- DO: `renderContractList` arma la lista desde `ContractItems` con cursor "> " /
  "  " y header "contracts=<N>", uniendo con `\n` prefijado (sin trailing
  newline, View lo agrega). Pura.
- DO: `viewDetail` con la precedencia `DetailErr` > `DetailLoading` > contenido
  + `"\n[esc]volver"`. El contenido se muestra SIN modificar (el `.md` crudo).
- DO: separar la logica pura (`model.go`) del wiring (`program.go`). Mismo
  criterio que `gates.go` (pura) vs `main.go` (glue).
- DO: el wrapper `Init()` shellea AMBAS cargas en paralelo con `tea.Batch`
  (`gates run-all --json` -> `gatesLoadedMsg` Y `contracts status --json` ->
  `contractsLoadedMsg`). `loadContracts` llama a `kdd.SummarizeContractsStatus`
  (-> summary) Y `kdd.ParseContractsStatus` (-> items) sobre el MISMO stdout: dos
  parses del mismo JSON, barato y mantiene cada funcion enfocada. Si una da
  error y la otra no (no deberia pasar), se propaga el no-nil (preferido
  summary). Un `*exec.ExitError` NO es error de shell-out.
- DO: nuevo metodo `func (p program) loadDetail(task string) tea.Cmd` en
  `program.go` que lee `knowledge/contracts/<task>.md` con `os.ReadFile` (path
  relativo, asume cwd = repo root) y devuelve `contractDetailMsg{content:
  string(b), err: err}`. NO es shell-out a python: es I/O local trivial, no hay
  logica de negocio que reimplementar (el CLI no expone "leer un .md"). Aceptable
  como glue, documentado.
- DO: el wrapper `Update(msg)` PRIMERO delega a `UpdateModel` (capturando ANTES
  `wasScaffolding`/`wasViewingDetail`/`input`/`inViewMode`/`inItems`/
  `inSelected` del Model ENTRANTE), y DESPUES detecta TRES casos: (1) Enter que
  confirma scaffolding (`key.Type==KeyEnter` && `wasScaffolding` && `input!=""`
  -> `loadScaffold(input)`); (2) Enter que abre detalle (`key.Type==KeyEnter` &&
  `!wasScaffolding` && `!wasViewingDetail` && `inViewMode=="contracts"` &&
  `len(inItems)>0` -> `loadDetail(inItems[inSelected].Task)`, usando el
  SelectedIndex ENTRANTE); (3) "r" refresh (`key.String()=="r"` &&
  `!wasScaffolding` -> `tea.Batch(loadGates, loadContracts)`). Para cualquier
  otro msg, el cmd es el que devolvio `UpdateModel`. Es wiring (no testeado por
  el oraculo congelado).
- DON'T: incluir `subprocess`/`os.exec` en `forbids` — `UpdateModel`/`View`/los
  handlers son puros y no los usan; el wrapper y `main.go` si shellean/leen
  disco (analogeo a `subprocess` de Python), pero son glue fuera del target y
  fuera del oraculo. `forbids` es `['network','llm']`.
- DON'T: agregar scroll/`bubbles/viewport` dentro del detalle (LIMITACION
  ACEPTADA: si el `.md` es mas largo que la terminal, Bubble Tea truncaria o
  desbordaria — tarea futura), ni busqueda/filtro en la lista, ni colores/
  `lipgloss`, ni mas paneles alla de gates + contracts + detalle + scaffolding.
- DON'T: tocar `tui/internal/kdd/gates.go`, `contracts.go`, sus `_test.go`, sus
  contratos, `tui/main.go`, `scripts/`, ni `.agents/`.
- DON'T: correr `tea.NewProgram(...).Run()` dentro de los tests (bloqueante). El
  oraculo congelado solo ejercita `UpdateModel`/`View`/los handlers como
  funciones puras; los pipes end-to-end viven en `pipe_test.go` como tests
  ADICIONALES opt-in (`LAZYKDD_RUN_PIPE=1`), fuera del oraculo sellado.

## Tests
(Los tests estan en `tui/internal/ui/model_test.go`, oraculo congelado sellado
por `tests_sha256`: el implementador no los escribe ni los modifica. Son 100%
Go puro (`testing` stdlib + tipos de `bubbletea` + `kdd.ContractStatus`),
construyendo `Model` y `tea.Msg` a mano — sin I/O real, sin shellear nada, sin
`tea.NewProgram`. Preserva TODOS los casos viejos (gatesLoadedMsg,
contractsLoadedMsg exito/error, scaffoldDoneMsg exito/error, teclas
q/ctrl+c/g/c/r/n, otra tecla, WindowSizeMsg, unknown, modo scaffolding con
delegacion a handleScaffoldKey, handleScaffoldKey directo, View
quitting/scaffolding/error/loading/normal/gates-ignora-contracts/ScaffoldMsg) y
AGREGA: contractsLoadedMsg con items (setea ContractItems, clampea SelectedIndex
alto, lista vacia/nil -> 0); contractDetailMsg exito (setea Detail, baja
DetailLoading, preserva ViewingDetail) y error; navegacion (KeyDown incrementa,
clamp al fondo, lista vacia sin cambio; KeyUp decrementa, clamp al tope;
flechas no navegan en gates view); Enter en contracts lista vacia no hace nada,
Enter lista no vacia entra en ViewingDetail+DetailLoading (limpia Detail/
DetailErr, preserva SelectedIndex), Enter en gates view no hace nada; detalle:
Esc vuelve a la lista preservando SelectedIndex, "q" ignorada durante detalle
(test explicito), g/c/r/n ignoradas durante detalle, flechas ignoradas durante
detalle; View detalle (loading/error/contenido+"[esc] volver"/empty/precedencia
sobre contracts), View detalle no muestra ScaffoldMsg, View quitting-gana-sobre-
detalle, scaffolding-gana-sobre-detalle, View lista con cursor (medio/tope/
fondo/vacia/un-elemento), View lista con ScaffoldMsg. El literal de helpLine se
congela como `wantHelpLine = "\n[g]ates [c]ontracts [r]efresh [n]ew [q]uit"` y el
de detalle como `wantDetailHelpLine = "\n[esc] volver"` (declarados aparte de
los const del paquete). `test_command: "go test -C tui ./..."` corre desde la
RAIZ del repo (forzado por `test_cwd: ../..`): el flag `-C tui` cambia a `tui/`
antes de correr, funcione desde el cwd que sea SIEMPRE Y CUANDO el cwd de
partida sea la raiz del repo. Asi el mismo `test_command` pasa para el gate CCDD
externo (`run_integration_gate`, que respeta `test_cwd`) Y para el Nivel 1
propio (`validate_test_commands`, que corre TODOS los `test_command` SIEMPRE con
cwd = raiz del repo, sin override). Exactamente el patron de
`tui-gates-summarize.md`/`kdd-contracts-status-summarize.md`.)

El test ADICIONAL `tui/internal/ui/pipe_test.go` (NO sellado, NO en `tests:`)
ejercita los `tea.Cmd` reales de `Init()`/`loadScaffold()`/`loadDetail()` del
wrapper llamandolos como funciones — eso SI shellea a python de verdad
(`loadGates`/`loadContracts`/`loadScaffold`) o lee disco (`loadDetail`). Es
OPT-IN: se saltea por defecto (`LAZYKDD_RUN_PIPE` vacio) para que el `go test
./...` default sea 100% puro y para ROMPER la recursion con
`validate_test_commands` (el `go test -C tui ./...` de este contrato, corrido por
`gates run-all`, dispararia `loadGates` que shellea `gates run-all` otra vez).
`TestLoadDetail_RealContract` lee un contrato REAL de solo lectura
(`kdd-gates-run-all-json`) — no crea ni borra nada, no shellea a python (es
`os.ReadFile`), asi que NO hay recursion con `validate_test_commands`; igual usa
`maybeSkipPipe` para el chdir al repo root y consistencia. Verifica content no
vacio y contiene `"---"` (frontmatter). Para correrlo de verdad:
`LAZYKDD_RUN_PIPE=1 go test -C tui -run 'TestInitPipeline|TestLoadDetail' -v
./internal/ui/`. El test consume (`os.Unsetenv`) el flag antes de shellerar/leer,
asi el `go test` anidado lo ve vacio y saltea — recursion rota en profundidad 1.

## Constraints
- PARAR y reportar si necesitas conectarte a la red o invocar un LLM.
- PARAR y reportar si el `intent` exige tocar un archivo fuera de
  `touch_only` (probablemente signifique que la spec esta mal escrita).
- PARAR y reportar si refactorizar `UpdateModel` a dispatcher delgado sin
  romper ninguno de los tests viejos resulta imposible (los tests viejos se
  preservan intactos: "q"/"ctrl+c" siguen igual, "x"/WindowSizeMsg/unknown
  siguen sin cambios; solo `View` de contracts cambia a renderizar la lista con
  cursor y se agrega la vista de detalle, y esos tests se actualizan con el
  nuevo esperado — re-sellados via `tests_sha256`).

## Budget note
Tras el refactor a dispatcher delgado, `UpdateModel` real mide `cyclomatic = 6`
(un type-switch con 5 cases + default, cada uno una linea de delegacion; cero
logica de rama extra) y `function_length` ~29 con comments internos (el doc
comment del dispatcher + el switch). El budget declarado (`cyclomatic_max: 8`,
`lines_max: 40`) deja margen chico sobre lo medido real y esta MUY por debajo de
los topes globales firmados (cyclomatic 20, lines 80) — ese es el punto del
refactor: la complejidad real (navegacion, detalle, clamping, modo
scaffolding) vive en los handlers chicos (`handleListKey`/`handleDetailKey`/
`handleContractsLoaded`/etc.), que el gate NO mide (no son el target via
`signature`), mismo criterio que `handleScaffoldKey`. `nesting_max: 3` (medido
1) y `params_max: 2` (medido 2) sin cambios. La bajada de `cyclomatic_max` de 14
a 8 y de `lines_max` de 70 a 40 refleja el refactor: `UpdateModel` paso de
contener toda la logica de teclas (12/66) a ser un dispatcher que solo delega
(6/29). `handleListKey` es el handler mas complejo (~cyclomatic 9 por sus dos
switches anidados + clamps), pero NO la mide el gate; sus tests propios lo
cubren.