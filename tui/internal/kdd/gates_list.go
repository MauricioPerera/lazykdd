package kdd

import (
	"encoding/json"
	"errors"
	"fmt"
	"sort"
)

// GateResult es una entrada estructurada del JSON de `gates run-all --json`: el
// nombre del gate y su exit_code (0 = pass, !=0 = fail). Lo pobla
// ParseGatesResults para alimentar la lista navegable del panel de GATES del
// TUI (tui/internal/ui/model.go).
type GateResult struct {
	Name     string
	ExitCode int
}

// ParseGatesResults parsea el JSON crudo que emite `python scripts/kdd_cli.py
// gates run-all --json` (un objeto con "overall_ok": bool y "results": map de
// nombre de gate a su {exit_code, stdout, stderr}) y devuelve los datos
// ESTRUCTURADOS: el bool overall_ok y un slice de GateResult ordenado
// alfabeticamente por Name.
//
// Es la variante estructurada de Summarize (que devuelve un string formateado):
// mismo parseo/validacion, mismo orden defensivo, mismo results-vacio-es-valido.
// El TUI la usa para armar la lista navegable del panel de GATES (cursor,
// Enter -> gates run <name> --json) en tui/internal/ui/model.go.
//
// Devuelve (false, nil, err) si data no es JSON valido, no matchea la forma
// esperada (falta "overall_ok" o "results", "results" no es un objeto o es
// null, "overall_ok" de tipo equivocado, top-level no objeto). Un "results"
// vacio ({}) es valido: items vacio (slice de longitud 0, no nil), overallOK
// tal cual, error nil.
//
// Pura: sin I/O, sin red, sin os.Exit, nunca paniquea.
//
// TRADE-OFF (documentado en el REPORT): la logica de parseo/validacion esta
// DUPLICADA de Summarize en gates.go. No se extrajo un parser interno comun
// porque [ARCHIVOS] prohíbe tocar gates.go (ni su contrato sellado); refactorizar
// Summarize para llamar a un helper compartido cambiaria sus internals y
// exigiria re-sellar su contrato, fuera de alcance. Duplicar ~40 lineas de
// validacion defensiva es mas barato que el acoplamiento cross-archivo. Mismo
// criterio que kdd-contracts-list-parse.md duplico de SummarizeContractsStatus.
func ParseGatesResults(data []byte) (overallOK bool, items []GateResult, err error) {
	// Primer pasada: objeto top-level como claves crudas para detectar
	// presencia de "overall_ok" y "results" y validar que "results" sea un
	// objeto (unmarshal sobre map rechaza arrays/strings/numeros).
	var top map[string]json.RawMessage
	if err := json.Unmarshal(data, &top); err != nil {
		return false, nil, err
	}
	if _, ok := top["overall_ok"]; !ok {
		return false, nil, fmt.Errorf("missing key: overall_ok")
	}
	rawResults, ok := top["results"]
	if !ok {
		return false, nil, fmt.Errorf("missing key: results")
	}
	var okBool bool
	if err := json.Unmarshal(top["overall_ok"], &okBool); err != nil {
		return false, nil, fmt.Errorf("overall_ok: %w", err)
	}
	var results map[string]json.RawMessage
	if err := json.Unmarshal(rawResults, &results); err != nil {
		return false, nil, fmt.Errorf("results: %w", err)
	}
	// Unmarshal de "null" sobre un map deja nil sin error; null no es un
	// objeto -> forma inesperada.
	if results == nil {
		return false, nil, fmt.Errorf("results is null, expected an object")
	}

	names := make([]string, 0, len(results))
	for name, raw := range results {
		var g struct {
			ExitCode int `json:"exit_code"`
		}
		if err := json.Unmarshal(raw, &g); err != nil {
			return false, nil, fmt.Errorf("gate %q: %w", name, err)
		}
		names = append(names, name)
	}
	sort.Strings(names)

	out := make([]GateResult, 0, len(names))
	for _, name := range names {
		var g struct {
			ExitCode int `json:"exit_code"`
		}
		// Se repite el unmarshal sobre el raw del nombre: ya validamos arriba
		// que parsea, asi que este no puede fallar; lo hacemos aca para leer el
		// exit_code en orden alfabetico sin un map paralelo.
		_ = json.Unmarshal(results[name], &g)
		out = append(out, GateResult{Name: name, ExitCode: g.ExitCode})
	}
	return okBool, out, nil
}

// SummarizeGateDetail parsea el JSON crudo que emite `python scripts/kdd_cli.py
// gates run <name> --json` (UN gate individual, no los 11 juntos) y arma un
// string legible con su exit_code, stdout y stderr — o un error si el CLI
// devolvio la forma de error.
//
// El JSON es uno de dos formas:
//   - {"exit_code": int, "stdout": string, "stderr": string}  (gate corrido)
//   - {"error": string}  (nombre de gate invalido, etc.)
//
// Si la clave "error" esta presente: devuelve ("", errors.New(<valor>)), donde
// el valor se decodifica como string (null -> "").
//
// Si la clave "exit_code" esta presente (y no "error"): arma el string EXACTO
//
//	exit_code=<N>
//	--- stdout ---
//	<stdout>
//	--- stderr ---
//	<stderr>
//
// stdout/stderr se decodifican como string, default "" si ausentes. Sin
// trailing newline extra mas alla del que ya traiga stderr (el formato deja
// siempre un '\n' tras el label "--- stderr ---" y luego el contenido de stderr
// tal cual; si stderr es "" el string termina en "--- stderr ---\n").
//
// JSON invalido o sin ninguna de las 2 formas esperadas -> ("", err).
// Pura: sin I/O, sin red, sin os.Exit, nunca paniquea.
func SummarizeGateDetail(data []byte) (string, error) {
	var top map[string]json.RawMessage
	if err := json.Unmarshal(data, &top); err != nil {
		return "", err
	}
	// Unmarshal de "null" sobre un map deja nil sin error; null no es un
	// objeto -> forma inesperada.
	if top == nil {
		return "", fmt.Errorf("top-level is null, expected an object")
	}
	// Forma de error: clave "error" presente. Tiene precedencia sobre
	// "exit_code" (no deberian coexistir; si lo hacen, gana "error").
	if errRaw, ok := top["error"]; ok {
		var errPtr *string
		if err := json.Unmarshal(errRaw, &errPtr); err != nil {
			return "", fmt.Errorf("error: %w", err)
		}
		val := ""
		if errPtr != nil {
			val = *errPtr
		}
		return "", errors.New(val)
	}
	// Forma exitosa: clave "exit_code" presente.
	exitRaw, ok := top["exit_code"]
	if !ok {
		return "", fmt.Errorf("missing key: exit_code or error")
	}
	var exitCode int
	if err := json.Unmarshal(exitRaw, &exitCode); err != nil {
		return "", fmt.Errorf("exit_code: %w", err)
	}
	var stdout, stderr string
	// stdout/stderr ausentes -> "" (default de Go); null -> "" tambien (unmarshal
	// de null sobre string deja "" sin error, aceptable aca).
	if r, ok := top["stdout"]; ok {
		_ = json.Unmarshal(r, &stdout)
	}
	if r, ok := top["stderr"]; ok {
		_ = json.Unmarshal(r, &stderr)
	}
	return fmt.Sprintf("exit_code=%d\n--- stdout ---\n%s\n--- stderr ---\n%s", exitCode, stdout, stderr), nil
}