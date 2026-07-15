package ui

import (
	"bytes"
	"encoding/json"
	"fmt"
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

// loadScaffold shellea `contracts scaffold <name> --json` y devuelve un
// scaffoldDoneMsg con el path creado (o el error). Mismo patron os/exec que
// loadGates/loadContracts. El CLI devuelve exit 0 con
// `{"created":true,"path":"..."}` o exit 1 con `{"error":"..."}` (nombre no
// kebab-case o contrato ya existente); en ambos caminos se conserva stdout, asi
// que un *exec.ExitError NO es error de shell-out (se parsea stdout igual). El
// JSON se parsea aca directo con encoding/json: es glue, no una funcion pura
// separada (no tiene su propio contrato CCDD). Si el JSON trae `"error"`, se
// envuelve en un error con fmt.Errorf; si trae `"created":true`, err es nil y
// path es el valor de `"path"`.
func (p program) loadScaffold(name string) tea.Cmd {
	return func() tea.Msg {
		cmd := exec.Command("python", "scripts/kdd_cli.py", "contracts", "scaffold", name, "--json")
		var stdout bytes.Buffer
		cmd.Stdout = &stdout
		cmd.Stderr = os.Stderr
		if err := cmd.Run(); err != nil {
			if _, ok := err.(*exec.ExitError); !ok {
				return scaffoldDoneMsg{path: "", err: err}
			}
		}
		var res struct {
			Created bool   `json:"created"`
			Path    string `json:"path"`
			Error   string `json:"error"`
		}
		if err := json.Unmarshal(stdout.Bytes(), &res); err != nil {
			return scaffoldDoneMsg{path: "", err: err}
		}
		if res.Error != "" {
			return scaffoldDoneMsg{path: "", err: fmt.Errorf("%s", res.Error)}
		}
		return scaffoldDoneMsg{path: res.Path, err: nil}
	}
}

// Update delega a la logica pura UpdateModel y envuelve la nueva Model de
// vuelta en el wrapper tea.Model. Despues de delegar, el wiring detecta DOS
// casos puntuales mirando el msg Y el Model ENTRANTE (antes de la delegacion):
//
//  1. Enter que confirma el input: si msg es tea.KeyMsg con Type == KeyEnter Y
//     el Model entrante tenia Scaffolding == true Y ScaffoldInput no vacio, el
//     tea.Cmd que devuelve Update es loadScaffold(input) (NO el nil que devolvio
//     UpdateModel, que es pura y no shellea). Un Enter con buffer vacio NO
//     dispara nada (ahorra un shell-out inutil), pero el modo input igual se
//     cierra (comportamiento ya fijado por UpdateModel).
//
//  2. "r" (refresh): si msg es tea.KeyMsg con String() == "r" Y el Model
//     entrante NO estaba en scaffolding (en modo input "r" es texto, no
//     comando), el tea.Cmd es tea.Batch(loadGates, loadContracts) (mismo patron
//     que Init). UpdateModel ya reseteo Loading/ContractsLoading y limpio
//     errores.
//
// Para cualquier otro msg, el cmd es el que devolvio UpdateModel, sin cambios.
// Limitacion conocida (primera version): no hay cancelacion ni IDs de peticion,
// asi que varios "r" apretados seguidos pueden cruzar respuestas viejas con
// nuevas (carreras) -- aceptado, documentado. Tampoco se auto-refresca el panel
// de contracts despues de un scaffold exitoso (queda para una tarea futura; el
// usuario puede apretar "r" a mano).
func (p program) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	wasScaffolding := p.Model.Scaffolding
	input := p.Model.ScaffoldInput
	newModel, cmd := UpdateModel(p.Model, msg)
	next := program{Model: newModel}
	if key, ok := msg.(tea.KeyMsg); ok && key.Type == tea.KeyEnter && wasScaffolding && input != "" {
		return next, next.loadScaffold(input)
	}
	if key, ok := msg.(tea.KeyMsg); ok && !wasScaffolding && key.String() == "r" {
		return next, tea.Batch(next.loadGates(), next.loadContracts())
	}
	return next, cmd
}

// View delega a la View pura.
func (p program) View() string {
	return View(p.Model)
}