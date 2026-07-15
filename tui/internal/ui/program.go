package ui

import (
	"bytes"
	"os"
	"os/exec"

	tea "github.com/charmbracelet/bubbletea"

	"github.com/MauricioPerera/lazykdd/tui/internal/kdd"
)

// program (lowercase, no exportado) es el WRAPPER que implementa la interfaz
// real tea.Model delegando a UpdateModel/View de model.go. Es WIRING (glue):
// NO esta cubierto por el oraculo congelado, mismo criterio que main.go.
type program struct {
	Model
}

// NewProgram devuelve el tea.Model inicial listo para tea.NewProgram: estado
// Loading (gates) y ContractsLoading (contracts), sin resumenes aun. La
// primera vista renderiza gates (ViewMode queda en zero-value "", que View
// trata como "gates"). Exportado porque main.go (package main) lo usa.
func NewProgram() tea.Model {
	return program{Model: Model{Loading: true, ContractsLoading: true}}
}

// Init lanza AMBAS cargas (gates y contracts) en paralelo con tea.Batch: dos
// tea.Cmd (func() tea.Msg) que shellean al CLI Python con el mismo patron de
// os/exec que main.go (path relativo scripts/kdd_cli.py, asume cwd = repo root)
// y envuelven el stdout en kdd.Summarize / kdd.SummarizeContractsStatus. Un
// *exec.ExitError (proceso corrio pero salio != 0, p.ej. gates fallando ->
// overall_ok=false) NO es error de shell-out: se conserva stdout y se resume
// igual; solo falla si no arranca el proceso. Para `contracts status --json`
// ver [kdd-contracts-status-json](../../knowledge/contracts/kdd-contracts-status-json.md):
// exit 0 para lista (incluida vacia), exit 1 solo si el directorio de
// contratos no existe (no ocurre en el repo real); ambos caminos conservan
// stdout, asi que el manejo de *exec.ExitError es identico al de gates.
func (p program) Init() tea.Cmd {
	return tea.Batch(p.loadGates(), p.loadContracts())
}

// loadGates shellea `gates run-all --json` y devuelve un gatesLoadedMsg con el
// resumen (o el error de arranque del proceso).
func (p program) loadGates() tea.Cmd {
	return func() tea.Msg {
		cmd := exec.Command("python", "scripts/kdd_cli.py", "gates", "run-all", "--json")
		var stdout bytes.Buffer
		cmd.Stdout = &stdout
		cmd.Stderr = os.Stderr
		if err := cmd.Run(); err != nil {
			if _, ok := err.(*exec.ExitError); !ok {
				return gatesLoadedMsg{summary: "", err: err}
			}
		}
		summary, err := kdd.Summarize(stdout.Bytes())
		return gatesLoadedMsg{summary: summary, err: err}
	}
}

// loadContracts shellea `contracts status --json` y devuelve un
// contractsLoadedMsg con el resumen (o el error de arranque del proceso).
func (p program) loadContracts() tea.Cmd {
	return func() tea.Msg {
		cmd := exec.Command("python", "scripts/kdd_cli.py", "contracts", "status", "--json")
		var stdout bytes.Buffer
		cmd.Stdout = &stdout
		cmd.Stderr = os.Stderr
		if err := cmd.Run(); err != nil {
			if _, ok := err.(*exec.ExitError); !ok {
				return contractsLoadedMsg{summary: "", err: err}
			}
		}
		summary, err := kdd.SummarizeContractsStatus(stdout.Bytes())
		return contractsLoadedMsg{summary: summary, err: err}
	}
}

// Update delega a la logica pura UpdateModel y envuelve la nueva Model de
// vuelta en el wrapper tea.Model.
func (p program) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	newModel, cmd := UpdateModel(p.Model, msg)
	return program{Model: newModel}, cmd
}

// View delega a la View pura.
func (p program) View() string {
	return View(p.Model)
}