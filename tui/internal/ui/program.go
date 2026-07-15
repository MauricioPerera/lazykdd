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
// Loading (sin resumen aun). Exportado porque main.go (package main) lo usa.
func NewProgram() tea.Model {
	return program{Model: Model{Loading: true}}
}

// Init lanza la carga del resumen de gates como un tea.Cmd (una funcion
// func() tea.Msg). Shellea al CLI Python con el mismo patron de os/exec que
// main.go (path relativo scripts/kdd_cli.py, asume cwd = repo root) y envuelve
// el stdout en kdd.Summarize. Un *exec.ExitError (proceso corrio pero salio != 0
// p.ej. gates fallando -> overall_ok=false) NO es error de shell-out: se
// conserva stdout y se resume igual; solo falla si no arranca el proceso.
func (p program) Init() tea.Cmd {
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