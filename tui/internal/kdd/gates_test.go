package kdd

import "testing"

// TestSummarizeValid cubre los casos de exito: forma exacta del string de
// resumen, ordenamiento alfabetico de los gates (el input viene en orden
// distinto al esperado), results vacio, gate sin exit_code (default 0 ->
// pass) y ausencia de newline final.
func TestSummarizeValid(t *testing.T) {
	cases := []struct {
		name string
		in   string
		want string
	}{
		{
			name: "mixed_pass_fail_alpha_sorted",
			in:   `{"overall_ok": false, "results": {"zeta": {"exit_code": 0, "stdout": "x", "stderr": ""}, "alpha": {"exit_code": 1, "stdout": "", "stderr": "boom"}}}`,
			want: "overall_ok=false pass=1 fail=1\n[FAIL] alpha\n[PASS] zeta",
		},
		{
			name: "empty_results",
			in:   `{"overall_ok": true, "results": {}}`,
			want: "overall_ok=true pass=0 fail=0",
		},
		{
			name: "all_pass_three_gates_sorted",
			in:   `{"overall_ok": true, "results": {"c": {"exit_code": 0}, "a": {"exit_code": 0}, "b": {"exit_code": 0}}}`,
			want: "overall_ok=true pass=3 fail=0\n[PASS] a\n[PASS] b\n[PASS] c",
		},
		{
			name: "all_fail_two_gates_sorted",
			in:   `{"overall_ok": false, "results": {"b": {"exit_code": 2}, "a": {"exit_code": 7}}}`,
			want: "overall_ok=false pass=0 fail=2\n[FAIL] a\n[FAIL] b",
		},
		{
			name: "gate_without_exit_code_defaults_zero_pass",
			in:   `{"overall_ok": false, "results": {"g": {"stdout": "s"}}}`,
			want: "overall_ok=false pass=1 fail=0\n[PASS] g",
		},
		{
			name: "single_pass_no_trailing_newline",
			in:   `{"overall_ok": true, "results": {"only": {"exit_code": 0}}}`,
			want: "overall_ok=true pass=1 fail=0\n[PASS] only",
		},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			got, err := Summarize([]byte(c.in))
			if err != nil {
				t.Fatalf("Summarize unexpected error: %v", err)
			}
			if got != c.want {
				t.Errorf("Summarize mismatch:\nwant: %q\ngot:  %q", c.want, got)
			}
		})
	}
}

// TestSummarizeInvalid cubre los casos de error: JSON invalido, forma
// inesperada (falta overall_ok o results, results no es un objeto, results
// null, overall_ok de tipo equivocado) y top-level no objeto. En todos
// esos casos Summarize devuelve ("", err) sin panic.
func TestSummarizeInvalid(t *testing.T) {
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
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			got, err := Summarize([]byte(c.in))
			if err == nil {
				t.Fatalf("expected error, got nil (result=%q)", got)
			}
			if got != "" {
				t.Errorf("expected empty string on error, got %q", got)
			}
		})
	}
}

// TestSummarizeNoPanicsOnGarbage asegura que un blob de bytes arbitrario
// (no ASCII, no JSON) se reporta como error y nunca como panic.
func TestSummarizeNoPanicsOnGarbage(t *testing.T) {
	defer func() {
		if r := recover(); r != nil {
			t.Fatalf("Summarize panicked on garbage input: %v", r)
		}
	}()
	got, err := Summarize([]byte{0x00, 0x01, 0x02, 0xff, 0xfe})
	if err == nil {
		t.Fatalf("expected error on garbage, got result=%q", got)
	}
	if got != "" {
		t.Errorf("expected empty string on error, got %q", got)
	}
}