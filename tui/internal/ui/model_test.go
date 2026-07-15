package ui

import (
	"errors"
	"strings"
	"testing"

	tea "github.com/charmbracelet/bubbletea"
)

// wantHelpLine es el literal EXACTO que View debe agregar al final (salvo
// quitting). Se declara aca (con otro nombre que el const del paquete) para
// que el oraculo sea independiente del target: si alguien cambia el literal en
// model.go, este test lo pega y falla, que es justo lo que debe hacer un
// oraculo congelado. El const del paquete (helpLine en model.go) NO se usa
// desde los tests; estos referencian solo a wantHelpLine.
const wantHelpLine = "\n[g]ates [c]ontracts [r]efresh [n]ew [q]uit"

// --- UpdateModel: gatesLoadedMsg (comportamiento historico, sin cambios) ---

// TestUpdateModel_GatesLoadedSuccess: un gatesLoadedMsg exitoso setea Summary,
// limpia Err, baja Loading y NO pide mas comandos. El resto del Model (ej.
// Quitting) se preserva sin cambios.
func TestUpdateModel_GatesLoadedSuccess(t *testing.T) {
	m := Model{Summary: "", Err: nil, Loading: true, Quitting: false}
	got, cmd := UpdateModel(m, gatesLoadedMsg{summary: "overall_ok=true pass=1 fail=0\n[PASS] g", err: nil})
	if cmd != nil {
		t.Errorf("expected nil cmd, got non-nil")
	}
	if got.Summary != "overall_ok=true pass=1 fail=0\n[PASS] g" {
		t.Errorf("Summary mismatch: %q", got.Summary)
	}
	if got.Err != nil {
		t.Errorf("Err should be nil, got %v", got.Err)
	}
	if got.Loading {
		t.Errorf("Loading should be false")
	}
	if got.Quitting {
		t.Errorf("Quitting should be unchanged (false)")
	}
}

// TestUpdateModel_GatesLoadedError: un gatesLoadedMsg con error propaga Err,
// baja Loading y devuelve cmd nil. Summary queda como vino en el msg.
func TestUpdateModel_GatesLoadedError(t *testing.T) {
	m := Model{Summary: "prev", Err: nil, Loading: true, Quitting: false}
	boom := errors.New("boom")
	got, cmd := UpdateModel(m, gatesLoadedMsg{summary: "", err: boom})
	if cmd != nil {
		t.Errorf("expected nil cmd, got non-nil")
	}
	if got.Err != boom {
		t.Errorf("Err mismatch: want %v, got %v", boom, got.Err)
	}
	if got.Loading {
		t.Errorf("Loading should be false")
	}
	if got.Summary != "" {
		t.Errorf("Summary should be empty, got %q", got.Summary)
	}
}

// --- UpdateModel: contractsLoadedMsg (comportamiento historico, sin cambios) ---

// TestUpdateModel_ContractsLoadedSuccess: un contractsLoadedMsg exitoso setea
// Contracts, limpia ContractsErr, baja ContractsLoading y NO pide comandos.
// Los campos de gates (Summary/Err/Loading) y Quitting se preservan sin cambios.
func TestUpdateModel_ContractsLoadedSuccess(t *testing.T) {
	m := Model{Summary: "g", Err: nil, Loading: false, Contracts: "", ContractsErr: nil, ContractsLoading: true, ViewMode: "gates", Quitting: false}
	got, cmd := UpdateModel(m, contractsLoadedMsg{summary: "contracts=2\na: draft\nb: verified", err: nil})
	if cmd != nil {
		t.Errorf("expected nil cmd, got non-nil")
	}
	if got.Contracts != "contracts=2\na: draft\nb: verified" {
		t.Errorf("Contracts mismatch: %q", got.Contracts)
	}
	if got.ContractsErr != nil {
		t.Errorf("ContractsErr should be nil, got %v", got.ContractsErr)
	}
	if got.ContractsLoading {
		t.Errorf("ContractsLoading should be false")
	}
	// gates y ViewMode/Quitting preservados.
	if got.Summary != "g" || got.Loading || got.Err != nil {
		t.Errorf("gates fields should be unchanged: %+v", got)
	}
	if got.ViewMode != "gates" {
		t.Errorf("ViewMode should be unchanged (gates), got %q", got.ViewMode)
	}
	if got.Quitting {
		t.Errorf("Quitting should be unchanged (false)")
	}
}

// TestUpdateModel_ContractsLoadedError: un contractsLoadedMsg con error propaga
// ContractsErr, baja ContractsLoading y devuelve cmd nil.
func TestUpdateModel_ContractsLoadedError(t *testing.T) {
	m := Model{Contracts: "prev", ContractsErr: nil, ContractsLoading: true}
	boom := errors.New("contracts boom")
	got, cmd := UpdateModel(m, contractsLoadedMsg{summary: "", err: boom})
	if cmd != nil {
		t.Errorf("expected nil cmd, got non-nil")
	}
	if got.ContractsErr != boom {
		t.Errorf("ContractsErr mismatch: want %v, got %v", boom, got.ContractsErr)
	}
	if got.ContractsLoading {
		t.Errorf("ContractsLoading should be false")
	}
	if got.Contracts != "" {
		t.Errorf("Contracts should be empty, got %q", got.Contracts)
	}
}

// --- UpdateModel: scaffoldDoneMsg (nuevo, resultado del shell-out de scaffold) ---

// TestUpdateModel_ScaffoldDoneSuccess: un scaffoldDoneMsg sin error setea
// ScaffoldMsg a "creado: <path>". Scaffolding ya era false (se apago al apretar
// Enter) y ScaffoldInput NO se limpia (se pisa la proxima vez que se entra en
// modo scaffolding con "n"). cmd nil.
func TestUpdateModel_ScaffoldDoneSuccess(t *testing.T) {
	m := Model{Scaffolding: false, ScaffoldInput: "my-task", ViewMode: "gates"}
	got, cmd := UpdateModel(m, scaffoldDoneMsg{path: "knowledge/contracts/my-task.md", err: nil})
	if cmd != nil {
		t.Errorf("expected nil cmd")
	}
	if got.ScaffoldMsg != "creado: knowledge/contracts/my-task.md" {
		t.Errorf("ScaffoldMsg mismatch: want %q, got %q", "creado: knowledge/contracts/my-task.md", got.ScaffoldMsg)
	}
	if got.Scaffolding {
		t.Errorf("Scaffolding should stay false")
	}
	if got.ScaffoldInput != "my-task" {
		t.Errorf("ScaffoldInput should be unchanged (conserved), got %q", got.ScaffoldInput)
	}
	if got.ViewMode != "gates" {
		t.Errorf("ViewMode should be unchanged, got %q", got.ViewMode)
	}
}

// TestUpdateModel_ScaffoldDoneError: un scaffoldDoneMsg con error setea
// ScaffoldMsg a "error: <err>". ScaffoldInput se conserva. cmd nil.
func TestUpdateModel_ScaffoldDoneError(t *testing.T) {
	m := Model{ScaffoldInput: "bad name"}
	got, cmd := UpdateModel(m, scaffoldDoneMsg{path: "", err: errors.New("invalid name")})
	if cmd != nil {
		t.Errorf("expected nil cmd")
	}
	if got.ScaffoldMsg != "error: invalid name" {
		t.Errorf("ScaffoldMsg mismatch: want %q, got %q", "error: invalid name", got.ScaffoldMsg)
	}
	if got.ScaffoldInput != "bad name" {
		t.Errorf("ScaffoldInput should be unchanged, got %q", got.ScaffoldInput)
	}
}

// --- UpdateModel: keys (quit + teclas de vista + refresh + nuevo "n") ---

// TestUpdateModel_KeyQ_Quits: la tecla "q" pone Quitting en true y devuelve
// tea.Quit como cmd (cmd() produce un tea.QuitMsg).
func TestUpdateModel_KeyQ_Quits(t *testing.T) {
	m := Model{Loading: false, Summary: "x"}
	got, cmd := UpdateModel(m, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("q")})
	if !got.Quitting {
		t.Errorf("Quitting should be true")
	}
	if cmd == nil {
		t.Fatalf("cmd should be non-nil (tea.Quit)")
	}
	if _, ok := cmd().(tea.QuitMsg); !ok {
		t.Errorf("cmd() should return tea.QuitMsg, got %T", cmd())
	}
}

// TestUpdateModel_KeyCtrlC_Quits: ctrl+c tambien sale (mismo camino que "q").
func TestUpdateModel_KeyCtrlC_Quits(t *testing.T) {
	m := Model{Loading: false}
	got, cmd := UpdateModel(m, tea.KeyMsg{Type: tea.KeyCtrlC})
	if !got.Quitting {
		t.Errorf("Quitting should be true")
	}
	if cmd == nil {
		t.Fatalf("cmd should be non-nil (tea.Quit)")
	}
	if _, ok := cmd().(tea.QuitMsg); !ok {
		t.Errorf("cmd() should return tea.QuitMsg, got %T", cmd())
	}
}

// TestUpdateModel_KeyG_SetsGates: la tecla "g" setea ViewMode="gates", no pide
// comandos y deja el resto del model sin cambios (incluido Quitting false).
func TestUpdateModel_KeyG_SetsGates(t *testing.T) {
	m := Model{Summary: "s", Loading: false, ViewMode: "contracts", Quitting: false}
	got, cmd := UpdateModel(m, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("g")})
	if cmd != nil {
		t.Errorf("expected nil cmd for g")
	}
	if got.ViewMode != "gates" {
		t.Errorf("ViewMode should be gates, got %q", got.ViewMode)
	}
	if got.Summary != "s" || got.Quitting {
		t.Errorf("rest of model should be unchanged: %+v", got)
	}
}

// TestUpdateModel_KeyC_SetsContracts: la tecla "c" setea ViewMode="contracts",
// no pide comandos y deja el resto del model sin cambios.
func TestUpdateModel_KeyC_SetsContracts(t *testing.T) {
	m := Model{Summary: "s", Loading: false, ViewMode: "gates", Quitting: false}
	got, cmd := UpdateModel(m, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("c")})
	if cmd != nil {
		t.Errorf("expected nil cmd for c")
	}
	if got.ViewMode != "contracts" {
		t.Errorf("ViewMode should be contracts, got %q", got.ViewMode)
	}
	if got.Summary != "s" || got.Quitting {
		t.Errorf("rest of model should be unchanged: %+v", got)
	}
}

// TestUpdateModel_KeyR_Refreshes: la tecla "r" vuelve AMBOS paneles a estado
// "cargando" (Loading y ContractsLoading en true), LIMPIA los errores viejos
// (Err y ContractsErr a nil incluso si tenian un error previo -- un refresco no
// debe seguir mostrando el error de la carga anterior mientras espera el nuevo),
// preserva Summary/Contracts/ViewMode/Quitting sin cambios y devuelve cmd nil.
// La funcion pura NO sabe shellear: el refresh real (el tea.Batch de
// loadGates/loadContracts) lo dispara el wiring en program.Update, no aca. Si
// Loading pasa a true, View ya muestra "cargando..." por la precedencia EXISTENTE
// (loading > resumen) -- UpdateModel no duplica esa logica.
func TestUpdateModel_KeyR_Refreshes(t *testing.T) {
	m := Model{
		Summary:          "old gates",
		Err:              errors.New("old gates err"),
		Loading:          false,
		Contracts:        "old contracts",
		ContractsErr:     errors.New("old contracts err"),
		ContractsLoading: false,
		ViewMode:         "contracts",
		Quitting:         false,
	}
	got, cmd := UpdateModel(m, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("r")})
	if cmd != nil {
		t.Errorf("expected nil cmd for r (pure UpdateModel does not shell out)")
	}
	if !got.Loading {
		t.Errorf("Loading should be true after refresh")
	}
	if !got.ContractsLoading {
		t.Errorf("ContractsLoading should be true after refresh")
	}
	if got.Err != nil {
		t.Errorf("Err should be cleared to nil after refresh, got %v", got.Err)
	}
	if got.ContractsErr != nil {
		t.Errorf("ContractsErr should be cleared to nil after refresh, got %v", got.ContractsErr)
	}
	if got.Summary != "old gates" {
		t.Errorf("Summary should be unchanged after refresh, got %q", got.Summary)
	}
	if got.Contracts != "old contracts" {
		t.Errorf("Contracts should be unchanged after refresh, got %q", got.Contracts)
	}
	if got.ViewMode != "contracts" {
		t.Errorf("ViewMode should be unchanged (contracts) after refresh, got %q", got.ViewMode)
	}
	if got.Quitting {
		t.Errorf("Quitting should be unchanged (false) after refresh")
	}
}

// TestUpdateModel_KeyR_RefreshesFromCleanState: un refresco desde un estado
// limpio (sin errores, ambos paneles cargados) igual vuelve a "cargando" y
// preserva los resumenes visibles hasta que lleguen los nuevos.
func TestUpdateModel_KeyR_RefreshesFromCleanState(t *testing.T) {
	m := Model{
		Summary:          "overall_ok=true pass=2 fail=0",
		Err:              nil,
		Loading:          false,
		Contracts:        "contracts=2",
		ContractsErr:     nil,
		ContractsLoading: false,
		ViewMode:         "gates",
		Quitting:         false,
	}
	got, cmd := UpdateModel(m, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("r")})
	if cmd != nil {
		t.Errorf("expected nil cmd for r")
	}
	if !got.Loading || !got.ContractsLoading {
		t.Errorf("both Loading flags should be true after refresh: %+v", got)
	}
	if got.Err != nil || got.ContractsErr != nil {
		t.Errorf("no errors to clear, but got gates=%v contracts=%v", got.Err, got.ContractsErr)
	}
	if got.Summary != "overall_ok=true pass=2 fail=0" {
		t.Errorf("Summary should be preserved, got %q", got.Summary)
	}
	if got.Contracts != "contracts=2" {
		t.Errorf("Contracts should be preserved, got %q", got.Contracts)
	}
	if got.ViewMode != "gates" || got.Quitting {
		t.Errorf("ViewMode/Quitting should be unchanged: %+v", got)
	}
}

// TestUpdateModel_KeyN_EntersScaffolding: la tecla "n" (modo normal) entra en
// modo scaffolding: Scaffolding true, ScaffoldInput "", ScaffoldMsg "" (limpia
// el resultado del intento anterior). El resto del model (Summary/ViewMode/
// Quitting) se preserva sin cambios. cmd nil.
func TestUpdateModel_KeyN_EntersScaffolding(t *testing.T) {
	m := Model{Summary: "s", ViewMode: "contracts", ScaffoldMsg: "prev intento", Quitting: false}
	got, cmd := UpdateModel(m, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("n")})
	if cmd != nil {
		t.Errorf("expected nil cmd for n")
	}
	if !got.Scaffolding {
		t.Errorf("Scaffolding should be true")
	}
	if got.ScaffoldInput != "" {
		t.Errorf("ScaffoldInput should be empty, got %q", got.ScaffoldInput)
	}
	if got.ScaffoldMsg != "" {
		t.Errorf("ScaffoldMsg should be cleared, got %q", got.ScaffoldMsg)
	}
	if got.Summary != "s" || got.ViewMode != "contracts" || got.Quitting {
		t.Errorf("rest of model should be unchanged: %+v", got)
	}
}

// TestUpdateModel_OtherKey_NoChange: una tecla que no es "q"/"ctrl+c"/"g"/"c"/"r"/"n"
// no cambia el model ni pide comandos (incluido ViewMode).
func TestUpdateModel_OtherKey_NoChange(t *testing.T) {
	m := Model{Summary: "s", Err: nil, Loading: true, Quitting: false, ViewMode: "contracts"}
	got, cmd := UpdateModel(m, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("x")})
	if cmd != nil {
		t.Errorf("expected nil cmd for other key")
	}
	if got.Summary != m.Summary || got.Loading != m.Loading || got.Quitting != m.Quitting || got.Err != m.Err {
		t.Errorf("model should be unchanged: want %+v, got %+v", m, got)
	}
	if got.ViewMode != "contracts" {
		t.Errorf("ViewMode should be unchanged (contracts), got %q", got.ViewMode)
	}
}

// TestUpdateModel_WindowSizeMsg_NoChange: un tea.WindowSizeMsg cae al default
// del switch: model sin cambios, cmd nil.
func TestUpdateModel_WindowSizeMsg_NoChange(t *testing.T) {
	m := Model{Summary: "s", Err: nil, Loading: true, Quitting: false}
	got, cmd := UpdateModel(m, tea.WindowSizeMsg{Width: 80, Height: 24})
	if cmd != nil {
		t.Errorf("expected nil cmd for WindowSizeMsg")
	}
	if got.Summary != m.Summary || got.Loading != m.Loading || got.Quitting != m.Quitting || got.Err != m.Err {
		t.Errorf("model should be unchanged: want %+v, got %+v", m, got)
	}
}

// unknownMsg es un tea.Msg no reconocido por UpdateModel (cae al default).
type unknownMsg struct{}

// TestUpdateModel_UnknownMsg_NoChange: cualquier otro msg cae al default y no
// muta el model ni pide comandos (nunca panic: type switch con default, sin
// type assertion sin ,ok).
func TestUpdateModel_UnknownMsg_NoChange(t *testing.T) {
	m := Model{Summary: "s", Err: nil, Loading: true, Quitting: false}
	got, cmd := UpdateModel(m, unknownMsg{})
	if cmd != nil {
		t.Errorf("expected nil cmd for unknown msg")
	}
	if got.Summary != m.Summary || got.Loading != m.Loading || got.Quitting != m.Quitting || got.Err != m.Err {
		t.Errorf("model should be unchanged: want %+v, got %+v", m, got)
	}
}

// --- UpdateModel: modo scaffolding (delegacion a handleScaffoldKey) ---
//
// En modo scaffolding (m.Scaffolding true) TODA tea.KeyMsg se delega a
// handleScaffoldKey ANTES del switch de comandos normal: "g"/"c"/"r"/"q" son
// texto a tipear, NO comandos. UpdateModel solo anade la guarda `if m.Scaffolding`
// dentro del case tea.KeyMsg (una linea de delegacion, bajo costo) y delega.

// TestUpdateModel_Scaffolding_TypeRunes_Appends: tipear caracteres normales en
// modo scaffolding appendea a ScaffoldInput. Scaffolding sigue true. cmd nil.
func TestUpdateModel_Scaffolding_TypeRunes_Appends(t *testing.T) {
	m := Model{Scaffolding: true, ScaffoldInput: "ab"}
	got, cmd := UpdateModel(m, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("cde")})
	if cmd != nil {
		t.Errorf("expected nil cmd")
	}
	if !got.Scaffolding {
		t.Errorf("Scaffolding should stay true")
	}
	if got.ScaffoldInput != "abcde" {
		t.Errorf("ScaffoldInput mismatch: want %q, got %q", "abcde", got.ScaffoldInput)
	}
}

// TestUpdateModel_Scaffolding_Backspace_RemovesLastRune: backspace saca el
// ULTIMO RUNE (no byte). Scaffolding sigue true. cmd nil.
func TestUpdateModel_Scaffolding_Backspace_RemovesLastRune(t *testing.T) {
	m := Model{Scaffolding: true, ScaffoldInput: "abc"}
	got, cmd := UpdateModel(m, tea.KeyMsg{Type: tea.KeyBackspace})
	if cmd != nil {
		t.Errorf("expected nil cmd")
	}
	if !got.Scaffolding {
		t.Errorf("Scaffolding should stay true")
	}
	if got.ScaffoldInput != "ab" {
		t.Errorf("ScaffoldInput mismatch: want %q, got %q", "ab", got.ScaffoldInput)
	}
}

// TestUpdateModel_Scaffolding_Backslice_Empty_NoChange: backspace con el buffer
// vacio no hace nada (sin panic, sin cambiar Scaffolding). cmd nil.
func TestUpdateModel_Scaffolding_Backslice_Empty_NoChange(t *testing.T) {
	m := Model{Scaffolding: true, ScaffoldInput: ""}
	got, cmd := UpdateModel(m, tea.KeyMsg{Type: tea.KeyBackspace})
	if cmd != nil {
		t.Errorf("expected nil cmd")
	}
	if !got.Scaffolding {
		t.Errorf("Scaffolding should stay true")
	}
	if got.ScaffoldInput != "" {
		t.Errorf("ScaffoldInput should stay empty, got %q", got.ScaffoldInput)
	}
}

// TestUpdateModel_Scaffolding_Esc_Cancels_PreservesScaffoldMsg: esc cancela el
// modo input (Scaffolding false, ScaffoldInput "") pero NO toca ScaffoldMsg
// (el resultado del intento anterior se conserva al cancelar). cmd nil.
func TestUpdateModel_Scaffolding_Esc_Cancels_PreservesScaffoldMsg(t *testing.T) {
	m := Model{Scaffolding: true, ScaffoldInput: "typed", ScaffoldMsg: "prev"}
	got, cmd := UpdateModel(m, tea.KeyMsg{Type: tea.KeyEsc})
	if cmd != nil {
		t.Errorf("expected nil cmd")
	}
	if got.Scaffolding {
		t.Errorf("Scaffolding should be false")
	}
	if got.ScaffoldInput != "" {
		t.Errorf("ScaffoldInput should be cleared, got %q", got.ScaffoldInput)
	}
	if got.ScaffoldMsg != "prev" {
		t.Errorf("ScaffoldMsg should be preserved on cancel, got %q", got.ScaffoldMsg)
	}
}

// TestUpdateModel_Scaffolding_Enter_NonEmpty_ConserveInput: enter con buffer no
// vacio sale del modo input (Scaffolding false) PERO CONSERVA ScaffoldInput en
// el Model que devuelve UpdateModel (el wiring en program.Update lo lee para
// saber que nombre scaffoldear). cmd nil (la funcion pura no shellea).
func TestUpdateModel_Scaffolding_Enter_NonEmpty_ConserveInput(t *testing.T) {
	m := Model{Scaffolding: true, ScaffoldInput: "my-task", ScaffoldMsg: "prev"}
	got, cmd := UpdateModel(m, tea.KeyMsg{Type: tea.KeyEnter})
	if cmd != nil {
		t.Errorf("expected nil cmd (pure UpdateModel does not shell out)")
	}
	if got.Scaffolding {
		t.Errorf("Scaffolding should be false after enter")
	}
	if got.ScaffoldInput != "my-task" {
		t.Errorf("ScaffoldInput should be conserved, got %q", got.ScaffoldInput)
	}
	if got.ScaffoldMsg != "prev" {
		t.Errorf("ScaffoldMsg should be unchanged, got %q", got.ScaffoldMsg)
	}
}

// TestUpdateModel_Scaffolding_Enter_Empty_NoCrash: enter con buffer VACIO
// tambien sale del modo input (Scaffolding false) sin crashear. cmd nil. El
// wiring NO dispara scaffold para un Enter con buffer vacio (ahorra shell-out
// inutil); el modo input igual se cierra.
func TestUpdateModel_Scaffolding_Enter_Empty_NoCrash(t *testing.T) {
	m := Model{Scaffolding: true, ScaffoldInput: ""}
	got, cmd := UpdateModel(m, tea.KeyMsg{Type: tea.KeyEnter})
	if cmd != nil {
		t.Errorf("expected nil cmd")
	}
	if got.Scaffolding {
		t.Errorf("Scaffolding should be false after enter")
	}
	if got.ScaffoldInput != "" {
		t.Errorf("ScaffoldInput should be empty, got %q", got.ScaffoldInput)
	}
}

// TestUpdateModel_Scaffolding_OtherKey_NoChange: una tecla no reconocida en
// modo input (flecha arriba) no cambia nada. Scaffolding sigue true, input y
// ViewMode intactos. cmd nil.
func TestUpdateModel_Scaffolding_OtherKey_NoChange(t *testing.T) {
	m := Model{Scaffolding: true, ScaffoldInput: "ab", ViewMode: "gates"}
	got, cmd := UpdateModel(m, tea.KeyMsg{Type: tea.KeyUp})
	if cmd != nil {
		t.Errorf("expected nil cmd")
	}
	if !got.Scaffolding {
		t.Errorf("Scaffolding should stay true")
	}
	if got.ScaffoldInput != "ab" {
		t.Errorf("ScaffoldInput should be unchanged, got %q", got.ScaffoldInput)
	}
	if got.ViewMode != "gates" {
		t.Errorf("ViewMode should be unchanged, got %q", got.ViewMode)
	}
}

// TestUpdateModel_Scaffolding_CommandKeysAreText: test EXPLICITO de que "g"/"c"/
// "r"/"q" mientras Scaffolding es true se tratan como TEXTO TIPEADO, NO como
// comandos: se appendean a ScaffoldInput, NO cambian ViewMode, NO ponen
// Quitting en true (la "q" no sale) y el cmd es nil (no tea.Quit). Es la
// precedencia del modo input sobre TODO lo demas.
func TestUpdateModel_Scaffolding_CommandKeysAreText(t *testing.T) {
	for _, ch := range []string{"g", "c", "r", "q"} {
		m := Model{Scaffolding: true, ScaffoldInput: "x", ViewMode: "contracts", Quitting: false}
		got, cmd := UpdateModel(m, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune(ch)})
		if cmd != nil {
			t.Errorf("key %q: expected nil cmd (text, not command)", ch)
		}
		if !got.Scaffolding {
			t.Errorf("key %q: Scaffolding should stay true", ch)
		}
		want := "x" + ch
		if got.ScaffoldInput != want {
			t.Errorf("key %q: ScaffoldInput should be %q, got %q", ch, want, got.ScaffoldInput)
		}
		if got.ViewMode != "contracts" {
			t.Errorf("key %q: ViewMode should be unchanged (contracts), got %q", ch, got.ViewMode)
		}
		if got.Quitting {
			t.Errorf("key %q: Quitting should stay false (q is text in scaffolding mode)", ch)
		}
	}
}

// --- handleScaffoldKey (helper extraido del target, target secundario) ---
//
// handleScaffoldKey fue extraida de UpdateModel por presupuesto de complejidad
// (UpdateModel estaba en cyclomatic 8/9). No es el target del gate (el gate
// sigue midiendo solo UpdateModel via signature), pero SI tiene sus propios
// casos de test en este oraculo congelado.

// TestHandleScaffoldKey_Runes_Appends: KeyRunes appendea string(key.Runes).
func TestHandleScaffoldKey_Runes_Appends(t *testing.T) {
	m := Model{Scaffolding: true, ScaffoldInput: "ab"}
	got, cmd := handleScaffoldKey(m, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("c")})
	if cmd != nil {
		t.Errorf("expected nil cmd")
	}
	if got.ScaffoldInput != "abc" {
		t.Errorf("ScaffoldInput mismatch: want %q, got %q", "abc", got.ScaffoldInput)
	}
	if !got.Scaffolding {
		t.Errorf("Scaffolding should stay true")
	}
}

// TestHandleScaffoldKey_Backspace_RemovesLastRune: backspace saca el ultimo rune.
func TestHandleScaffoldKey_Backspace_RemovesLastRune(t *testing.T) {
	m := Model{Scaffolding: true, ScaffoldInput: "abc"}
	got, _ := handleScaffoldKey(m, tea.KeyMsg{Type: tea.KeyBackspace})
	if got.ScaffoldInput != "ab" {
		t.Errorf("ScaffoldInput mismatch: want %q, got %q", "ab", got.ScaffoldInput)
	}
	if !got.Scaffolding {
		t.Errorf("Scaffolding should stay true")
	}
}

// TestHandleScaffoldKey_Backspace_UTF8: backspace saca el ULTIMO RUNE, no el
// ultimo byte (seguro con UTF-8: 'é' son 2 bytes, sacarlo deja "a", no un rune
// truncado).
func TestHandleScaffoldKey_Backspace_UTF8(t *testing.T) {
	m := Model{Scaffolding: true, ScaffoldInput: "aé"} // 'é' = 2 bytes, 1 rune
	got, _ := handleScaffoldKey(m, tea.KeyMsg{Type: tea.KeyBackspace})
	if got.ScaffoldInput != "a" {
		t.Errorf("expected %q (last rune removed), got %q", "a", got.ScaffoldInput)
	}
}

// TestHandleScaffoldKey_Esc_Clears: esc pone Scaffolding false y ScaffoldInput
// "", pero NO toca ScaffoldMsg (se conserva al cancelar).
func TestHandleScaffoldKey_Esc_Clears(t *testing.T) {
	m := Model{Scaffolding: true, ScaffoldInput: "x", ScaffoldMsg: "keep"}
	got, cmd := handleScaffoldKey(m, tea.KeyMsg{Type: tea.KeyEsc})
	if cmd != nil {
		t.Errorf("expected nil cmd")
	}
	if got.Scaffolding {
		t.Errorf("Scaffolding should be false")
	}
	if got.ScaffoldInput != "" {
		t.Errorf("ScaffoldInput should be cleared, got %q", got.ScaffoldInput)
	}
	if got.ScaffoldMsg != "keep" {
		t.Errorf("ScaffoldMsg should be preserved, got %q", got.ScaffoldMsg)
	}
}

// TestHandleScaffoldKey_Enter_ConserveInput: enter pone Scaffolding false y
// CONSERVA ScaffoldInput (el wiring lo lee para scaffoldear).
func TestHandleScaffoldKey_Enter_ConserveInput(t *testing.T) {
	m := Model{Scaffolding: true, ScaffoldInput: "task"}
	got, cmd := handleScaffoldKey(m, tea.KeyMsg{Type: tea.KeyEnter})
	if cmd != nil {
		t.Errorf("expected nil cmd")
	}
	if got.Scaffolding {
		t.Errorf("Scaffolding should be false")
	}
	if got.ScaffoldInput != "task" {
		t.Errorf("ScaffoldInput should be conserved, got %q", got.ScaffoldInput)
	}
}

// TestHandleScaffoldKey_Other_NoChange: una tecla no reconocida (flecha abajo)
// no cambia nada. Scaffolding sigue true, input intacto. cmd nil.
func TestHandleScaffoldKey_Other_NoChange(t *testing.T) {
	m := Model{Scaffolding: true, ScaffoldInput: "ab"}
	got, cmd := handleScaffoldKey(m, tea.KeyMsg{Type: tea.KeyDown})
	if cmd != nil {
		t.Errorf("expected nil cmd")
	}
	if got.ScaffoldInput != "ab" {
		t.Errorf("ScaffoldInput should be unchanged, got %q", got.ScaffoldInput)
	}
	if !got.Scaffolding {
		t.Errorf("Scaffolding should stay true")
	}
}

// --- View ---

// TestView_Quitting: devuelve string vacio (Bubble Tea limpia la pantalla al
// salir; no queremos residuo). Tiene precedencia sobre todo, incluida la linea
// de ayuda (no se agrega al salir) y el modo scaffolding.
func TestView_Quitting(t *testing.T) {
	got := View(Model{Quitting: true, Summary: "whatever", Err: errors.New("e"), Loading: true})
	if got != "" {
		t.Errorf("expected empty string when quitting, got %q", got)
	}
}

// TestView_QuittingPrecedenceOverContracts: quitting gana incluso si la vista
// activa es contracts con error de carga.
func TestView_QuittingPrecedenceOverContracts(t *testing.T) {
	got := View(Model{Quitting: true, ViewMode: "contracts", ContractsErr: errors.New("e"), ContractsLoading: true})
	if got != "" {
		t.Errorf("expected empty string when quitting, got %q", got)
	}
}

// TestView_QuittingPrecedenceOverScaffolding: quitting gana sobre el modo
// scaffolding (no se muestra el prompt de input al salir).
func TestView_QuittingPrecedenceOverScaffolding(t *testing.T) {
	got := View(Model{Quitting: true, Scaffolding: true, ScaffoldInput: "x"})
	if got != "" {
		t.Errorf("expected empty string when quitting, got %q", got)
	}
}

// TestView_Scaffolding_Prompt: en modo scaffolding View devuelve una vista
// DISTINTA que reemplaza TODO lo demas (sin helpLine): el prompt exacto + el
// input tipeado. Sin trailing newline (decision documentada: consistente con
// kdd.Summarize/SummarizeContractsStatus que tampoco lo llevan).
func TestView_Scaffolding_Prompt(t *testing.T) {
	got := View(Model{Scaffolding: true, ScaffoldInput: "my-task", Summary: "x", ViewMode: "contracts"})
	want := "nuevo contrato (kebab-case), enter confirma, esc cancela:\n> my-task"
	if got != want {
		t.Errorf("View scaffolding mismatch: want %q, got %q", want, got)
	}
}

// TestView_Scaffolding_EmptyInput: el prompt con buffer vacio termina en "> "
// (sin trailing newline).
func TestView_Scaffolding_EmptyInput(t *testing.T) {
	got := View(Model{Scaffolding: true, ScaffoldInput: ""})
	want := "nuevo contrato (kebab-case), enter confirma, esc cancela:\n> "
	if got != want {
		t.Errorf("View scaffolding empty mismatch: want %q, got %q", want, got)
	}
}

// TestView_Error: "error: " + mensaje + "\n" + wantHelpLine. Prioridad sobre
// Loading dentro de la vista de gates (default).
func TestView_Error(t *testing.T) {
	got := View(Model{Err: errors.New("boom"), Loading: true, Summary: "x"})
	want := "error: boom\n" + wantHelpLine
	if got != want {
		t.Errorf("View error mismatch: want %q, got %q", want, got)
	}
}

// TestView_Loading: "cargando gates...\n" + wantHelpLine (sin error, sin quitting,
// vista gates).
func TestView_Loading(t *testing.T) {
	got := View(Model{Loading: true, Summary: "x"})
	want := "cargando gates...\n" + wantHelpLine
	if got != want {
		t.Errorf("View loading mismatch: want %q, got %q", want, got)
	}
}

// TestView_Normal: el resumen tal cual + un newline final + wantHelpLine. Como
// kdd.Summarize NO trae trailing newline (por diseno), View es quien lo agrega.
func TestView_Normal(t *testing.T) {
	summary := "overall_ok=true pass=2 fail=0\n[PASS] a\n[PASS] b"
	got := View(Model{Summary: summary})
	want := summary + "\n" + wantHelpLine
	if got != want {
		t.Errorf("View normal mismatch: want %q, got %q", want, got)
	}
	if strings.HasSuffix(got, "\n\n") {
		t.Errorf("View should not end with double newline: %q", got)
	}
}

// TestView_DefaultViewModeIsGates: ViewMode en zero-value ("") se comporta como
// "gates": usa Summary/Err/Loading (no Contracts). Aqui loading gates ->
// "cargando gates...\n" + wantHelpLine.
func TestView_DefaultViewModeIsGates(t *testing.T) {
	got := View(Model{ViewMode: "", Loading: true, ContractsLoading: true, Contracts: "contracts=9"})
	want := "cargando gates...\n" + wantHelpLine
	if got != want {
		t.Errorf("zero-value ViewMode should render gates: want %q, got %q", want, got)
	}
}

// --- View: vista de contracts ---

// TestView_ContractsError: en ViewMode contracts, error > loading > resumen:
// "error: <err>\n" + wantHelpLine.
func TestView_ContractsError(t *testing.T) {
	got := View(Model{ViewMode: "contracts", ContractsErr: errors.New("contracts boom"), ContractsLoading: true, Contracts: "x"})
	want := "error: contracts boom\n" + wantHelpLine
	if got != want {
		t.Errorf("View contracts error mismatch: want %q, got %q", want, got)
	}
}

// TestView_ContractsLoading: en ViewMode contracts sin error, "cargando
// contratos...\n" + wantHelpLine.
func TestView_ContractsLoading(t *testing.T) {
	got := View(Model{ViewMode: "contracts", ContractsLoading: true})
	want := "cargando contratos...\n" + wantHelpLine
	if got != want {
		t.Errorf("View contracts loading mismatch: want %q, got %q", want, got)
	}
}

// TestView_ContractsNormal: en ViewMode contracts sin error ni loading, el
// resumen de contratos + "\n" + wantHelpLine.
func TestView_ContractsNormal(t *testing.T) {
	summary := "contracts=2\na: draft\nb: verified"
	got := View(Model{ViewMode: "contracts", Contracts: summary})
	want := summary + "\n" + wantHelpLine
	if got != want {
		t.Errorf("View contracts normal mismatch: want %q, got %q", want, got)
	}
}

// TestView_GatesUnaffectedByContractsFields: estando en vista gates, los campos
// de contracts NO influyen: un ContractsErr seteado no aparece si Err es nil y
// no esta loading gates -> resumen de gates + wantHelpLine.
func TestView_GatesUnaffectedByContractsFields(t *testing.T) {
	got := View(Model{ViewMode: "gates", Summary: "overall_ok=true pass=0 fail=0", ContractsErr: errors.New("must not show"), ContractsLoading: true})
	want := "overall_ok=true pass=0 fail=0\n" + wantHelpLine
	if got != want {
		t.Errorf("gates view should ignore contracts fields: want %q, got %q", want, got)
	}
}

// --- View: linea extra de ScaffoldMsg (nuevo) ---

// TestView_Normal_WithScaffoldMsg_AddsLine: en vista normal (no scaffolding),
// si ScaffoldMsg != "" se agrega una linea "\n" + ScaffoldMsg ANTES de helpLine.
func TestView_Normal_WithScaffoldMsg_AddsLine(t *testing.T) {
	summary := "overall_ok=true pass=2 fail=0"
	got := View(Model{Summary: summary, ScaffoldMsg: "creado: knowledge/contracts/foo.md"})
	want := summary + "\n" + "\ncreado: knowledge/contracts/foo.md" + wantHelpLine
	if got != want {
		t.Errorf("want %q, got %q", want, got)
	}
}

// TestView_Contracts_WithScaffoldMsg_AddsLine: la linea extra de ScaffoldMsg se
// agrega tambien en la vista de contracts.
func TestView_Contracts_WithScaffoldMsg_AddsLine(t *testing.T) {
	summary := "contracts=2\na: draft"
	got := View(Model{ViewMode: "contracts", Contracts: summary, ScaffoldMsg: "error: bad"})
	want := summary + "\n" + "\nerror: bad" + wantHelpLine
	if got != want {
		t.Errorf("want %q, got %q", want, got)
	}
}

// TestView_Normal_WithEmptyScaffoldMsg_NoExtraLine: con ScaffoldMsg vacio NO se
// agrega nada: byte-identico al comportamiento previo a esta tarea (sin la
// linea extra). Verifica que el layout no cambio para el caso comun.
func TestView_Normal_WithEmptyScaffoldMsg_NoExtraLine(t *testing.T) {
	summary := "overall_ok=true pass=2 fail=0"
	got := View(Model{Summary: summary, ScaffoldMsg: ""})
	want := summary + "\n" + wantHelpLine
	if got != want {
		t.Errorf("want %q, got %q", want, got)
	}
}