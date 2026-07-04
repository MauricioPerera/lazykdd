---
type: 'Task Contract'
title: 'Ejemplo de Tarea (Hello World)'
description: 'Un contrato base para demostrar el uso de CCDD + OKF'
tags: ['ccdd', 'template']

task: hello_world
intent: "Demostrar cómo se estructura una tarea en la plantilla KDD."
target: src/hello.py
signature: "def hello(name: str) -> str:"
test_command: "python -m unittest tests/test_sample.py"
budget:
  max_cyclomatic_complexity: 2
  max_nesting_depth: 1
tests: "tests/test_sample.py"
deps_allowed: []
forbids: ['network', 'subprocess']
---

# Contract: Hello World

## Intent
Implementar una función que retorne un saludo simple. Se alinea con nuestra meta de desarrollo demostrada en [la arquitectura general](../index.md).

## Interface
```python
def hello(name: str) -> str:
    ...
```

## Invariants
- La función no lanza excepciones.

## Examples
- `hello("Agente")` -> `"Hello, Agente"`
- `hello("Mundo")` -> `"Hello, Mundo"`
- `hello("")` -> `"Hello, "`

## Do / Don't
- DO: Usar f-strings de Python.

## Tests
(Los tests están en `tests/test_sample.py`)

## Constraints
- PARAR y reportar si... necesitas conectarte a la red.
