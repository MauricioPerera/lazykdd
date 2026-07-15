package kdd

import "testing"

// TestSummarizeContractsStatusValid cubre los casos de exito: forma exacta
// del string de resumen, ordenamiento alfabetico por task (el input viene en
// orden distinto al esperado), lista vacia (contracts=0), un solo elemento,
// varios con distintos lifecycle y un elemento con claves extra (se acepta:
// alcanza con que tenga AL MENOS task y lifecycle como string). Sin trailing
// newline.
func TestSummarizeContractsStatusValid(t *testing.T) {
	cases := []struct {
		name string
		in   string
		want string
	}{
		{
			name: "mixed_lifecycle_alpha_sorted",
			in:   `[{"task":"zeta","lifecycle":"draft"},{"task":"alpha","lifecycle":"verified"},{"task":"mid","lifecycle":"implemented"}]`,
			want: "contracts=3\nalpha: verified\nmid: implemented\nzeta: draft",
		},
		{
			name: "empty_list",
			in:   `[]`,
			want: "contracts=0",
		},
		{
			name: "single_element",
			in:   `[{"task":"only","lifecycle":"draft"}]`,
			want: "contracts=1\nonly: draft",
		},
		{
			name: "several_distinct_lifecycle",
			in:   `[{"task":"c","lifecycle":"validated"},{"task":"a","lifecycle":"draft"},{"task":"b","lifecycle":"implemented"}]`,
			want: "contracts=3\na: draft\nb: implemented\nc: validated",
		},
		{
			name: "element_with_extra_keys_accepted",
			in:   `[{"task":"a","lifecycle":"draft","extra":42,"more":"x"}]`,
			want: "contracts=1\na: draft",
		},
		{
			name: "duplicate_tasks_listed_all",
			in:   `[{"task":"a","lifecycle":"draft"},{"task":"a","lifecycle":"verified"}]`,
			want: "contracts=2\na: draft\na: verified",
		},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			got, err := SummarizeContractsStatus([]byte(c.in))
			if err != nil {
				t.Fatalf("SummarizeContractsStatus unexpected error: %v", err)
			}
			if got != c.want {
				t.Errorf("SummarizeContractsStatus mismatch:\nwant: %q\ngot:  %q", c.want, got)
			}
		})
	}
}

// TestSummarizeContractsStatusInvalid cubre los casos de error: JSON invalido,
// top-level no lista (objeto/numero/string/null), elemento de la lista que no
// es objeto (numero/string/null/bool), elemento sin task o sin lifecycle, y
// elemento con task/lifecycle de tipo no-string. En todos esos casos devuelve
// ("", err) sin panic.
func TestSummarizeContractsStatusInvalid(t *testing.T) {
	cases := []struct {
		name string
		in   string
	}{
		{"invalid_json_trailing_comma", `[{"task":"a",`},
		{"empty_bytes", ``},
		{"toplevel_object", `{"task":"a","lifecycle":"draft"}`},
		{"toplevel_number", `42`},
		{"toplevel_string", `"hello"`},
		{"toplevel_null", `null`},
		{"toplevel_bool", `true`},
		{"element_number", `[1, 2, 3]`},
		{"element_string", `["a", "b"]`},
		{"element_null", `[null]`},
		{"element_bool", `[true, false]`},
		{"element_missing_task", `[{"lifecycle":"draft"}]`},
		{"element_missing_lifecycle", `[{"task":"a"}]`},
		{"element_task_not_string", `[{"task":1,"lifecycle":"draft"}]`},
		{"element_lifecycle_not_string", `[{"task":"a","lifecycle":2}]`},
		{"element_task_null", `[{"task":null,"lifecycle":"draft"}]`},
		{"element_task_bool", `[{"task":true,"lifecycle":"draft"}]`},
		{"second_element_missing_task", `[{"task":"a","lifecycle":"draft"},{"lifecycle":"x"}]`},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			got, err := SummarizeContractsStatus([]byte(c.in))
			if err == nil {
				t.Fatalf("expected error, got nil (result=%q)", got)
			}
			if got != "" {
				t.Errorf("expected empty string on error, got %q", got)
			}
		})
	}
}

// TestSummarizeContractsStatusNoPanicsOnGarbage asegura que un blob de bytes
// arbitrario (no ASCII, no JSON) se reporta como error y nunca como panic.
func TestSummarizeContractsStatusNoPanicsOnGarbage(t *testing.T) {
	defer func() {
		if r := recover(); r != nil {
			t.Fatalf("SummarizeContractsStatus panicked on garbage input: %v", r)
		}
	}()
	got, err := SummarizeContractsStatus([]byte{0x00, 0x01, 0x02, 0xff, 0xfe})
	if err == nil {
		t.Fatalf("expected error on garbage, got result=%q", got)
	}
	if got != "" {
		t.Errorf("expected empty string on error, got %q", got)
	}
}