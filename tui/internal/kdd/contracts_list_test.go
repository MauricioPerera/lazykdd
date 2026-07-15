package kdd

import "testing"

// TestParseContractsStatusValid cubre los casos de exito: orden alfabetico
// por Task (el input viene en orden distinto al esperado), lista vacia (slice
// vacio, no nil, sin error), un solo elemento, varios con distintos lifecycle,
// elemento con claves extra (se acepta: alcanza con AL MENOS task y lifecycle
// como string), y tasks duplicados (se listan todos). Verifica Task y Lifecycle
// exactos de cada entrada.
func TestParseContractsStatusValid(t *testing.T) {
	cases := []struct {
		name string
		in   string
		want []ContractStatus
	}{
		{
			name: "mixed_lifecycle_alpha_sorted",
			in:   `[{"task":"zeta","lifecycle":"draft"},{"task":"alpha","lifecycle":"verified"},{"task":"mid","lifecycle":"implemented"}]`,
			want: []ContractStatus{
				{Task: "alpha", Lifecycle: "verified"},
				{Task: "mid", Lifecycle: "implemented"},
				{Task: "zeta", Lifecycle: "draft"},
			},
		},
		{
			name: "empty_list",
			in:   `[]`,
			want: []ContractStatus{},
		},
		{
			name: "single_element",
			in:   `[{"task":"only","lifecycle":"draft"}]`,
			want: []ContractStatus{{Task: "only", Lifecycle: "draft"}},
		},
		{
			name: "several_distinct_lifecycle",
			in:   `[{"task":"c","lifecycle":"validated"},{"task":"a","lifecycle":"draft"},{"task":"b","lifecycle":"implemented"}]`,
			want: []ContractStatus{
				{Task: "a", Lifecycle: "draft"},
				{Task: "b", Lifecycle: "implemented"},
				{Task: "c", Lifecycle: "validated"},
			},
		},
		{
			name: "element_with_extra_keys_accepted",
			in:   `[{"task":"a","lifecycle":"draft","extra":42,"more":"x"}]`,
			want: []ContractStatus{{Task: "a", Lifecycle: "draft"}},
		},
		{
			name: "duplicate_tasks_listed_all",
			in:   `[{"task":"a","lifecycle":"draft"},{"task":"a","lifecycle":"verified"}]`,
			want: []ContractStatus{
				{Task: "a", Lifecycle: "draft"},
				{Task: "a", Lifecycle: "verified"},
			},
		},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			got, err := ParseContractsStatus([]byte(c.in))
			if err != nil {
				t.Fatalf("ParseContractsStatus unexpected error: %v", err)
			}
			if len(got) != len(c.want) {
				t.Fatalf("len mismatch: want %d, got %d (got=%+v)", len(c.want), len(got), got)
			}
			for i := range c.want {
				if got[i] != c.want[i] {
					t.Errorf("entry %d mismatch: want %+v, got %+v", i, c.want[i], got[i])
				}
			}
		})
	}
}

// TestParseContractsStatusEmptyListIsNotEmptyNil verifica que una lista vacia
// devuelve un slice de longitud 0 (no nil) y error nil: el caller (el TUI)
// puede iterar sin un nil-check extra.
func TestParseContractsStatusEmptyListIsNotEmptyNil(t *testing.T) {
	got, err := ParseContractsStatus([]byte(`[]`))
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if got == nil {
		t.Fatalf("expected non-nil empty slice for [], got nil")
	}
	if len(got) != 0 {
		t.Errorf("expected len 0, got %d", len(got))
	}
}

// TestParseContractsStatusInvalid cubre los mismos casos de error que el
// oraculo de SummarizeContractsStatus (paridad): JSON invalido, top-level no
// lista (objeto/numero/string/null/bool), elemento no objeto
// (numero/string/null/bool), elemento sin task o sin lifecycle, y elemento con
// task/lifecycle de tipo no-string (numero/null/bool). En todos devuelve
// (nil, err) sin panic.
func TestParseContractsStatusInvalid(t *testing.T) {
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
			got, err := ParseContractsStatus([]byte(c.in))
			if err == nil {
				t.Fatalf("expected error, got nil (result=%+v)", got)
			}
			if got != nil {
				t.Errorf("expected nil slice on error, got %+v", got)
			}
		})
	}
}

// TestParseContractsStatusNoPanicsOnGarbage asegura que un blob de bytes
// arbitrario (no ASCII, no JSON) se reporta como error y nunca como panic.
func TestParseContractsStatusNoPanicsOnGarbage(t *testing.T) {
	defer func() {
		if r := recover(); r != nil {
			t.Fatalf("ParseContractsStatus panicked on garbage input: %v", r)
		}
	}()
	got, err := ParseContractsStatus([]byte{0x00, 0x01, 0x02, 0xff, 0xfe})
	if err == nil {
		t.Fatalf("expected error on garbage, got result=%+v", got)
	}
	if got != nil {
		t.Errorf("expected nil slice on error, got %+v", got)
	}
}