package kdd

import "testing"

// TestParseGatesResultsValid cubre los casos de exito de ParseGatesResults: el
// bool overallOK se copia del JSON tal cual, los items se devuelven ordenados
// alfabeticamente por Name (el input viene en orden distinto al esperado), un
// results vacio ({}) es valido (items vacio no nil, sin error), un gate sin
// exit_code se decodifica como 0 (pass), y la mezcla pass/fail queda reflejada
// en ExitCode. Verifica Name y ExitCode exactos de cada item y overallOK.
func TestParseGatesResultsValid(t *testing.T) {
	cases := []struct {
		name       string
		in         string
		wantOK     bool
		wantItems  []GateResult
	}{
		{
			name:   "mixed_pass_fail_alpha_sorted",
			in:     `{"overall_ok": false, "results": {"zeta": {"exit_code": 0, "stdout": "x", "stderr": ""}, "alpha": {"exit_code": 1, "stdout": "", "stderr": "boom"}}}`,
			wantOK: false,
			wantItems: []GateResult{
				{Name: "alpha", ExitCode: 1},
				{Name: "zeta", ExitCode: 0},
			},
		},
		{
			name:      "empty_results",
			in:        `{"overall_ok": true, "results": {}}`,
			wantOK:    true,
			wantItems: []GateResult{},
		},
		{
			name:   "all_pass_three_gates_sorted",
			in:     `{"overall_ok": true, "results": {"c": {"exit_code": 0}, "a": {"exit_code": 0}, "b": {"exit_code": 0}}}`,
			wantOK: true,
			wantItems: []GateResult{
				{Name: "a", ExitCode: 0},
				{Name: "b", ExitCode: 0},
				{Name: "c", ExitCode: 0},
			},
		},
		{
			name:   "all_fail_two_gates_sorted",
			in:     `{"overall_ok": false, "results": {"b": {"exit_code": 2}, "a": {"exit_code": 7}}}`,
			wantOK: false,
			wantItems: []GateResult{
				{Name: "a", ExitCode: 7},
				{Name: "b", ExitCode: 2},
			},
		},
		{
			name:   "gate_without_exit_code_defaults_zero_pass",
			in:     `{"overall_ok": false, "results": {"g": {"stdout": "s"}}}`,
			wantOK: false,
			wantItems: []GateResult{
				{Name: "g", ExitCode: 0},
			},
		},
		{
			name:   "single_pass",
			in:     `{"overall_ok": true, "results": {"only": {"exit_code": 0}}}`,
			wantOK: true,
			wantItems: []GateResult{
				{Name: "only", ExitCode: 0},
			},
		},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			ok, items, err := ParseGatesResults([]byte(c.in))
			if err != nil {
				t.Fatalf("ParseGatesResults unexpected error: %v", err)
			}
			if ok != c.wantOK {
				t.Errorf("overallOK mismatch: want %v, got %v", c.wantOK, ok)
			}
			if len(items) != len(c.wantItems) {
				t.Fatalf("len mismatch: want %d, got %d (got=%+v)", len(c.wantItems), len(items), items)
			}
			for i := range c.wantItems {
				if items[i] != c.wantItems[i] {
					t.Errorf("item %d mismatch: want %+v, got %+v", i, c.wantItems[i], items[i])
				}
			}
		})
	}
}

// TestParseGatesResultsEmptyResultsIsNotEmptyNil verifica que un results vacio
// ({}) devuelve un slice de longitud 0 (no nil) y error nil: el caller (el TUI)
// puede iterar sin un nil-check extra.
func TestParseGatesResultsEmptyResultsIsNotEmptyNil(t *testing.T) {
	ok, items, err := ParseGatesResults([]byte(`{"overall_ok": true, "results": {}}`))
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !ok {
		t.Errorf("expected overallOK true, got false")
	}
	if items == nil {
		t.Fatalf("expected non-nil empty slice for empty results, got nil")
	}
	if len(items) != 0 {
		t.Errorf("expected len 0, got %d", len(items))
	}
}

// TestParseGatesResultsInvalid cubre los MISMOS casos de error que el oraculo de
// Summarize (paridad): JSON invalido, falta overall_ok o results, results no es
// un objeto (array/string/numero/null), overall_ok de tipo equivocado, y
// top-level no objeto (array/numero/null/string/bool, bytes vacios). En todos
// devuelve (false, nil, err) sin panic.
func TestParseGatesResultsInvalid(t *testing.T) {
	cases := []struct {
		name string
		in   string
	}{
		{"invalid_json_trailing_comma", `{"overall_ok": true,`},
		{"missing_overall_ok", `{"results": {}}`},
		{"missing_results", `{"overall_ok": true}`},
		{"results_array", `{"overall_ok": true, "results": [1, 2]}`},
		{"results_string", `{"overall_ok": true, "results": "x"}`},
		{"results_number", `{"overall_ok": true, "results": 5}`},
		{"results_null", `{"overall_ok": true, "results": null}`},
		{"overall_ok_wrong_type", `{"overall_ok": "true", "results": {}}`},
		{"empty_bytes", ``},
		{"toplevel_array", `[1, 2, 3]`},
		{"toplevel_number", `42`},
		{"toplevel_null", `null`},
		{"toplevel_string", `"hello"`},
		{"toplevel_bool", `true`},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			ok, items, err := ParseGatesResults([]byte(c.in))
			if err == nil {
				t.Fatalf("expected error, got nil (ok=%v items=%+v)", ok, items)
			}
			if items != nil {
				t.Errorf("expected nil items on error, got %+v", items)
			}
		})
	}
}

// TestParseGatesResultsNoPanicsOnGarbage asegura que un blob de bytes arbitrario
// (no ASCII, no JSON) se reporta como error y nunca como panic.
func TestParseGatesResultsNoPanicsOnGarbage(t *testing.T) {
	defer func() {
		if r := recover(); r != nil {
			t.Fatalf("ParseGatesResults panicked on garbage input: %v", r)
		}
	}()
	ok, items, err := ParseGatesResults([]byte{0x00, 0x01, 0x02, 0xff, 0xfe})
	if err == nil {
		t.Fatalf("expected error on garbage, got ok=%v items=%+v", ok, items)
	}
	if items != nil {
		t.Errorf("expected nil items on error, got %+v", items)
	}
}

// --- SummarizeGateDetail ---

// TestSummarizeGateDetailSuccessWithOutput: la forma exitosa con stdout y
// stderr no vacios arma el string EXACTO con el formato documentado:
// "exit_code=<N>\n--- stdout ---\n<stdout>\n--- stderr ---\n<stderr>". Sin
// trailing newline extra mas alla del que ya traiga stderr.
func TestSummarizeGateDetailSuccessWithOutput(t *testing.T) {
	in := `{"exit_code": 1, "stdout": "hello\nworld", "stderr": "boom"}`
	want := "exit_code=1\n--- stdout ---\nhello\nworld\n--- stderr ---\nboom"
	got, err := SummarizeGateDetail([]byte(in))
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if got != want {
		t.Errorf("SummarizeGateDetail mismatch:\nwant: %q\ngot:  %q", want, got)
	}
}

// TestSummarizeGateDetailSuccessEmptyStderr: stderr vacio -> el string termina
// con "--- stderr ---\n" (sin contenido despues del separador). Formato
// determinista documentado.
func TestSummarizeGateDetailSuccessEmptyStderr(t *testing.T) {
	in := `{"exit_code": 0, "stdout": "hi", "stderr": ""}`
	want := "exit_code=0\n--- stdout ---\nhi\n--- stderr ---\n"
	got, err := SummarizeGateDetail([]byte(in))
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if got != want {
		t.Errorf("SummarizeGateDetail empty stderr mismatch:\nwant: %q\ngot:  %q", want, got)
	}
}

// TestSummarizeGateDetailSuccessEmptyStdout: stdout vacio, stderr no vacio.
func TestSummarizeGateDetailSuccessEmptyStdout(t *testing.T) {
	in := `{"exit_code": 2, "stdout": "", "stderr": "oops\n"}`
	want := "exit_code=2\n--- stdout ---\n\n--- stderr ---\noops\n"
	got, err := SummarizeGateDetail([]byte(in))
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if got != want {
		t.Errorf("SummarizeGateDetail empty stdout mismatch:\nwant: %q\ngot:  %q", want, got)
	}
}

// TestSummarizeGateDetailSuccessMissingStdoutStderr: exit_code presente pero sin
// claves stdout/stderr -> se decodifican como "" (default). Forma exitosa valida.
func TestSummarizeGateDetailSuccessMissingStdoutStderr(t *testing.T) {
	in := `{"exit_code": 0}`
	want := "exit_code=0\n--- stdout ---\n\n--- stderr ---\n"
	got, err := SummarizeGateDetail([]byte(in))
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if got != want {
		t.Errorf("SummarizeGateDetail missing stdout/stderr mismatch:\nwant: %q\ngot:  %q", want, got)
	}
}

// TestSummarizeGateDetailErrorForm: la forma de error {"error": "..."} devuelve
// ("", err) donde err.Error() es EXACTAMENTE el valor de "error".
func TestSummarizeGateDetailErrorForm(t *testing.T) {
	in := `{"error": "unknown gate: foo"}`
	got, err := SummarizeGateDetail([]byte(in))
	if err == nil {
		t.Fatalf("expected error, got nil (result=%q)", got)
	}
	if got != "" {
		t.Errorf("expected empty string on error form, got %q", got)
	}
	if err.Error() != "unknown gate: foo" {
		t.Errorf("error message mismatch: want %q, got %q", "unknown gate: foo", err.Error())
	}
}

// TestSummarizeGateDetailErrorFormEmptyValue: un "error" con valor vacio sigue
// siendo la forma de error (clave presente) -> ("", err) con mensaje "".
func TestSummarizeGateDetailErrorFormEmptyValue(t *testing.T) {
	in := `{"error": ""}`
	got, err := SummarizeGateDetail([]byte(in))
	if err == nil {
		t.Fatalf("expected error, got nil (result=%q)", got)
	}
	if got != "" {
		t.Errorf("expected empty string, got %q", got)
	}
}

// TestSummarizeGateDetailInvalidJSON: JSON invalido -> error, sin panic.
func TestSummarizeGateDetailInvalidJSON(t *testing.T) {
	got, err := SummarizeGateDetail([]byte(`{"exit_code": 0,`))
	if err == nil {
		t.Fatalf("expected error, got nil (result=%q)", got)
	}
	if got != "" {
		t.Errorf("expected empty string on invalid JSON, got %q", got)
	}
}

// TestSummarizeGateDetailNeitherForm: sin clave "error" ni "exit_code" -> no
// matchea ninguna de las 2 formas esperadas -> error.
func TestSummarizeGateDetailNeitherForm(t *testing.T) {
	got, err := SummarizeGateDetail([]byte(`{"stdout": "x"}`))
	if err == nil {
		t.Fatalf("expected error, got nil (result=%q)", got)
	}
	if got != "" {
		t.Errorf("expected empty string, got %q", got)
	}
}

// TestSummarizeGateDetailNoPanicsOnGarbage: garbage no ASCII -> error, sin panic.
func TestSummarizeGateDetailNoPanicsOnGarbage(t *testing.T) {
	defer func() {
		if r := recover(); r != nil {
			t.Fatalf("SummarizeGateDetail panicked on garbage: %v", r)
		}
	}()
	got, err := SummarizeGateDetail([]byte{0x00, 0x01, 0xff, 0xfe})
	if err == nil {
		t.Fatalf("expected error on garbage, got result=%q", got)
	}
	if got != "" {
		t.Errorf("expected empty string on error, got %q", got)
	}
}