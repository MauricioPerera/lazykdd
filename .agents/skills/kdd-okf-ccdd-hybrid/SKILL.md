---
name: kdd-okf-ccdd-hybrid
description: Define el estándar Knowledge-Driven Development (KDD) que unifica el modelado de contexto de Open Knowledge Format (OKF) con el rigor de Contract-Driven Development (CCDD).
---

# Knowledge-Driven Development (KDD): OKF + CCDD

Esta skill establece las reglas obligatorias al definir tareas de desarrollo utilizando la metodología híbrida. 
El objetivo es que los contratos no sean documentos aislados, sino nodos vivos de la base de conocimiento OKF que controlan determinísticamente a los agentes efímeros.

## 1. El Contrato es un Nodo OKF
Todo Task Contract CCDD que se escriba (p.ej. `implementar_login.md`) debe comenzar estrictamente con un Frontmatter YAML válido.

## 2. Fusión de Metadatos (Frontmatter)
El Frontmatter debe unificar los campos requeridos por ambas metodologías:
- **OKF Fields:** `type` (debe ser `'Task Contract'`), `title`, `description`, `tags`.
- **CCDD Fields:** `task`, `intent`, `target`, `signature`, `test_command`, `budget`, `tests`, `deps_allowed`.

Ejemplo:
```yaml
---
type: 'Task Contract'
title: 'Implementar verify_user'
description: 'Función pura para validación de ID.'
tags: ['ccdd', 'auth']

task: verify_user
intent: "Implementar la validación..."
target: verify_user.py
signature: "def verify_user(id: str) -> bool:"
test_command: "python -m unittest verify_test.py"
budget:
  max_cyclomatic_complexity: 4
tests: "verify_test.py"
---
```

## 3. Contexto Interconectado (Enlaces OKF)
Para proveer el contexto del negocio y diseño a los agentes efímeros sin abrumarlos, **está prohibido duplicar reglas de negocio de manera verbosa en el contrato**.
En lugar de eso, en secciones como `## Intent`, `## Interface`, o `## Constraints`, se DEBE usar un enlace de Markdown relativo hacia los nodos de OKF relevantes (arquitectura, modelos de datos).
- **DO:** "Validar formato contra [users_table.md](../data_models/users_table.md)"
- **DON'T:** "La tabla de usuarios tiene un uuid, un email, un password, y una fecha de creación, y su ID es un string de 36 caracteres..."

## 4. Validación Continua Obligatoria
Antes de dar un contrato por terminado o pasárselo a un agente efímero, debes invocar obligatoriamente las herramientas CLI locales (`ccdd-lint` y `ccdd-gate`) sobre el archivo híbrido para confirmar que no se violan las reglas estrictas de parsing ni de los tests congelados.
