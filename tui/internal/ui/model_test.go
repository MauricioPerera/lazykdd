package ui

import (
	"errors"
	"strings"
	"testing"

	tea "github.com/charmbracelet/bubbletea"

	"github.com/MauricioPerera/lazykdd/tui/internal/kdd"
)

// wantHelpLine es el literal EXACTO que View debe agregar al final de la vista
// normal (salvo quitting/scaffolding/detalle). Se declara aca (con otro nombre
// que el const del paquete) para que el oraculo sea independiente del target:
// si alguien cambia el literal en model.go, este test lo pega y falla, que es
// justo lo que debe hacer un oraculo congelado. El const del paquete (helpLine
// en model.go) NO se usa desde los tests; estos referencian solo a wantHelpLine.
const wantHelpLine = "\n[g]ates [c]ontracts [r]efresh [n]ew [q]uit"

// wantDetailHelpLine es el literal EXACTO de la linea de ayuda DISTINTA que View
// agrega al final de la vista de detalle (mismo rol que wantHelpLine pero para
// la vista de detalle, donde la unica accion es Esc).
const wantDetailHelpLine = "\n[esc] volver"

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

// --- UpdateModel: contractsLoadedMsg (comportamiento historico + items nuevo) ---
//
// El comportamiento historico (setear Contracts/ContractsErr/ContractsLoading,
// preservar gates/ViewMode/Quitting) se preserva intacto. ADEMAS, el handler
// ahora setea ContractItems desde msg.items y clampea SelectedIndex si queda
// fuera de rango tras la carga.

// TestUpdateModel_ContractsLoadedSuccess: un contractsLoadedMsg exitoso setea
// Contracts, limpia ContractsErr, baja ContractsLoading y NO pide comandos.
// Los campos de gates (Summary/Err/Loading) y Quitting se preservan sin cambios.
// (Caso historico: el msg no trae items -> ContractItems queda nil, que es
// valido; el oraculo viejo no aserta sobre items.)
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

// TestUpdateModel_ContractsLoaded_SetsItems: el campo items del msg se copia a
// ContractItems tal cual (en el orden que los entrega ParseContractsStatus, ya
// alfabetico). SelectedIndex en rango se preserva. cmd nil.
func TestUpdateModel_ContractsLoaded_SetsItems(t *testing.T) {
	items := []kdd.ContractStatus{
		{Task: "a", Lifecycle: "draft"},
		{Task: "b", Lifecycle: "verified"},
		{Task: "c", Lifecycle: "implemented"},
	}
	m := Model{ContractsLoading: true, SelectedIndex: 1}
	got, cmd := UpdateModel(m, contractsLoadedMsg{summary: "contracts=3", items: items, err: nil})
	if cmd != nil {
		t.Errorf("expected nil cmd")
	}
	if len(got.ContractItems) != 3 {
		t.Fatalf("ContractItems len: want 3, got %d", len(got.ContractItems))
	}
	for i := range items {
		if got.ContractItems[i] != items[i] {
			t.Errorf("ContractItems[%d]: want %+v, got %+v", i, items[i], got.ContractItems[i])
		}
	}
	if got.SelectedIndex != 1 {
		t.Errorf("SelectedIndex in-range should be preserved, got %d", got.SelectedIndex)
	}
}

// TestUpdateModel_ContractsLoaded_ClampsSelectedIndex: si la lista se achica y
// SelectedIndex queda > len-1, se clampea a len-1. cmd nil.
func TestUpdateModel_ContractsLoaded_ClampsSelectedIndex(t *testing.T) {
	items := []kdd.ContractStatus{{Task: "a", Lifecycle: "draft"}, {Task: "b", Lifecycle: "verified"}}
	m := Model{ContractsLoading: true, SelectedIndex: 5}
	got, _ := UpdateModel(m, contractsLoadedMsg{summary: "contracts=2", items: items, err: nil})
	if got.SelectedIndex != 1 {
		t.Errorf("SelectedIndex should clamp to len-1=1, got %d", got.SelectedIndex)
	}
}

// TestUpdateModel_ContractsLoaded_EmptyItemsResetsSelectedIndex: una lista vacia
// clampea SelectedIndex a 0 (no -1). cmd nil.
func TestUpdateModel_ContractsLoaded_EmptyItemsResetsSelectedIndex(t *testing.T) {
	m := Model{ContractsLoading: true, SelectedIndex: 3}
	got, _ := UpdateModel(m, contractsLoadedMsg{summary: "contracts=0", items: []kdd.ContractStatus{}, err: nil})
	if got.SelectedIndex != 0 {
		t.Errorf("SelectedIndex should be 0 for empty list, got %d", got.SelectedIndex)
	}
}

// TestUpdateModel_ContractsLoaded_NilItemsResetsSelectedIndex: items nil (ej.
// el caso historico sin items) tambien deja SelectedIndex en 0.
func TestUpdateModel_ContractsLoaded_NilItemsResetsSelectedIndex(t *testing.T) {
	m := Model{ContractsLoading: true, SelectedIndex: 2}
	got, _ := UpdateModel(m, contractsLoadedMsg{summary: "contracts=0", items: nil, err: nil})
	if got.SelectedIndex != 0 {
		t.Errorf("SelectedIndex should be 0 for nil items, got %d", got.SelectedIndex)
	}
}

// --- UpdateModel: contractDetailMsg (nuevo) ---

// TestUpdateModel_ContractDetail_Success: un contractDetailMsg sin error setea
// Detail, limpia DetailErr, baja DetailLoading. ViewingDetail YA era true (lo
// seteo el Enter) y se PRESERVA. cmd nil.
func TestUpdateModel_ContractDetail_Success(t *testing.T) {
	m := Model{ViewingDetail: true, DetailLoading: true, Detail: "", DetailErr: nil, SelectedIndex: 1}
	got, cmd := UpdateModel(m, contractDetailMsg{content: "---\ntask: x\n---\nbody", err: nil})
	if cmd != nil {
		t.Errorf("expected nil cmd")
	}
	if got.Detail != "---\ntask: x\n---\nbody" {
		t.Errorf("Detail mismatch: %q", got.Detail)
	}
	if got.DetailErr != nil {
		t.Errorf("DetailErr should be nil, got %v", got.DetailErr)
	}
	if got.DetailLoading {
		t.Errorf("DetailLoading should be false")
	}
	if !got.ViewingDetail {
		t.Errorf("ViewingDetail should stay true")
	}
	if got.SelectedIndex != 1 {
		t.Errorf("SelectedIndex should be preserved, got %d", got.SelectedIndex)
	}
}

// TestUpdateModel_ContractDetail_Error: un contractDetailMsg con error setea
// DetailErr, baja DetailLoading. ViewingDetail se preserva (sigue en detalle
// para mostrar el error). cmd nil.
func TestUpdateModel_ContractDetail_Error(t *testing.T) {
	m := Model{ViewingDetail: true, DetailLoading: true}
	boom := errors.New("no such file")
	got, cmd := UpdateModel(m, contractDetailMsg{content: "", err: boom})
	if cmd != nil {
		t.Errorf("expected nil cmd")
	}
	if got.DetailErr != boom {
		t.Errorf("DetailErr mismatch: want %v, got %v", boom, got.DetailErr)
	}
	if got.DetailLoading {
		t.Errorf("DetailLoading should be false")
	}
	if !got.ViewingDetail {
		t.Errorf("ViewingDetail should stay true (show the error)")
	}
}

// --- UpdateModel: scaffoldDoneMsg (comportamiento historico, sin cambios) ---

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
//
// Estas teclas funcionan en AMBAS vistas (gates y contracts) cuando NO se esta
// scaffolding ni viendo detalle - comportamiento historico sin cambios. La
// navegacion (flechas/Enter) es extra y se testa aparte (solo en contracts).

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
// loadGates/loadContracts) lo dispara el wiring en program.Update, no aca.
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
// (ni flecha/Enter en contracts) no cambia el model ni pide comandos.
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

// --- UpdateModel: navegacion de la lista de contratos (nuevo) ---
//
// Flechas y Enter NAVEGAN solo cuando ViewMode == "contracts" Y !Scaffolding Y
// !ViewingDetail. En gates view las flechas/Enter no hacen nada (caen al default
// de las teclas de comando).

// TestUpdateModel_KeyDown_Increments: flecha abajo en contracts incrementa
// SelectedIndex. cmd nil.
func TestUpdateModel_KeyDown_Increments(t *testing.T) {
	items := []kdd.ContractStatus{{Task: "a", Lifecycle: "draft"}, {Task: "b", Lifecycle: "verified"}, {Task: "c", Lifecycle: "implemented"}}
	m := Model{ViewMode: "contracts", ContractItems: items, SelectedIndex: 1}
	got, cmd := UpdateModel(m, tea.KeyMsg{Type: tea.KeyDown})
	if cmd != nil {
		t.Errorf("expected nil cmd")
	}
	if got.SelectedIndex != 2 {
		t.Errorf("SelectedIndex should increment to 2, got %d", got.SelectedIndex)
	}
}

// TestUpdateModel_KeyDown_ClampsAtBottom: flecha abajo en la ultima fila no da
// la vuelta: SelectedIndex se queda en len-1. cmd nil.
func TestUpdateModel_KeyDown_ClampsAtBottom(t *testing.T) {
	items := []kdd.ContractStatus{{Task: "a", Lifecycle: "draft"}, {Task: "b", Lifecycle: "verified"}, {Task: "c", Lifecycle: "implemented"}}
	m := Model{ViewMode: "contracts", ContractItems: items, SelectedIndex: 2}
	got, cmd := UpdateModel(m, tea.KeyMsg{Type: tea.KeyDown})
	if cmd != nil {
		t.Errorf("expected nil cmd")
	}
	if got.SelectedIndex != 2 {
		t.Errorf("SelectedIndex should clamp at len-1=2, got %d", got.SelectedIndex)
	}
}

// TestUpdateModel_KeyDown_EmptyList_NoChange: flecha abajo con lista vacia no
// cambia SelectedIndex (no lo lleva a -1) ni paniquea. cmd nil.
func TestUpdateModel_KeyDown_EmptyList_NoChange(t *testing.T) {
	m := Model{ViewMode: "contracts", ContractItems: nil, SelectedIndex: 0}
	got, cmd := UpdateModel(m, tea.KeyMsg{Type: tea.KeyDown})
	if cmd != nil {
		t.Errorf("expected nil cmd")
	}
	if got.SelectedIndex != 0 {
		t.Errorf("SelectedIndex should stay 0 on empty list, got %d", got.SelectedIndex)
	}
}

// TestUpdateModel_KeyUp_Decrements: flecha arriba en contracts decrementa
// SelectedIndex. cmd nil.
func TestUpdateModel_KeyUp_Decrements(t *testing.T) {
	items := []kdd.ContractStatus{{Task: "a", Lifecycle: "draft"}, {Task: "b", Lifecycle: "verified"}, {Task: "c", Lifecycle: "implemented"}}
	m := Model{ViewMode: "contracts", ContractItems: items, SelectedIndex: 2}
	got, cmd := UpdateModel(m, tea.KeyMsg{Type: tea.KeyUp})
	if cmd != nil {
		t.Errorf("expected nil cmd")
	}
	if got.SelectedIndex != 1 {
		t.Errorf("SelectedIndex should decrement to 1, got %d", got.SelectedIndex)
	}
}

// TestUpdateModel_KeyUp_ClampsAtTop: flecha arriba en la primera fila no baja de
// 0 (no da la vuelta). cmd nil.
func TestUpdateModel_KeyUp_ClampsAtTop(t *testing.T) {
	items := []kdd.ContractStatus{{Task: "a", Lifecycle: "draft"}, {Task: "b", Lifecycle: "verified"}}
	m := Model{ViewMode: "contracts", ContractItems: items, SelectedIndex: 0}
	got, cmd := UpdateModel(m, tea.KeyMsg{Type: tea.KeyUp})
	if cmd != nil {
		t.Errorf("expected nil cmd")
	}
	if got.SelectedIndex != 0 {
		t.Errorf("SelectedIndex should clamp at 0, got %d", got.SelectedIndex)
	}
}

// TestUpdateModel_Arrows_NoEffectInGatesView: en gates view las flechas NO
// navegan (caen al default de las teclas de comando): SelectedIndex sin cambios.
func TestUpdateModel_Arrows_NoEffectInGatesView(t *testing.T) {
	items := []kdd.ContractStatus{{Task: "a", Lifecycle: "draft"}, {Task: "b", Lifecycle: "verified"}}
	m := Model{ViewMode: "gates", ContractItems: items, SelectedIndex: 0}
	for _, key := range []tea.KeyMsg{{Type: tea.KeyUp}, {Type: tea.KeyDown}} {
		got, cmd := UpdateModel(m, key)
		if cmd != nil {
			t.Errorf("expected nil cmd for %v in gates view", key.Type)
		}
		if got.SelectedIndex != 0 {
			t.Errorf("arrows should not navigate in gates view, got %d", got.SelectedIndex)
		}
	}
}

// TestUpdateModel_Enter_ContractsList_Empty_NoAction: Enter con lista vacia no
// hace nada (no entra en detalle, no paniquea). cmd nil.
func TestUpdateModel_Enter_ContractsList_Empty_NoAction(t *testing.T) {
	m := Model{ViewMode: "contracts", ContractItems: nil, SelectedIndex: 0}
	got, cmd := UpdateModel(m, tea.KeyMsg{Type: tea.KeyEnter})
	if cmd != nil {
		t.Errorf("expected nil cmd")
	}
	if got.ViewingDetail {
		t.Errorf("ViewingDetail should stay false on empty list Enter")
	}
}

// TestUpdateModel_Enter_ContractsList_NonEmpty_EntersDetail: Enter con lista no
// vacia entra en ViewingDetail + DetailLoading, limpia Detail/DetailErr. cmd nil
// (la funcion pura no lee archivos; el loadDetail real lo dispara el wiring).
func TestUpdateModel_Enter_ContractsList_NonEmpty_EntersDetail(t *testing.T) {
	items := []kdd.ContractStatus{{Task: "a", Lifecycle: "draft"}, {Task: "b", Lifecycle: "verified"}}
	m := Model{ViewMode: "contracts", ContractItems: items, SelectedIndex: 1, Detail: "stale", DetailErr: errors.New("stale err")}
	got, cmd := UpdateModel(m, tea.KeyMsg{Type: tea.KeyEnter})
	if cmd != nil {
		t.Errorf("expected nil cmd (pure UpdateModel does not read files)")
	}
	if !got.ViewingDetail {
		t.Errorf("ViewingDetail should be true")
	}
	if !got.DetailLoading {
		t.Errorf("DetailLoading should be true")
	}
	if got.Detail != "" {
		t.Errorf("Detail should be cleared, got %q", got.Detail)
	}
	if got.DetailErr != nil {
		t.Errorf("DetailErr should be cleared, got %v", got.DetailErr)
	}
	if got.SelectedIndex != 1 {
		t.Errorf("SelectedIndex should be preserved, got %d", got.SelectedIndex)
	}
}

// TestUpdateModel_Enter_GatesView_NoAction: Enter en gates view no hace nada
// (no es navegacion aca). cmd nil.
func TestUpdateModel_Enter_GatesView_NoAction(t *testing.T) {
	m := Model{ViewMode: "gates", ContractItems: []kdd.ContractStatus{{Task: "a", Lifecycle: "draft"}}, SelectedIndex: 0}
	got, cmd := UpdateModel(m, tea.KeyMsg{Type: tea.KeyEnter})
	if cmd != nil {
		t.Errorf("expected nil cmd")
	}
	if got.ViewingDetail {
		t.Errorf("ViewingDetail should stay false in gates view")
	}
}

// --- UpdateModel: teclas durante ViewingDetail (nuevo) ---
//
// Mientras se ve el detalle, SOLO Esc hace algo (vuelve a la lista
// preservando SelectedIndex). Cualquier otra tecla (incluidas "q"/"g"/"c"/"r"/
// "n") se IGNORA: decision de UX explicita, evita que "q" salga del programa
// entero cuando el usuario solo quiere volver atras.

// TestUpdateModel_Detail_Esc_ReturnsToList_PreservesSelectedIndex: Esc desde el
// detalle vuelve a la lista (ViewingDetail false, Detail/DetailErr limpios) y
// PRESERVA SelectedIndex (el cursor no se mueve al salir del detalle). cmd nil.
func TestUpdateModel_Detail_Esc_ReturnsToList_PreservesSelectedIndex(t *testing.T) {
	m := Model{ViewingDetail: true, Detail: "---\nx", DetailErr: errors.New("e"), SelectedIndex: 1, ViewMode: "contracts"}
	got, cmd := UpdateModel(m, tea.KeyMsg{Type: tea.KeyEsc})
	if cmd != nil {
		t.Errorf("expected nil cmd")
	}
	if got.ViewingDetail {
		t.Errorf("ViewingDetail should be false")
	}
	if got.Detail != "" {
		t.Errorf("Detail should be cleared, got %q", got.Detail)
	}
	if got.DetailErr != nil {
		t.Errorf("DetailErr should be cleared, got %v", got.DetailErr)
	}
	if got.SelectedIndex != 1 {
		t.Errorf("SelectedIndex should be preserved (1), got %d", got.SelectedIndex)
	}
}

// TestUpdateModel_Detail_Q_Ignored: test EXPLICITO de que "q" durante el detalle
// NO sale del programa (Quitting se queda false, cmd nil, NO tea.Quit). El
// usuario debe apretar Esc primero para volver a la lista.
func TestUpdateModel_Detail_Q_Ignored(t *testing.T) {
	m := Model{ViewingDetail: true, Quitting: false, ViewMode: "contracts"}
	got, cmd := UpdateModel(m, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("q")})
	if cmd != nil {
		t.Errorf("expected nil cmd (q ignored during detail, no tea.Quit)")
	}
	if got.Quitting {
		t.Errorf("Quitting should stay false (q ignored during detail)")
	}
	if !got.ViewingDetail {
		t.Errorf("ViewingDetail should stay true (q ignored)")
	}
}

// TestUpdateModel_Detail_CommandKeys_Ignored: "g"/"c"/"r"/"n" durante el detalle
// NO hacen nada (ViewMode sin cambios, no entra scaffolding, no refresh de
// flags). Solo Esc sale del detalle.
func TestUpdateModel_Detail_CommandKeys_Ignored(t *testing.T) {
	for _, ch := range []string{"g", "c", "r", "n"} {
		m := Model{ViewingDetail: true, ViewMode: "contracts", Scaffolding: false, Loading: false, ContractsLoading: false}
		got, cmd := UpdateModel(m, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune(ch)})
		if cmd != nil {
			t.Errorf("key %q: expected nil cmd (ignored during detail)", ch)
		}
		if !got.ViewingDetail {
			t.Errorf("key %q: ViewingDetail should stay true", ch)
		}
		if got.ViewMode != "contracts" {
			t.Errorf("key %q: ViewMode should be unchanged, got %q", ch, got.ViewMode)
		}
		if got.Scaffolding {
			t.Errorf("key %q: should not enter scaffolding during detail", ch)
		}
		if got.Loading || got.ContractsLoading {
			t.Errorf("key %q: should not trigger refresh flags during detail", ch)
		}
	}
}

// TestUpdateModel_Detail_Arrows_Ignored: flechas durante el detalle no mueven el
// cursor (no estamos en la lista). SelectedIndex sin cambios.
func TestUpdateModel_Detail_Arrows_Ignored(t *testing.T) {
	items := []kdd.ContractStatus{{Task: "a", Lifecycle: "draft"}, {Task: "b", Lifecycle: "verified"}}
	m := Model{ViewingDetail: true, ViewMode: "contracts", ContractItems: items, SelectedIndex: 0}
	for _, key := range []tea.KeyMsg{{Type: tea.KeyUp}, {Type: tea.KeyDown}} {
		got, cmd := UpdateModel(m, key)
		if cmd != nil {
			t.Errorf("expected nil cmd for %v during detail", key.Type)
		}
		if got.SelectedIndex != 0 {
			t.Errorf("arrows should not move cursor during detail, got %d", got.SelectedIndex)
		}
		if !got.ViewingDetail {
			t.Errorf("ViewingDetail should stay true")
		}
	}
}

// --- UpdateModel: modo scaffolding (delegacion a handleScaffoldKey) ---
//
// En modo scaffolding (m.Scaffolding true) TODA tea.KeyMsg se delega a
// handleScaffoldKey ANTES del switch de comandos normal: "g"/"c"/"r"/"q" son
// texto a tipear, NO comandos. Comportamiento historico sin cambios.

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
// handleScaffoldKey fue extraida de UpdateModel por presupuesto de complejidad.
// No es el target del gate (el gate sigue midiendo solo UpdateModel via
// signature), pero SI tiene sus propios casos de test en este oraculo congelado.

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
// de ayuda (no se agrega al salir), el modo scaffolding Y el detalle.
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

// TestView_QuittingPrecedenceOverDetail: quitting gana sobre la vista de detalle
// (no se muestra el .md al salir).
func TestView_QuittingPrecedenceOverDetail(t *testing.T) {
	got := View(Model{Quitting: true, ViewingDetail: true, Detail: "x"})
	if got != "" {
		t.Errorf("expected empty string when quitting, got %q", got)
	}
}

// TestView_Scaffolding_Prompt: en modo scaffolding View devuelve una vista
// DISTINTA que reemplaza TODO lo demas (sin helpLine): el prompt exacto + el
// input tipeado. Sin trailing newline (decision documentada: consistente con
// kdd.Summarize/SummarizeContractsStatus que tampoco lo llevan). Precedencia
// sobre el detalle.
func TestView_Scaffolding_Prompt(t *testing.T) {
	got := View(Model{Scaffolding: true, ScaffoldInput: "my-task", Summary: "x", ViewMode: "contracts", ViewingDetail: true, Detail: "stale"})
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

// --- View: vista de contracts (lista navegable con cursor) ---

// TestView_ContractsError: en ViewMode contracts, error > loading > lista:
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

// TestView_ContractsList_RenderedWithCursor: la vista normal de contracts
// RENDERIZA la lista desde ContractItems con el cursor "> " en la fila
// SelectedIndex y "  " en las demas, con header "contracts=<N>". Mantiene el
// formato "<task>: <lifecycle>" por fila. helpLine al final.
func TestView_ContractsList_RenderedWithCursor(t *testing.T) {
	items := []kdd.ContractStatus{
		{Task: "a", Lifecycle: "draft"},
		{Task: "b", Lifecycle: "verified"},
		{Task: "c", Lifecycle: "implemented"},
	}
	got := View(Model{ViewMode: "contracts", ContractItems: items, SelectedIndex: 1})
	want := "contracts=3\n  a: draft\n> b: verified\n  c: implemented\n" + wantHelpLine
	if got != want {
		t.Errorf("View contracts list mismatch: want %q, got %q", want, got)
	}
}

// TestView_ContractsList_CursorAtTop: el cursor en la primera fila pone "> " ahi.
func TestView_ContractsList_CursorAtTop(t *testing.T) {
	items := []kdd.ContractStatus{{Task: "a", Lifecycle: "draft"}, {Task: "b", Lifecycle: "verified"}}
	got := View(Model{ViewMode: "contracts", ContractItems: items, SelectedIndex: 0})
	want := "contracts=2\n> a: draft\n  b: verified\n" + wantHelpLine
	if got != want {
		t.Errorf("cursor at top mismatch: want %q, got %q", want, got)
	}
}

// TestView_ContractsList_CursorAtBottom: el cursor en la ultima fila.
func TestView_ContractsList_CursorAtBottom(t *testing.T) {
	items := []kdd.ContractStatus{{Task: "a", Lifecycle: "draft"}, {Task: "b", Lifecycle: "verified"}}
	got := View(Model{ViewMode: "contracts", ContractItems: items, SelectedIndex: 1})
	want := "contracts=2\n  a: draft\n> b: verified\n" + wantHelpLine
	if got != want {
		t.Errorf("cursor at bottom mismatch: want %q, got %q", want, got)
	}
}

// TestView_ContractsList_Empty: lista vacia (o nil) -> solo header "contracts=0"
// + "\n" + wantHelpLine (sin filas, sin cursor).
func TestView_ContractsList_Empty(t *testing.T) {
	got := View(Model{ViewMode: "contracts", ContractItems: nil})
	want := "contracts=0\n" + wantHelpLine
	if got != want {
		t.Errorf("empty list mismatch: want %q, got %q", want, got)
	}
}

// TestView_ContractsList_SingleElement: un solo elemento con cursor en 0.
func TestView_ContractsList_SingleElement(t *testing.T) {
	items := []kdd.ContractStatus{{Task: "only", Lifecycle: "draft"}}
	got := View(Model{ViewMode: "contracts", ContractItems: items, SelectedIndex: 0})
	want := "contracts=1\n> only: draft\n" + wantHelpLine
	if got != want {
		t.Errorf("single element mismatch: want %q, got %q", want, got)
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

// --- View: vista de detalle (nuevo) ---

// TestView_Detail_Loading: mientras carga el .md, "cargando contrato...\n" (sin
// helpLine normal).
func TestView_Detail_Loading(t *testing.T) {
	got := View(Model{ViewingDetail: true, DetailLoading: true})
	want := "cargando contrato...\n"
	if got != want {
		t.Errorf("detail loading mismatch: want %q, got %q", want, got)
	}
}

// TestView_Detail_Error: si loadDetail fallo, "error: <err>" (sin trailing
// newline, sin helpLine normal).
func TestView_Detail_Error(t *testing.T) {
	got := View(Model{ViewingDetail: true, DetailErr: errors.New("no such file")})
	want := "error: no such file"
	if got != want {
		t.Errorf("detail error mismatch: want %q, got %q", want, got)
	}
}

// TestView_Detail_Content: el contenido del .md tal cual + la linea de ayuda
// propia "\n[esc] volver" al final (sin helpLine normal, sin modificar el .md).
func TestView_Detail_Content(t *testing.T) {
	content := "---\ntask: x\n---\n# Contract\nbody"
	got := View(Model{ViewingDetail: true, Detail: content})
	want := content + wantDetailHelpLine
	if got != want {
		t.Errorf("detail content mismatch: want %q, got %q", want, got)
	}
}

// TestView_Detail_EmptyContent: contenido vacio (no deberia pasar con un .md
// real, pero View no paniquea) -> solo la linea de ayuda.
func TestView_Detail_EmptyContent(t *testing.T) {
	got := View(Model{ViewingDetail: true, Detail: ""})
	want := wantDetailHelpLine
	if got != want {
		t.Errorf("detail empty content mismatch: want %q, got %q", want, got)
	}
}

// TestView_DetailPrecedenceOverContracts: la vista de detalle gana sobre la
// vista normal de contracts incluso si contracts tiene error de carga: muestra
// el detalle (loading aca), no el error de contracts.
func TestView_DetailPrecedenceOverContracts(t *testing.T) {
	got := View(Model{ViewingDetail: true, DetailLoading: true, ViewMode: "contracts", ContractsErr: errors.New("contracts boom"), ContractsLoading: false})
	want := "cargando contrato...\n"
	if got != want {
		t.Errorf("detail should win over contracts error: want %q, got %q", want, got)
	}
}

// TestView_ScaffoldingPrecedenceOverDetail: scaffolding gana sobre el detalle
// (no se muestra el .md mientras se tipea un nombre nuevo). Cubierto por
// TestView_Scaffolding_Prompt que pasa ViewingDetail:true; aca un caso extra
// con buffer vacio.
func TestView_ScaffoldingPrecedenceOverDetail(t *testing.T) {
	got := View(Model{Scaffolding: true, ScaffoldInput: "", ViewingDetail: true, Detail: "stale"})
	want := "nuevo contrato (kebab-case), enter confirma, esc cancela:\n> "
	if got != want {
		t.Errorf("scaffolding should win over detail: want %q, got %q", want, got)
	}
}

// --- View: linea extra de ScaffoldMsg (solo en vista normal) ---

// TestView_Normal_WithScaffoldMsg_AddsLine: en vista normal (no scaffolding, no
// detalle), si ScaffoldMsg != "" se agrega una linea "\n" + ScaffoldMsg ANTES
// de helpLine.
func TestView_Normal_WithScaffoldMsg_AddsLine(t *testing.T) {
	summary := "overall_ok=true pass=2 fail=0"
	got := View(Model{Summary: summary, ScaffoldMsg: "creado: knowledge/contracts/foo.md"})
	want := summary + "\n" + "\ncreado: knowledge/contracts/foo.md" + wantHelpLine
	if got != want {
		t.Errorf("want %q, got %q", want, got)
	}
}

// TestView_ContractsList_WithScaffoldMsg_AddsLine: la linea extra de ScaffoldMsg
// se agrega tambien en la vista de contracts (lista). La lista se renderiza
// desde ContractItems, no desde Contracts.
func TestView_ContractsList_WithScaffoldMsg_AddsLine(t *testing.T) {
	items := []kdd.ContractStatus{{Task: "a", Lifecycle: "draft"}, {Task: "b", Lifecycle: "verified"}}
	got := View(Model{ViewMode: "contracts", ContractItems: items, SelectedIndex: 0, ScaffoldMsg: "error: bad"})
	want := "contracts=2\n> a: draft\n  b: verified\n" + "\nerror: bad" + wantHelpLine
	if got != want {
		t.Errorf("want %q, got %q", want, got)
	}
}

// TestView_Detail_WithScaffoldMsg_NoExtraLine: durante el detalle NO se agrega
// la linea de ScaffoldMsg (la vista de detalle es propia, devuelve antes).
func TestView_Detail_WithScaffoldMsg_NoExtraLine(t *testing.T) {
	got := View(Model{ViewingDetail: true, Detail: "x", ScaffoldMsg: "must not show"})
	want := "x" + wantDetailHelpLine
	if got != want {
		t.Errorf("detail should not show ScaffoldMsg: want %q, got %q", want, got)
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