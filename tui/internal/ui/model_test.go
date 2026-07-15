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
const wantHelpLine = "\n[g]ates [c]ontracts [q]uit"

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

// --- UpdateModel: contractsLoadedMsg (nuevo) ---

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

// --- UpdateModel: keys (quit + nuevas teclas de vista) ---

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

// TestUpdateModel_OtherKey_NoChange: una tecla que no es "q"/"ctrl+c"/"g"/"c"
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

// --- View ---

// TestView_Quitting: devuelve string vacio (Bubble Tea limpia la pantalla al
// salir; no queremos residuo). Tiene precedencia sobre todo, incluida la linea
// de ayuda (no se agrega al salir).
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

// --- View: vista de contracts (nueva) ---

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