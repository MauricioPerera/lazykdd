package ui

import (
	tea "github.com/charmbracelet/bubbletea"
)

// Model es el estado de la capa interactiva de la Piel 3: dos "screens" que el
// usuario alterna con teclas — la vista de gates (la que ya existia) y la vista
// de contratos (nueva, via contracts status --json). Arquitectura Elm: la
// logica pura (UpdateModel/View, aqui, testeable, target del contrato CCDD) va
// SEPARADA del wiring de I/O real (el wrapper tea.Model en program.go, glue, no
// testeado, mismo criterio que main.go).
type Model struct {
	// --- gates ---
	// Summary es el string de kdd.Summarize; vacio si no cargo aun.
	Summary string
	// Err es el error de kdd.Summarize o del shell-out de gates; nil si ok.
	Err error
	// Loading es true hasta que llega el primer resultado de gates (gatesLoadedMsg).
	Loading bool
	// --- contracts ---
	// Contracts es el string de kdd.SummarizeContractsStatus; vacio si no cargo.
	Contracts string
	// ContractsErr es el error de contracts status o del shell-out; nil si ok.
	ContractsErr error
	// ContractsLoading es true hasta que llega contractsLoadedMsg.
	ContractsLoading bool
	// --- comunes ---
	// ViewMode gobierna que muestra View: "gates" (default) o "contracts".
	// El zero-value "" se trata EXACTAMENTE igual que "gates" en View (no hace
	// falta setearlo explicito al construir la Model inicial en program.go: el
	// primer render muestra gates, que es el default historico).
	ViewMode string
	// Quitting es true una vez que el usuario pidio salir ("q" / ctrl+c).
	Quitting bool
}

// gatesLoadedMsg es el mensaje propio que llega cuando termina de cargar el
// resumen de gates (producido por el Init() del wrapper en program.go).
type gatesLoadedMsg struct {
	summary string
	err     error
}

// contractsLoadedMsg es el mensaje propio que llega cuando termina de cargar el
// resumen de contratos (producido por el Init() del wrapper en program.go, en
// paralelo con gatesLoadedMsg via tea.Batch).
type contractsLoadedMsg struct {
	summary string
	err     error
}

// helpLine es la linea de ayuda que View agrega SIEMPRE al final (salvo cuando
// esta quitting, que devuelve ""). Literal exacto exigido por el contrato.
const helpLine = "\n[g]ates [c]ontracts [q]uit"

// UpdateModel es la funcion pura que gobierna este contrato: dada una Model y
// un tea.Msg, devuelve la nueva Model y un tea.Cmd. Sin I/O, sin red, sin
// goroutines, sin llamar a Bubble Tea real mas alla de sus TIPOS (tea.KeyMsg,
// tea.Quit). Nunca paniquea: usa type switch con default (no type assertion sin
// ", ok").
func UpdateModel(m Model, msg tea.Msg) (Model, tea.Cmd) {
	switch msg := msg.(type) {
	case gatesLoadedMsg:
		m.Summary = msg.summary
		m.Err = msg.err
		m.Loading = false
		return m, nil
	case contractsLoadedMsg:
		m.Contracts = msg.summary
		m.ContractsErr = msg.err
		m.ContractsLoading = false
		return m, nil
	case tea.KeyMsg:
		switch msg.String() {
		case "q", "ctrl+c":
			m.Quitting = true
			return m, tea.Quit
		case "g":
			m.ViewMode = "gates"
			return m, nil
		case "c":
			m.ViewMode = "contracts"
			return m, nil
		default:
			return m, nil
		}
	default:
		return m, nil
	}
}

// View renderiza la Model a un string. Pura, sin I/O. Precedencia: quitting >
// (segun ViewMode) error > loading > resumen, y la linea de ayuda al final.
// ViewMode == "contracts" usa los campos de contracts; cualquier otro valor
// (incluido el zero-value "") usa los de gates (default historico).
//
// El cuerpo de cada vista es el mismo formato que ya usaba View para gates,
// aplicado a los campos que correspondan: "error: <err>\n" / "cargando
// gates...\n" (o "cargando contratos...\n" para contracts) / "<resumen>\n". A
// eso se le agrega la linea de ayuda helpLine al final (un \n + el literal).
// Cuando m.Quitting es true devuelve "" (precedencia sobre todo, sin ayuda).
func View(m Model) string {
	if m.Quitting {
		return ""
	}
	var body string
	if m.ViewMode == "contracts" {
		switch {
		case m.ContractsErr != nil:
			body = "error: " + m.ContractsErr.Error() + "\n"
		case m.ContractsLoading:
			body = "cargando contratos...\n"
		default:
			body = m.Contracts + "\n"
		}
	} else {
		switch {
		case m.Err != nil:
			body = "error: " + m.Err.Error() + "\n"
		case m.Loading:
			body = "cargando gates...\n"
		default:
			body = m.Summary + "\n"
		}
	}
	return body + helpLine
}