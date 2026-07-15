package kdd

import (
	"encoding/json"
	"fmt"
	"sort"
)

// ContractStatus es una entrada estructurada del JSON de `contracts status
// --json`: el task (nombre kebab-case del contrato) y su etapa de ciclo de
// vida (draft/validated/implemented/verified). Lo pobla ParseContractsStatus.
type ContractStatus struct {
	Task      string
	Lifecycle string
}

// ParseContractsStatus parsea el JSON crudo que emite `python
// scripts/kdd_cli.py contracts status --json` (una lista de objetos
// {"task": string, "lifecycle": string}) y devuelve los datos ESTRUCTURADOS
// como un slice de ContractStatus, en orden alfabetico por Task.
//
// Es la variante estructurada de SummarizeContractsStatus (que devuelve un
// string formateado): mismo parseo/validacion, mismo orden defensivo, misma
// lista-vacia-es-valida. El TUI la usa para armar la lista navegable (cursor,
// Enter -> detalle) en tui/internal/ui/model.go.
//
// Devuelve (nil, err) si data no es JSON valido, el top-level no es una lista
// (o es null), o algun elemento no es un objeto con AL MENOS las claves "task"
// y "lifecycle" como string (numero/bool/null/objeto/array rechazados). Una
// lista vacia ([]) es valida: devuelve un slice vacio (no nil) y error nil.
//
// Pura: sin I/O, sin red, sin os.Exit, nunca paniquea.
//
// TRADE-OFF (documentado en el REPORT): la logica de parseo/validacion esta
// DUPLICADA de SummarizeContractsStatus en contracts.go. No se extrajo un
// parser interno comun porque [ARCHIVOS] prohíbe tocar contracts.go (ni su
// contrato sellado); refactorizar SummarizeContractsStatus para llamar a un
// helper compartido cambiaria sus internals y exigiria re-sellar su contrato,
// fuera de alcance. Duplicar ~40 lineas de validacion defensiva es mas barato
// que el acoplamiento cross-archivo y mantiene cada funcion enfocada. Si
// ambas divergieran algun dia, los tests congelados de cada una lo pegan.
func ParseContractsStatus(data []byte) ([]ContractStatus, error) {
	// Primer pasada: lista top-level como raw messages. Unmarshal sobre un
	// slice rechaza objeto/numero/string/bool; "null" deja nil sin error y
	// hay que detectarlo (null no es una lista).
	var raws []json.RawMessage
	if err := json.Unmarshal(data, &raws); err != nil {
		return nil, err
	}
	if raws == nil {
		return nil, fmt.Errorf("top-level is null, expected an array")
	}

	entries := make([]ContractStatus, 0, len(raws))
	for i, raw := range raws {
		// Elemento como claves crudas para detectar presencia de "task" y
		// "lifecycle" y validar que sean string (unmarshal sobre string
		// rechaza numero/bool/null/objeto/array).
		var obj map[string]json.RawMessage
		if err := json.Unmarshal(raw, &obj); err != nil {
			return nil, fmt.Errorf("element %d: %w", i, err)
		}
		// Unmarshal de "null" sobre un map deja nil sin error; null no es un
		// objeto -> forma inesperada.
		if obj == nil {
			return nil, fmt.Errorf("element %d is null, expected an object", i)
		}
		taskRaw, ok := obj["task"]
		if !ok {
			return nil, fmt.Errorf("element %d missing key: task", i)
		}
		// Puntero para distinguir "null" (nil, no es string) de un string
		// vacio legitimo; ademas rechaza numero/bool/objeto/array.
		var taskPtr *string
		if err := json.Unmarshal(taskRaw, &taskPtr); err != nil {
			return nil, fmt.Errorf("element %d task: %w", i, err)
		}
		if taskPtr == nil {
			return nil, fmt.Errorf("element %d task: null is not a string", i)
		}
		lifeRaw, ok := obj["lifecycle"]
		if !ok {
			return nil, fmt.Errorf("element %d missing key: lifecycle", i)
		}
		var lifePtr *string
		if err := json.Unmarshal(lifeRaw, &lifePtr); err != nil {
			return nil, fmt.Errorf("element %d lifecycle: %w", i, err)
		}
		if lifePtr == nil {
			return nil, fmt.Errorf("element %d lifecycle: null is not a string", i)
		}
		entries = append(entries, ContractStatus{Task: *taskPtr, Lifecycle: *lifePtr})
	}

	sort.Slice(entries, func(i, j int) bool {
		return entries[i].Task < entries[j].Task
	})

	return entries, nil
}