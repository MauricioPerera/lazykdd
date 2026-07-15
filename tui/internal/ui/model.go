package ui

import (
	tea "github.com/charmbracelet/bubbletea"
)

// Model es el estado de la capa interactiva de la Piel 3: dos "screens" que el
// usuario alterna con teclas — la vista de gates (la que ya existia) y la vista
// de contratos (nueva, via contracts status --json) — mas un modo de
// scaffolding interactivo (tecla "n") para crear contratos nuevos sin salir de
// la TUI. Arquitectura Elm: la logica pura (UpdateModel/View, aqui, testeable,
// target del contrato CCDD) va SEPARADA del wiring de I/O real (el wrapper
// tea.Model en program.go, glue, no testeado, mismo criterio que main.go).
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
	// --- scaffolding (nuevo) ---
	// Scaffolding es true mientras el usuario esta tipeando un nombre de
	// contrato nuevo (modo input, precedencia sobre las teclas de comando).
	Scaffolding bool
	// ScaffoldInput es el buffer de texto tipeado hasta ahora en modo input.
	ScaffoldInput string
	// ScaffoldMsg es el resultado del ultimo intento de scaffold (exito o
	// error), "" si no hubo ninguno aun. Se limpia al entrar de nuevo en modo
	// scaffolding con "n"; al cancelar con Esc NO se toca.
	ScaffoldMsg string
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

// scaffoldDoneMsg es el mensaje propio que llega cuando termina el shell-out de
// `contracts scaffold <name> --json` (producido por loadScaffold del wrapper en
// program.go). path es el contrato creado (si err == nil); err es el error de
// arranque del proceso, de parseo del JSON, o el `"error"` que devuelve el CLI.
type scaffoldDoneMsg struct {
	path string
	err  error
}

// helpLine es la linea de ayuda que View agrega SIEMPRE al final (salvo cuando
// esta quitting o en modo scaffolding, que devuelven vistas propias). Literal
// exacto exigido por el contrato.
const helpLine = "\n[g]ates [c]ontracts [r]efresh [n]ew [q]uit"

// UpdateModel es la funcion pura que gobierna este contrato: dada una Model y
// un tea.Msg, devuelve la nueva Model y un tea.Cmd. Sin I/O, sin red, sin
// goroutines, sin llamar a Bubble Tea real mas alla de sus TIPOS (tea.KeyMsg,
// tea.Quit). Nunca paniquea: usa type switch con default (no type assertion sin
// ", ok").
//
// En modo scaffolding (m.Scaffolding true) TODA tea.KeyMsg se delega a
// handleScaffoldKey ANTES del switch de comandos normal: en ese modo "g"/"c"/
// "r"/"q" son texto a tipear, NO comandos. La delegacion es una sola linea (bajo
// costo) y mantiene UpdateModel dentro del presupuesto de complejidad (ver
// trade-offs en el REPORT): la logica de input vive en handleScaffoldKey.
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
	case scaffoldDoneMsg:
		// Resultado del shell-out de scaffold. Scaffolding ya era false y
		// ScaffoldInput NO se limpia (se pisa la proxima vez que se entra con
		// "n"). cmd nil.
		if msg.err != nil {
			m.ScaffoldMsg = "error: " + msg.err.Error()
		} else {
			m.ScaffoldMsg = "creado: " + msg.path
		}
		return m, nil
	case tea.KeyMsg:
		if m.Scaffolding {
			// Modo input: precedencia sobre TODO. "g"/"c"/"r"/"q" son texto, no
			// comandos. Delegacion al helper.
			return handleScaffoldKey(m, msg)
		}
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
		case "r":
			// Refresh: ambos paneles vuelven a "cargando" y se limpian los
			// errores viejos (un refresco no debe seguir mostrando el error
			// de la carga anterior mientras espera el resultado nuevo). El
			// resto (Summary/Contracts/ViewMode/Quitting) se preserva sin
			// cambios: los resumenes viejos quedan visibles hasta que lleguen
			// los nuevos. La funcion pura NO sabe shellear -> cmd nil; el
			// refresh real (tea.Batch de loadGates/loadContracts) lo dispara
			// el wiring en program.Update al ver esta misma tecla.
			m.Loading = true
			m.ContractsLoading = true
			m.Err = nil
			m.ContractsErr = nil
			return m, nil
		case "n":
			// Entra en modo scaffolding: buffer limpio y se borra el resultado
			// del intento anterior.
			m.Scaffolding = true
			m.ScaffoldInput = ""
			m.ScaffoldMsg = ""
			return m, nil
		default:
			return m, nil
		}
	default:
		return m, nil
	}
}

// handleScaffoldKey maneja las teclas en modo scaffolding (m.Scaffolding true).
// Fue extraida de UpdateModel por presupuesto de complejidad (UpdateModel estaba
// en cyclomatic 8/9 y agregar la logica de input inline la habria excedido). Es
// PURA (sin I/O, sin shellear — el shell-out real lo dispara el wiring en
// program.Update al ver el Enter confirmado) y tiene sus propios tests en el
// oraculo congelado (model_test.go). No es el target del gate (el gate sigue
// midiendo solo UpdateModel via signature), mismo criterio que un helper de la
// funcion contratada. Comportamiento por tea.KeyMsg.Type:
//   - KeyEsc: cancela (Scaffolding false, ScaffoldInput ""), NO toca ScaffoldMsg.
//   - KeyEnter: confirma (Scaffolding false), CONSERVA ScaffoldInput (el wiring
//     lo lee para saber que nombre scaffoldear). cmd nil.
//   - KeyBackspace: saca el ULTIMO RUNE (no byte, seguro con UTF-8); si el
//     buffer esta vacio, sin cambios.
//   - KeyRunes: appendea string(key.Runes) a ScaffoldInput. NO valida kebab-case
//     (lo hace el CLI Python del lado del shell-out; un nombre invalido llega
//     como ScaffoldMsg de error via scaffoldDoneMsg).
//   - cualquier otra tecla (flechas, tab, etc.): sin cambios.
func handleScaffoldKey(m Model, key tea.KeyMsg) (Model, tea.Cmd) {
	switch key.Type {
	case tea.KeyEsc:
		m.Scaffolding = false
		m.ScaffoldInput = ""
		return m, nil
	case tea.KeyEnter:
		m.Scaffolding = false
		// ScaffoldInput se CONSERVA: el wiring en program.Update lo lee para
		// disparar loadScaffold. cmd nil (la funcion pura no shellea).
		return m, nil
	case tea.KeyBackspace:
		if m.ScaffoldInput != "" {
			runes := []rune(m.ScaffoldInput)
			m.ScaffoldInput = string(runes[:len(runes)-1])
		}
		return m, nil
	case tea.KeyRunes:
		m.ScaffoldInput += string(key.Runes)
		return m, nil
	default:
		return m, nil
	}
}

// View renderiza la Model a un string. Pura, sin I/O. Precedencia: quitting >
// scaffolding > (segun ViewMode) error > loading > resumen, y la linea de ayuda
// al final (salvo en quitting y scaffolding, que devuelven vistas propias).
// ViewMode == "contracts" usa los campos de contracts; cualquier otro valor
// (incluido el zero-value "") usa los de gates (default historico).
//
// El cuerpo de cada vista es el mismo formato que ya usaba View para gates,
// aplicado a los campos que correspondan: "error: <err>\n" / "cargando
// gates...\n" (o "cargando contratos...\n" para contracts) / "<resumen>\n". A
// eso se le agrega la linea de ayuda helpLine al final (un \n + el literal).
// Cuando m.Quitting es true devuelve "" (precedencia sobre todo, sin ayuda).
// Cuando m.Scaffolding es true devuelve el prompt de input (sin ayuda, sin
// newline final). Si m.ScaffoldMsg != "" (vista normal), se agrega una linea
// "\n" + ScaffoldMsg ANTES de helpLine.
func View(m Model) string {
	if m.Quitting {
		return ""
	}
	if m.Scaffolding {
		// Modo input: reemplaza TODO lo demas. Sin trailing newline
		// (consistente con kdd.Summarize/SummarizeContractsStatus).
		return "nuevo contrato (kebab-case), enter confirma, esc cancela:\n> " + m.ScaffoldInput
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
	if m.ScaffoldMsg != "" {
		body += "\n" + m.ScaffoldMsg
	}
	return body + helpLine
}