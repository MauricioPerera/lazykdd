---
type: 'Concept'
title: 'Diagram contract: diagramas Mermaid verificables'
description: 'Convencion OKF para referenciar diagramas Mermaid desde un concept doc, y formato del .diagram-contract.json que verifica su estructura de forma determinista contra scripts/validate_diagrams.py.'
tags: ['diagramas', 'mermaid', 'ccdd', 'okf', 'declarativo', 'reference']
---

# Diagram contract — diagramas Mermaid verificables

Extiende OKF (ver [OKF-SPEC](./OKF-SPEC.md)) para que un concept doc pueda declarar un
diagrama Mermaid como parte de su conocimiento, y que ese diagrama sea verificable de
forma determinista (no solo embebido como texto). Mismo patron que
[rule-contract-spec](./rule-contract-spec.md): datos declarativos + checker sin LLM ni red.

## Dos niveles de "diagrama verificable"

1. **Embebido, sin verificar** — un bloque ` ```mermaid ` dentro del cuerpo markdown de
   cualquier concept doc. Ya funciona sin ninguna convencion nueva; GitHub y la mayoria de
   los viewers OKF lo renderizan. No hay gate: es prosa con dibujo, igual que cualquier otro
   contenido markdown.
2. **Referenciado y verificable** — el concept doc apunta a un archivo `.mmd` real via
   `resource`, y ese `.mmd` tiene un `.diagram-contract.json` al lado que declara su
   estructura obligatoria. `scripts/validate_diagrams.py` lo verifica en CI. Este documento
   describe el nivel 2.

## Convencion de archivos

Por cada diagrama verificable:

```
<nombre>.mmd                       # el diagrama Mermaid
<nombre>.diagram-contract.json     # el contrato (mismo basename, sufijo fijo)
```

El concept doc que lo declara usa:

```yaml
---
type: 'Architecture Diagram'
title: 'Flujo de checkout'
resource: '/examples/diagrams/checkout-flow.mmd'
---
```

`type: 'Architecture Diagram'` es una convencion de este proyecto, no una lista cerrada de
OKF (la spec es explicita: "los valores de tipo no se registran centralmente" y los
consumidores deben tolerar tipos desconocidos). Cualquier `type` sirve; este es el que usan
los ejemplos de este repo.

## Formato del `.diagram-contract.json`

Subconjunto deliberadamente simple del formato YAML del proyecto hermano `mermaid-gate`
(mismo vocabulario, JSON en vez de YAML: este repo no tiene parser YAML de proposito
general, mismo precedente que `examples/rules/*.rules.json` de `rule_engine.py`).

```json
{
  "diagram_type": "flowchart",
  "min_nodes": 3,
  "max_nodes": 8,
  "required_nodes": [
    { "id": "A", "label": "Inicio" },
    { "id": "B" }
  ],
  "required_edges": [
    { "from": "A", "to": "B" },
    { "from": "B", "to": "C", "label": "Si" }
  ]
}
```

Todos los campos son opcionales salvo que quieras que el gate chequee algo — un contrato
`{}` solo valida que el `.mmd` parsee como flowchart. `label` en `required_nodes`/
`required_edges` es opcional: si se omite, solo se exige que el nodo/edge exista, sin
importar su texto.

## Alcance: SOLO flowchart

`scripts/validate_diagrams.py` es un parser propio en Python puro (regex, sin dependencias),
escrito porque los gates de este repo prohiben `subprocess`/`network`/`llm` — no puede
invocar el parser real de mermaid (Node.js). Consecuencia directa: solo soporta
`diagram_type: "flowchart"` (o el alias legacy `graph` en el `.mmd`). Un contrato que pida
otro tipo (`sequenceDiagram`, `classDiagram`, etc.) falla explicito con
`DIAGRAM_TYPE_UNSUPPORTED`, no intenta parsearlo con la gramatica equivocada.

Tampoco tiene la fidelidad del parser real dentro de flowchart: no maneja subgraphs,
estilos, ni edges multi-linea. Es un chequeo de estructura basico (nodos/edges esperados),
no un parser completo.

### El proyecto hermano: mermaid-gate

Para verificacion con el parser real de mermaid y cobertura de los 20 tipos de diagrama
(flowchart, sequenceDiagram, classDiagram, stateDiagram, erDiagram, mindmap, gitGraph,
gantt, pie, journey, requirementDiagram, C4Context, sankey, quadrantChart, block, timeline,
xychart, kanban, packet, radar), usar el proyecto `mermaid-gate` (Node.js, fuera de este
repo, sin la restriccion `forbids: subprocess`) como herramienta externa —
`node <ruta-a-mermaid-gate>/src/gate.js <diagrama.mmd> <contrato.yaml>`. Su formato de
contrato YAML es el superset del que describe este documento; incluye ademas una capa
opcional de juicio semantico via LLM externo (`judge`/veredictos), fuera del alcance de
`validate_diagrams.py` por la misma razon (`forbids: llm`).

Esto es intencional, no una limitacion a resolver: los gates Nivel 1 de este repo son
deterministas y sin dependencias por diseno; `mermaid-gate` cubre el resto del espacio
(mas tipos, mas fidelidad, juicio semantico) como herramienta externa, igual que el gate
CCDD real (`ccdd-complexity` MCP) ya es Nivel 2 opcional en vez de Nivel 1.

## Gate

`python scripts/validate_diagrams.py <path...>` — default `examples/diagrams`. Ver
[knowledge/contracts/diagram-gate.md](./contracts/diagram-gate.md) para el contrato completo
y `tests/test_validate_diagrams.py` para el comportamiento exacto (reglas, niveles,
mensajes). Capa opcional: sin diagramas, INFO y exit 0; `.mmd` sin contrato, WARNING (no
bloquea) — un diagrama puede existir sin contrato si no se lo quiere verificar.
