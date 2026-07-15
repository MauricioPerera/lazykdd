package kdd

import (
	"encoding/json"
	"fmt"
	"sort"
	"strings"
)

// Summarize parsea el JSON crudo que emite `python scripts/kdd_cli.py gates
// run-all --json` (un objeto con "overall_ok": bool y "results": map de
// nombre de gate a su {exit_code, stdout, stderr}) y arma un resumen
// determinista de una sola pieza:
//
//	overall_ok=<true|false> pass=<N> fail=<M>
//	[PASS] <nombre_gate>
//	[FAIL] <nombre_gate>
//	...
//
// Los gates se listan en orden alfabetico (un map de Go no itera en orden
// estable). Las lineas se unen con '\n' SIN trailing newline. Un "results"
// vacio ({}) es valido: solo el header, sin lineas de gate.
//
// Devuelve ("", err) si data no es JSON valido o no matchea la forma
// esperada (falta "overall_ok" o "results", o "results" no es un objeto).
// La funcion es pura: sin I/O, sin red, sin os.Exit, nunca paniquea.
func Summarize(data []byte) (string, error) {
	// Primer pasada: objeto top-level como claves crudas para detectar
	// presencia de "overall_ok" y "results" y validar que "results" sea un
	// objeto (unmarshal sobre map rechaza arrays/strings/numeros).
	var top map[string]json.RawMessage
	if err := json.Unmarshal(data, &top); err != nil {
		return "", err
	}
	if _, ok := top["overall_ok"]; !ok {
		return "", fmt.Errorf("missing key: overall_ok")
	}
	rawResults, ok := top["results"]
	if !ok {
		return "", fmt.Errorf("missing key: results")
	}
	var overallOK bool
	if err := json.Unmarshal(top["overall_ok"], &overallOK); err != nil {
		return "", fmt.Errorf("overall_ok: %w", err)
	}
	var results map[string]json.RawMessage
	if err := json.Unmarshal(rawResults, &results); err != nil {
		return "", fmt.Errorf("results: %w", err)
	}
	// Unmarshal de "null" sobre un map deja nil sin error; null no es un
	// objeto -> forma inesperada.
	if results == nil {
		return "", fmt.Errorf("results is null, expected an object")
	}

	names := make([]string, 0, len(results))
	passed := make(map[string]bool, len(results))
	pass, fail := 0, 0
	for name, raw := range results {
		var g struct {
			ExitCode int `json:"exit_code"`
		}
		if err := json.Unmarshal(raw, &g); err != nil {
			return "", fmt.Errorf("gate %q: %w", name, err)
		}
		names = append(names, name)
		if g.ExitCode == 0 {
			pass++
			passed[name] = true
		} else {
			fail++
			passed[name] = false
		}
	}
	sort.Strings(names)

	var sb strings.Builder
	fmt.Fprintf(&sb, "overall_ok=%v pass=%d fail=%d", overallOK, pass, fail)
	for _, name := range names {
		if passed[name] {
			fmt.Fprintf(&sb, "\n[PASS] %s", name)
		} else {
			fmt.Fprintf(&sb, "\n[FAIL] %s", name)
		}
	}
	return sb.String(), nil
}