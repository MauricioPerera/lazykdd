package ui

import (
	"errors"
	"strings"
	"testing"

	tea "github.com/charmbracelet/bubbletea"
)

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

// TestUpdateModel_OtherKey_NoChange: una tecla que no es "q"/"ctrl+c" no
// cambia el model ni pide comandos.
func TestUpdateModel_OtherKey_NoChange(t *testing.T) {
	m := Model{Summary: "s", Err: nil, Loading: true, Quitting: false}
	got, cmd := UpdateModel(m, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("x")})
	if cmd != nil {
		t.Errorf("expected nil cmd for other key")
	}
	if got.Summary != m.Summary || got.Loading != m.Loading || got.Quitting != m.Quitting || got.Err != m.Err {
		t.Errorf("model should be unchanged: want %+v, got %+v", m, got)
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
// salir; no queremos residuo). Tiene prioridad sobre Err y Loading.
func TestView_Quitting(t *testing.T) {
	got := View(Model{Quitting: true, Summary: "whatever", Err: errors.New("e"), Loading: true})
	if got != "" {
		t.Errorf("expected empty string when quitting, got %q", got)
	}
}

// TestView_Error: "error: " + mensaje + "\n". Prioridad sobre Loading.
func TestView_Error(t *testing.T) {
	got := View(Model{Err: errors.New("boom"), Loading: true, Summary: "x"})
	want := "error: boom\n"
	if got != want {
		t.Errorf("View error mismatch: want %q, got %q", want, got)
	}
}

// TestView_Loading: "cargando gates...\n" (sin error, sin quitting).
func TestView_Loading(t *testing.T) {
	got := View(Model{Loading: true, Summary: "x"})
	want := "cargando gates...\n"
	if got != want {
		t.Errorf("View loading mismatch: want %q, got %q", want, got)
	}
}

// TestView_Normal: el resumen tal cual + un unico newline final. Como
// kdd.Summarize NO trae trailing newline (por diseno), View es quien lo agrega.
func TestView_Normal(t *testing.T) {
	summary := "overall_ok=true pass=2 fail=0\n[PASS] a\n[PASS] b"
	got := View(Model{Summary: summary})
	want := summary + "\n"
	if got != want {
		t.Errorf("View normal mismatch: want %q, got %q", want, got)
	}
	if strings.HasSuffix(got, "\n\n") {
		t.Errorf("View should not add double trailing newline: %q", got)
	}
}