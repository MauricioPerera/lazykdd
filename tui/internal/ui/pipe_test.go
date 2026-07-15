package ui

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// Este archivo NO es parte del oraculo congelado (tests_sha256 sella solo a
// model_test.go). Es el test ADICIONAL del punto 6b del HECHO: ejercita los
// tea.Cmd reales devueltos por loadGates()/loadContracts() del wrapper
// llamandolos como funciones, lo que shellea a python de verdad. Es la unica
// forma de probar los pipes end-to-end sin lanzar la TUI completa.
//
// Por que es OPT-IN (se saltea por defecto):
//  1. HECHO punto 2 exige que `go test ./...` (default) sea 100% Go puro, sin
//     shellear nada real. Si este test corriese por defecto, violaria eso.
//  2. Recursion: `go test -C tui ./...` es el test_command de este contrato, y
//     `gates run-all` (lo que shellea loadGates) corre validate_test_commands,
//     que corre `go test -C tui ./...` otra vez -> recursion infinita. Al
//     saltearlo por defecto, el gate validate_test_commands pasa sin colgarse.
//     `contracts status --json` (lo que shellea loadContracts) NO dispara go
//     test por si solo, pero vive en el mismo binario de test, asi que el
//     mismo opt-in lo cubre.
//
// Para correrlo de verdad (HECHO 6b/7b):
//
//	LAZYKDD_RUN_PIPE=1 go test -C tui -run TestInitPipeline -v ./internal/ui/
//
// (documentado en el REPORT; el env var es la unica desviacion del literal
// `go test -run <nombre> -v` del prompt, forzada por 1 y 2 arriba).
//
// NOTA: Init() ahora devuelve tea.Batch(loadGates(), loadContracts()); llamar a
// ese batch como funcion directa no entrega los gatesLoadedMsg/contractsLoadedMsg
// individuales (la concurrencia la resuelve el runtime de Bubble Tea, no una
// llamada sincronica). Por eso estos tests llaman a loadGates()/loadContracts()
// directamente: son metodos no exportados del wrapper, pero el test vive en el
// MISMO paquete `ui`, asi que tiene acceso. Cada uno shellea a python de verdad.

// chdirRepoRoot ubica la raiz del repo caminando hacia arriba hasta encontrar
// scripts/kdd_cli.py y hace chdir ahi. loadGates()/loadContracts() shellean
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

// maybeSkipPipe consume el flag opt-in y hace chdir al repo root. Centraliza el
// preambulo comun a ambos tests de pipe.
func maybeSkipPipe(t *testing.T) {
	t.Helper()
	orig := os.Getenv("LAZYKDD_RUN_PIPE")
	if orig == "" {
		t.Skip("skipping real python shell-out; set LAZYKDD_RUN_PIPE=1 to run (keep default go test pure + avoid validate_test_commands recursion)")
	}
	// CONSUMIR el flag antes de shellerar: sin esto, el env var se propaga al
	// `go test` anidado que dispara validate_test_commands (dentro del
	// gates run-all que shelleamos abajo), y ese go test correria este mismo
	// test de nuevo -> recursion infinita. Al desactivarlo aca, el go test
	// anidado lo ve vacio -> t.Skip -> recursion rota en profundidad 1.
	//
	// Se RESTAURA al final del test (t.Cleanup) para que el SIGUIENTE test de
	// pipe del mismo binario vuelva a verlo seteado: sin esto, el primer test
	// que corre deja el env var vacio y los demas salten sin shellerar.
	os.Unsetenv("LAZYKDD_RUN_PIPE")
	t.Cleanup(func() { os.Setenv("LAZYKDD_RUN_PIPE", orig) })
	chdirRepoRoot(t)
}

// TestInitPipelineGates ejercita el tea.Cmd real devuelto por loadGates() del
// wrapper llamandolo directamente como funcion. Verifica que el gatesLoadedMsg
// resultante tiene err == nil y summary no vacio conteniendo "overall_ok=".
func TestInitPipelineGates(t *testing.T) {
	maybeSkipPipe(t)
	p := program{Model: Model{Loading: true, ContractsLoading: true}}
	cmd := p.loadGates()
	if cmd == nil {
		t.Fatalf("loadGates() returned nil cmd")
	}
	msg := cmd()
	loaded, ok := msg.(gatesLoadedMsg)
	if !ok {
		t.Fatalf("cmd() should return gatesLoadedMsg, got %T", msg)
	}
	if loaded.err != nil {
		t.Fatalf("expected nil err from gates pipeline, got %v", loaded.err)
	}
	if loaded.summary == "" {
		t.Fatalf("expected non-empty gates summary")
	}
	if !strings.Contains(loaded.summary, "overall_ok=") {
		t.Fatalf("gates summary should contain overall_ok=, got %q", loaded.summary)
	}
}

// TestInitPipelineContracts ejercita el tea.Cmd real devuelto por loadContracts()
// del wrapper llamandolo directamente como funcion. Verifica que el
// contractsLoadedMsg resultante tiene err == nil y summary conteniendo
// "contracts=".
func TestInitPipelineContracts(t *testing.T) {
	maybeSkipPipe(t)
	p := program{Model: Model{Loading: true, ContractsLoading: true}}
	cmd := p.loadContracts()
	if cmd == nil {
		t.Fatalf("loadContracts() returned nil cmd")
	}
	msg := cmd()
	loaded, ok := msg.(contractsLoadedMsg)
	if !ok {
		t.Fatalf("cmd() should return contractsLoadedMsg, got %T", msg)
	}
	if loaded.err != nil {
		t.Fatalf("expected nil err from contracts pipeline, got %v", loaded.err)
	}
	if loaded.summary == "" {
		t.Fatalf("expected non-empty contracts summary")
	}
	if !strings.Contains(loaded.summary, "contracts=") {
		t.Fatalf("contracts summary should contain contracts=, got %q", loaded.summary)
	}
}

// TestInitPipelineScaffold ejercita el tea.Cmd real devuelto por loadScaffold()
// del wrapper llamandolo directamente como funcion. shellea `contracts scaffold
// <name> --json` de verdad, que ESCRIBE un archivo nuevo en
// knowledge/contracts/ del repo real -- por eso este test es opt-in y usa un
// nombre DESCARTABLE que no colisiona con contratos reales. Verifica que el
// scaffoldDoneMsg resultante tiene err == nil y path no vacio, y que el archivo
// existe en disco. BORRA el archivo al final (t.Cleanup, registrado ANTES de
// shellerar para que corra incluso si el test falla a mitad de camino). NUNCA
// deja ese archivo en el repo: se verifica con `git status --short` al final de
// la tarea. Nota: a diferencia de loadGates, scaffold NO dispara go test (solo
// crea un archivo desde la plantilla), asi que NO hay recursion con
// validate_test_commands -- igual se usa maybeSkipPipe para el chdir al repo
// root (el CLI escribe a knowledge/contracts/ relativo al cwd).
func TestInitPipelineScaffold(t *testing.T) {
	maybeSkipPipe(t)
	const name = "zz-pipe-test-scaffold-tmp"
	// Path esperado relativo al repo root (maybeSkipPipe ya hizo chdir ahi).
	// Se registra el Cleanup ANTES de shellerar: corre incluso si el test
	// falla despues de que el archivo fue creado.
	expectedPath := filepath.Join("knowledge", "contracts", name+".md")
	t.Cleanup(func() { _ = os.Remove(expectedPath) })

	p := program{}
	cmd := p.loadScaffold(name)
	if cmd == nil {
		t.Fatalf("loadScaffold() returned nil cmd")
	}
	msg := cmd()
	done, ok := msg.(scaffoldDoneMsg)
	if !ok {
		t.Fatalf("cmd() should return scaffoldDoneMsg, got %T", msg)
	}
	if done.err != nil {
		t.Fatalf("expected nil err from scaffold pipeline, got %v", done.err)
	}
	if done.path == "" {
		t.Fatalf("expected non-empty path from scaffold, got empty (msg=%+v)", done)
	}
	if _, err := os.Stat(done.path); err != nil {
		t.Fatalf("scaffolded file should exist at %s: %v", done.path, err)
	}
}