package main

import (
	"fmt"
	"os"

	tea "github.com/charmbracelet/bubbletea"

	"github.com/MauricioPerera/lazykdd/tui/internal/ui"
)

// main es el wiring minimo de la Piel 3 (TUI Go) en su modo interactivo: lanza
// el programa Bubble Tea (arquitectura Elm en tui/internal/ui) y lo deja correr
// hasta que el usuario sale con 'q' o Ctrl+C. La logica pura (UpdateModel/View)
// y el wrapper tea.Model viven en tui/internal/ui; aca solo el lanzamiento.
//
// Asume que el binario se ejecuta desde la RAIZ del repo (cwd = repo root), igual
// que el CLI Python `scripts/kdd_cli.py` (que usa rutas root-relative) y que el
// Init() del wrapper al shellerar (mismo patron que el main.go previo). El modo
// viejo (imprime y sale, exit-code-refleja-overall_ok) SE PIERDE a cambio de la
// interactividad: un TUI interactivo no tiene un "resultado" que devolver por
// exit code de la misma forma que un comando no-interactivo. Si Run() devuelve
// error, se imprime a stderr y se sale 1; si no, exit 0.
func main() {
	p := tea.NewProgram(ui.NewProgram())
	if _, err := p.Run(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}