package main

import (
	"bytes"
	"fmt"
	"os"
	"os/exec"
	"strings"

	"github.com/MauricioPerera/lazykdd/tui/internal/kdd"
)

// main es el wiring minimo de la Piel 3 (TUI Go): shellea al CLI Python ya
// existente, parsea su JSON via kdd.Summarize e imprime el resumen. Sin
// interactividad, sin loop de eventos, sin Bubble Tea (tarea futura).
//
// Asume que el binario se ejecuta desde la RAIZ del repo (cwd = repo root),
// igual que el CLI Python `scripts/kdd_cli.py` (que usa rutas root-relative).
// Resolverlo de forma mas robusta es fuera de alcance de esta tarea.
func main() {
	// 1. corre `python scripts/kdd_cli.py gates run-all --json`.
	cmd := exec.Command("python", "scripts/kdd_cli.py", "gates", "run-all", "--json")
	var stdout bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = os.Stderr
	if err := cmd.Run(); err != nil {
		// 2. falla en arrancar (ejecutable no encontrado, etc.) -> stderr + exit 1.
		// Un *exec.ExitError (proceso corrio pero salio != 0, p.ej. gates
		// fallando -> overall_ok=false) NO aborta: se conserva stdout y se
		// resume igual, decidiendo el exit code por overall_ok abajo.
		if _, ok := err.(*exec.ExitError); !ok {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(1)
		}
	}
	// 3. pasa el stdout capturado a kdd.Summarize.
	summary, err := kdd.Summarize(stdout.Bytes())
	if err != nil {
		// 4. error de parseo -> stderr + exit 1.
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	// 5. imprime el resumen y sale 0 si overall_ok=true, si no 1. Se detecta
	// por el prefijo del header del resumen (sin reparsear JSON ni exportar
	// una funcion extra): el header es "overall_ok=<true|false> ...", asi que
	// "overall_ok=true" es prefijo solo cuando el flag es true.
	fmt.Println(summary)
	if strings.HasPrefix(summary, "overall_ok=true") {
		os.Exit(0)
	}
	os.Exit(1)
}