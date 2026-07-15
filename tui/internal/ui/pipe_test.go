package ui

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// Este archivo NO es parte del oraculo congelado (tests_sha256 sella solo a
// model_test.go). Es el test ADICIONAL del punto 6b del HECHO: ejercita el
// tea.Cmd real devuelto por Init() del wrapper llamandolo como funcion, lo que
// shellea a python de verdad. Es la unica forma de probar el pipe end-to-end
// sin lanzar la TUI completa.
//
// Por que es OPT-IN (se saltea por defecto):
//  1. HECHO punto 2 exige que `go test ./...` (default) sea 100% Go puro, sin
//     shellear nada real. Si este test corriese por defecto, violaria eso.
//  2. Recursion: `go test -C tui ./...` es el test_command de este contrato, y
//     `gates run-all` (lo que shellea Init()) corre validate_test_commands,
//     que corre `go test -C tui ./...` otra vez -> recursion infinita. Al
//     saltearlo por defecto, el gate validate_test_commands pasa sin colgarse.
//
// Para correrlo de verdad (HECHO 6b):
//
//	LAZYKDD_RUN_PIPE=1 go test -C tui -run TestInitPipelineShellsOutToPython -v ./internal/ui/
//
// (documentado en el REPORT; el env var es la unica desviacion del literal
// `go test -run <nombre> -v` del prompt, forzada por 1 y 2 arriba).

// chdirRepoRoot ubica la raiz del repo caminando hacia arriba hasta encontrar
// scripts/kdd_cli.py y hace chdir ahi. Init() shellea
// `python scripts/kdd_cli.py ...` con path relativo al repo root (mismo patron
// que main.go), y kdd_cli.py usa rutas root-relative, asi que el test necesita
// cwd = repo root. Go corre cada test binario con cwd = directorio del paquete
// (tui/internal/ui/), de ahi la necesidad de ubicar la raiz. Se restaura al
// final (t.Cleanup).
func chdirRepoRoot(t *testing.T) {
	t.Helper()
	dir, err := os.Getwd()
	if err != nil {
		t.Fatalf("getwd: %v", err)
	}
	root := dir
	for {
		if _, err := os.Stat(filepath.Join(root, "scripts", "kdd_cli.py")); err == nil {
			break
		}
		parent := filepath.Dir(root)
		if parent == root {
			t.Fatalf("repo root (scripts/kdd_cli.py) not found walking up from %s", dir)
		}
		root = parent
	}
	orig, err := os.Getwd()
	if err != nil {
		t.Fatalf("getwd orig: %v", err)
	}
	if err := os.Chdir(root); err != nil {
		t.Fatalf("chdir %s: %v", root, err)
	}
	t.Cleanup(func() { _ = os.Chdir(orig) })
}

// TestInitPipelineShellsOutToPython ejercita el tea.Cmd real devuelto por
// Init() del wrapper llamandolo directamente como funcion. Verifica que el
// gatesLoadedMsg resultante tiene err == nil y summary no vacio conteniendo la
// subcadena "overall_ok=".
func TestInitPipelineShellsOutToPython(t *testing.T) {
	if os.Getenv("LAZYKDD_RUN_PIPE") == "" {
		t.Skip("skipping real python shell-out; set LAZYKDD_RUN_PIPE=1 to run (keep default go test pure + avoid validate_test_commands recursion)")
	}
	// CONSUMIR el flag antes de shellerar: sin esto, el env var se propaga al
	// `go test` anidado que dispara validate_test_commands (dentro del
	// gates run-all que shelleamos abajo), y ese go test correria este mismo
	// test de nuevo -> recursion infinita. Al desactivarlo aca, el go test
	// anidado lo ve vacio -> t.Skip -> recursion rota en profundidad 1.
	os.Unsetenv("LAZYKDD_RUN_PIPE")
	chdirRepoRoot(t)

	w := NewProgram()
	cmd := w.Init()
	if cmd == nil {
		t.Fatalf("Init() returned nil cmd")
	}
	msg := cmd()
	loaded, ok := msg.(gatesLoadedMsg)
	if !ok {
		t.Fatalf("cmd() should return gatesLoadedMsg, got %T", msg)
	}
	if loaded.err != nil {
		t.Fatalf("expected nil err from pipeline, got %v", loaded.err)
	}
	if loaded.summary == "" {
		t.Fatalf("expected non-empty summary")
	}
	if !strings.Contains(loaded.summary, "overall_ok=") {
		t.Fatalf("summary should contain overall_ok=, got %q", loaded.summary)
	}
}