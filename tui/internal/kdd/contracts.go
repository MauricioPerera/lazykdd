package kdd

import (
	"encoding/json"
	"fmt"
	"sort"
	"strings"
)

// SummarizeContractsStatus parsea el JSON crudo que emite `python
// scripts/kdd_cli.py contracts status --json` (una lista de objetos
// {"task": string, "lifecycle": string}) y arma un resumen determinista:
//
//	contracts=<N>
//	<task_1>: <lifecycle_1>
//	<task_2>: <lifecycle_2>
//	...
//
// Los contratos se listan en orden alfabetico por task (el JSON no garantiza
// orden estable). Las lineas se unen con '\n' SIN trailing newline. Una lista
// vacia ([]) es valida: solo el header contracts=0, sin lineas.
//
// Devuelve ("", err) si data no es JSON valido, el top-level no es una lista,
// o algun elemento no es un objeto con AL MENOS las claves "task" y
// "lifecycle" como string. La funcion es pura: sin I/O, sin red, sin os.Exit,
// nunca paniquea.
func SummarizeContractsStatus(data []byte) (string, error) {
	// Primer pasada: lista top-level como raw messages. Unmarshal sobre un
	// slice rechaza objeto/numero/string/bool; "null" deja nil sin error y
	// hay que detectarlo (null no es una lista).
	var raws []json.RawMessage
	if err := json.Unmarshal(data, &raws); err != nil {
		return "", err
	}
	if raws == nil {
		return "", fmt.Errorf("top-level is null, expected an array")
	}

	type entry struct {
		task      string
		lifecycle string
	}
	entries := make([]entry, 0, len(raws))
	for i, raw := range raws {
		// Elemento como claves crudas para detectar presencia de "task" y
		// "lifecycle" y validar que sean string (unmarshal sobre string
		// rechaza numero/bool/null/objeto/array).
		var obj map[string]json.RawMessage
		if err := json.Unmarshal(raw, &obj); err != nil {
			return "", fmt.Errorf("element %d: %w", i, err)
		}
		// Unmarshal de "null" sobre un map deja nil sin error; null no es un
		// objeto -> forma inesperada.
		if obj == nil {
			return "", fmt.Errorf("element %d is null, expected an object", i)
		}
		taskRaw, ok := obj["task"]
		if !ok {
			return "", fmt.Errorf("element %d missing key: task", i)
		}
		// Puntero para distinguir "null" (nil, no es string) de un string
		// vacio legitimo; ademas rechaza numero/bool/objeto/array.
		var taskPtr *string
		if err := json.Unmarshal(taskRaw, &taskPtr); err != nil {
			return "", fmt.Errorf("element %d task: %w", i, err)
		}
		if taskPtr == nil {
			return "", fmt.Errorf("element %d task: null is not a string", i)
		}
		lifeRaw, ok := obj["lifecycle"]
		if !ok {
			return "", fmt.Errorf("element %d missing key: lifecycle", i)
		}
		var lifePtr *string
		if err := json.Unmarshal(lifeRaw, &lifePtr); err != nil {
			return "", fmt.Errorf("element %d lifecycle: %w", i, err)
		}
		if lifePtr == nil {
			return "", fmt.Errorf("element %d lifecycle: null is not a string", i)
		}
		entries = append(entries, entry{task: *taskPtr, lifecycle: *lifePtr})
	}

	sort.Slice(entries, func(i, j int) bool {
		return entries[i].task < entries[j].task
	})

	var sb strings.Builder
	fmt.Fprintf(&sb, "contracts=%d", len(entries))
	for _, e := range entries {
		fmt.Fprintf(&sb, "\n%s: %s", e.task, e.lifecycle)
	}
	return sb.String(), nil
}