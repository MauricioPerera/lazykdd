package ui

import (
	"fmt"
	"strings"

	tea "github.com/charmbracelet/bubbletea"

	"github.com/MauricioPerera/lazykdd/tui/internal/kdd"
)

// Model es el estado de la capa interactiva de la Piel 3: dos "screens" que el
// usuario alterna con teclas - la vista de gates (la que ya existia) y la vista
// de contratos (nueva, via contracts status --json) - mas un modo de
// scaffolding interactivo (tecla "n") para crear contratos nuevos sin salir de
// la TUI. La vista de contratos ademas es una LISTA NAVEGABLE: flechas
// arriba/abajo mueven un cursor, Enter sobre un contrato muestra su contenido
// COMPLETO (el .md real, leido de disco por el wiring), Esc vuelve a la lista.
// Arquitectura Elm: la logica pura (UpdateModel/View, aqui, testeable, target
// del contrato CCDD) va SEPARADA del wiring de I/O real (el wrapper tea.Model
// en program.go, glue, no testeado, mismo criterio que main.go).
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
	// Se sigue poblando (program.go llama a SummarizeContractsStatus) para
	// mantener paridad con la carga, PERO View ya NO lo renderiza: la lista se
	// arma desde ContractItems (navegable). Se conserva por compatibilidad y
	// porque el oraculo congelado lo verifica.
	Contracts string
	// ContractsErr es el error de contracts status o del shell-out; nil si ok.
	ContractsErr error
	// ContractsLoading es true hasta que llega contractsLoadedMsg.
	ContractsLoading bool
	// ContractItems es la lista estructurada (kdd.ContractStatus) que alimenta
	// la lista navegable. Lo pobla contractsLoadedMsg (program.go llama a
	// kdd.ParseContractsStatus sobre el mismo stdout que SummarizeContractsStatus).
	ContractItems []kdd.ContractStatus
	// SelectedIndex es el cursor (0-based) sobre ContractItems. Lo clampea
	// handleContractsLoaded si la lista se achica y queda fuera de rango.
	SelectedIndex int
	// --- detalle de contrato (nuevo) ---
	// ViewingDetail es true mientras se muestra el contenido de un contrato
	// (tras Enter); false mirando la lista. Esc lo vuelve a false.
	ViewingDetail bool
	// Detail es el contenido del .md leido de disco por loadDetail; "" si no
	// cargo aun o si se salio del detalle.
	Detail string
	// DetailErr es el error de loadDetail (ej. archivo inexistente); nil si ok.
	DetailErr error
	// DetailLoading es true desde el Enter que abre el detalle hasta que llega
	// contractDetailMsg con el contenido.
	DetailLoading bool
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
// paralelo con gatesLoadedMsg via tea.Batch). items es la lista estructurada
// (kdd.ParseContractsStatus sobre el mismo stdout que summary); el TUI la usa
// para la lista navegable.
type contractsLoadedMsg struct {
	summary string
	items   []kdd.ContractStatus
	err     error
}

// contractDetailMsg es el mensaje propio que llega cuando termina de leer de
// disco el .md de un contrato (producido por loadDetail del wrapper en
// program.go, disparado por Enter sobre la lista de contratos). content es el
// archivo completo; err es el error de os.ReadFile (ej. contrato inexistente).
type contractDetailMsg struct {
	content string
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

// helpLine es la linea de ayuda que View agrega SIEMPRE al final de la vista
// normal (salvo quitting / scaffolding / detalle, que devuelven vistas propias).
// Literal exacto exigido por el contrato. DECISION (documentada en el REPORT):
// NO se le agrega el hint de navegacion opcional que sugeria la spec, para
// mantener helpLine byte-identico al comportamiento previo (menos churn del
// oraculo) y el .go ASCII-clean (el repo mantiene los .go sin no-ASCII por
// convencion). La navegacion flechas+enter+esc es estandar.
const helpLine = "\n[g]ates [c]ontracts [r]efresh [n]ew [q]uit"

// detailHelpLine es la linea de ayuda DISTINTA que View agrega al final de la
// vista de detalle (mientras se ve el contenido de un contrato). Literal
// exacto exigido por el contrato.
const detailHelpLine = "\n[esc] volver"

// UpdateModel es la funcion pura que gobierna este contrato: dada una Model y
// un tea.Msg, devuelve la nueva Model y un tea.Cmd. Sin I/O, sin red, sin
// goroutines, sin llamar a Bubble Tea real mas alla de sus TIPOS (tea.KeyMsg,
// tea.Quit). Nunca paniquea: usa type switch con default (no type assertion sin
// ", ok").
//
// DELGADA (dispatcher): un type-switch corto delega TODO el trabajo real a
// handlers separadas (handleGatesLoaded/handleContractsLoaded/handleContractDetail/
// handleScaffoldDone/handleKey), cada una chica y facil de razonar/testear por
// separado (mismo patron que handleScaffoldKey, ya extraido en la tarea
// anterior). El gate SOLO mide UpdateModel (target via signature); los handlers
// son helpers sin contrato propio. La complejidad real vive en los handlers,
// no en UpdateModel - ese es el punto del refactor (ver trade-offs en el REPORT).
func UpdateModel(m Model, msg tea.Msg) (Model, tea.Cmd) {
	switch msg := msg.(type) {
	case gatesLoadedMsg:
		return handleGatesLoaded(m, msg), nil
	case contractsLoadedMsg:
		return handleContractsLoaded(m, msg), nil
	case contractDetailMsg:
		return handleContractDetail(m, msg), nil
	case scaffoldDoneMsg:
		return handleScaffoldDone(m, msg), nil
	case tea.KeyMsg:
		return handleKey(m, msg)
	default:
		return m, nil
	}
}

// handleGatesLoaded setea Summary/Err, baja Loading. El resto del Model se
// preserva del entrante. Comportamiento historico, sin cambios.
func handleGatesLoaded(m Model, msg gatesLoadedMsg) Model {
	m.Summary = msg.summary
	m.Err = msg.err
	m.Loading = false
	return m
}

// handleContractsLoaded setea Contracts/ContractsErr, baja ContractsLoading, y
// ADEMAS setea ContractItems desde msg.items. Clampea SelectedIndex si quedo
// fuera de rango tras la carga (ej. la lista se achico): a len(items)-1, o 0
// si la lista quedo vacia. El resto del Model (gates, ViewMode, Quitting) se
// preserva.
func handleContractsLoaded(m Model, msg contractsLoadedMsg) Model {
	m.Contracts = msg.summary
	m.ContractsErr = msg.err
	m.ContractsLoading = false
	m.ContractItems = msg.items
	if len(m.ContractItems) == 0 {
		m.SelectedIndex = 0
	} else if m.SelectedIndex > len(m.ContractItems)-1 {
		m.SelectedIndex = len(m.ContractItems) - 1
	}
	return m
}

// handleContractDetail setea Detail/DetailErr, baja DetailLoading. ViewingDetail
// YA era true desde el Enter que abrio el detalle; no se toca aca.
func handleContractDetail(m Model, msg contractDetailMsg) Model {
	m.Detail = msg.content
	m.DetailErr = msg.err
	m.DetailLoading = false
	return m
}

// handleScaffoldDone setea ScaffoldMsg al formato exacto ("creado: <path>" o
// "error: <err>"). Scaffolding ya era false (se apago al apretar Enter);
// ScaffoldInput NO se limpia (se pisa la proxima vez que se entra con "n").
func handleScaffoldDone(m Model, msg scaffoldDoneMsg) Model {
	if msg.err != nil {
		m.ScaffoldMsg = "error: " + msg.err.Error()
	} else {
		m.ScaffoldMsg = "creado: " + msg.path
	}
	return m
}

// handleKey despacha las teclas segun el modo: scaffolding (modo input,
// precedencia sobre TODO) > viewingDetail (detalle, solo Esc) > lista/normal.
// Cada modo delega a su propio handler, manteniendo handleKey chica.
func handleKey(m Model, msg tea.KeyMsg) (Model, tea.Cmd) {
	if m.Scaffolding {
		return handleScaffoldKey(m, msg)
	}
	if m.ViewingDetail {
		return handleDetailKey(m, msg)
	}
	return handleListKey(m, msg)
}

// handleDetailKey maneja las teclas mientras se ve el detalle de un contrato.
// Esc vuelve a la lista (ViewingDetail false, Detail/DetailErr limpios);
// SelectedIndex se PRESERVA (el cursor no se mueve al salir del detalle).
// CUALQUIER otra tecla (incluidas "g"/"c"/"r"/"n"/"q") NO hace nada: decision
// de UX explicita, evita que "q" salga del programa entero cuando el usuario
// solo quiere volver atras; el usuario debe apretar Esc primero.
func handleDetailKey(m Model, msg tea.KeyMsg) (Model, tea.Cmd) {
	if msg.Type == tea.KeyEsc {
		m.ViewingDetail = false
		m.Detail = ""
		m.DetailErr = nil
		return m, nil
	}
	return m, nil
}

// handleListKey maneja las teclas en modo lista/normal (no scaffolding, no
// detalle). Las flechas y Enter NAVEGAN la lista SOLO cuando ViewMode ==
// "contracts"; las teclas de comando ("q"/"ctrl+c"/"g"/"c"/"r"/"n") funcionan
// en AMBAS vistas (gates y contracts) igual que antes - esta tarea no les
// cambia el comportamiento, solo agrega flechas + Enter en la lista de
// contracts.
func handleListKey(m Model, msg tea.KeyMsg) (Model, tea.Cmd) {
	if m.ViewMode == "contracts" {
		switch msg.Type {
		case tea.KeyUp:
			if m.SelectedIndex > 0 {
				m.SelectedIndex--
			}
			return m, nil
		case tea.KeyDown:
			if len(m.ContractItems) > 0 && m.SelectedIndex < len(m.ContractItems)-1 {
				m.SelectedIndex++
			}
			return m, nil
		case tea.KeyEnter:
			if len(m.ContractItems) > 0 {
				m.ViewingDetail = true
				m.DetailLoading = true
				m.Detail = ""
				m.DetailErr = nil
			}
			return m, nil
		}
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
		// errores viejos. El resto (Summary/Contracts/ViewMode/Quitting) se
		// preserva. La funcion pura NO sabe shellear -> cmd nil; el refresh
		// real lo dispara el wiring en program.Update al ver esta misma tecla.
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
}

// handleScaffoldKey maneja las teclas en modo scaffolding (m.Scaffolding true).
// Fue extraida de UpdateModel por presupuesto de complejidad (UpdateModel estaba
// en cyclomatic 8/9 y agregar la logica de input inline la habria excedido). Es
// PURA (sin I/O, sin shellear - el shell-out real lo dispara el wiring en
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

// renderContractList arma el cuerpo de la vista de contracts desde
// ContractItems con un indicador de cursor en la fila SelectedIndex: "> " en
// la fila seleccionada, "  " en las demas. Empieza con el header
// "contracts=<N>" (mismo formato que kdd.SummarizeContractsStatus, para
// familiaridad) seguido de una linea por item "<task>: <lifecycle>" con su
// prefijo de cursor. Las lineas se unen con '\n' SIN trailing newline (View lo
// agrega). Pura, sin I/O.
func renderContractList(m Model) string {
	var sb strings.Builder
	fmt.Fprintf(&sb, "contracts=%d", len(m.ContractItems))
	for i, it := range m.ContractItems {
		if i == m.SelectedIndex {
			fmt.Fprintf(&sb, "\n> %s: %s", it.Task, it.Lifecycle)
		} else {
			fmt.Fprintf(&sb, "\n  %s: %s", it.Task, it.Lifecycle)
		}
	}
	return sb.String()
}

// View renderiza la Model a un string. Pura, sin I/O. Precedencia (de mayor a
// menor): Quitting (devuelve "") > Scaffolding (prompt propio) > ViewingDetail
// (vista de detalle, propia) > vista normal (gates/contracts segun ViewMode,
// con helpLine). En la vista normal de contracts se RENDERIZA la lista desde
// ContractItems con cursor (no el string plano Contracts); mantiene la
// precedencia error > loading > lista que ya existia (usa ContractsErr /
// ContractsLoading). Si ScaffoldMsg != "" se agrega una linea extra antes de
// helpLine (solo en vista normal, no en detalle).
func View(m Model) string {
	if m.Quitting {
		return ""
	}
	if m.Scaffolding {
		// Modo input: reemplaza TODO lo demas. Sin trailing newline
		// (consistente con kdd.Summarize/SummarizeContractsStatus).
		return "nuevo contrato (kebab-case), enter confirma, esc cancela:\n> " + m.ScaffoldInput
	}
	if m.ViewingDetail {
		return viewDetail(m)
	}
	var body string
	if m.ViewMode == "contracts" {
		switch {
		case m.ContractsErr != nil:
			body = "error: " + m.ContractsErr.Error() + "\n"
		case m.ContractsLoading:
			body = "cargando contratos...\n"
		default:
			body = renderContractList(m) + "\n"
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

// viewDetail arma la vista de detalle de un contrato. Precedencia: DetailErr
// (-> "error: <err>") > DetailLoading (-> "cargando contrato...\n") > contenido
// del .md tal cual + la linea de ayuda propia "[esc] volver". El contenido NO
// se modifica (el .md crudo, tal cual lo leyo loadDetail). Sin helpLine normal.
// LIMITACION ACEPTADA (tarea futura): sin viewport/scroll - si el .md es mas
// largo que la terminal, Bubble Tea truncaria o desbordaria. No se agrega
// bubbles/viewport en esta tarea (fuera de alcance, documentado en el REPORT).
func viewDetail(m Model) string {
	switch {
	case m.DetailErr != nil:
		return "error: " + m.DetailErr.Error()
	case m.DetailLoading:
		return "cargando contrato...\n"
	default:
		return m.Detail + detailHelpLine
	}
}