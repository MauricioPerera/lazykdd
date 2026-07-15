package ui

import (
	tea "github.com/charmbracelet/bubbletea"
)

// Model es el estado de la primera capa interactiva de la Piel 3: un solo
// "screen" que carga el resumen de gates y lo muestra. Arquitectura Elm: la
// logica pura (UpdateModel/View, aqui, testeable, target del contrato CCDD) va
// SEPARADA del wiring de I/O real (el wrapper teaModel en program.go, glue, no
// testeado, mismo criterio que main.go).
type Model struct {
	// Summary es el string de kdd.Summarize; vacio si no cargo aun.
	Summary string
	// Err es el error de kdd.Summarize o del shell-out; nil si ok.
	Err error
	// Loading es true hasta que llega el primer resultado (gatesLoadedMsg).
	Loading bool
	// Quitting es true una vez que el usuario pidio salir ("q" / ctrl+c).
	Quitting bool
}

// gatesLoadedMsg es el mensaje propio que llega cuando termina de cargar el
// resumen de gates (producido por el Init() del wrapper en program.go).
type gatesLoadedMsg struct {
	summary string
	err     error
}

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
	case tea.KeyMsg:
		switch msg.String() {
		case "q", "ctrl+c":
			m.Quitting = true
			return m, tea.Quit
		default:
			return m, nil
		}
	default:
		return m, nil
	}
}

// View renderiza la Model a un string. Pura, sin I/O. Precedencia: quitting >
// error > loading > resumen. Agrega el newline final que kdd.Summarize no trae
// (por diseno de la tarea anterior) para que el prompt de la terminal no quede
// pegado.
func View(m Model) string {
	switch {
	case m.Quitting:
		return ""
	case m.Err != nil:
		return "error: " + m.Err.Error() + "\n"
	case m.Loading:
		return "cargando gates...\n"
	default:
		return m.Summary + "\n"
	}
}