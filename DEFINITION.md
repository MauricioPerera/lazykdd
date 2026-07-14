# lazykdd — Definición del proyecto

Este documento es la definición cerrada del proyecto real que se va a
construir con KDD, de punta a punta, como caso de estudio (ver
`CASE-STUDY-LOG.md`). Es DEFINICIÓN, no implementación: acá no hay
contratos CCDD todavía — esos se escriben tarea por tarea, justo antes de
delegar cada una, siguiendo el propio proceso de KDD.

## Qué es

TUI (terminal UI) estilo `lazygit`/`lazydocker` para navegar y operar un
repo KDD sin memorizar los `scripts/*.py` ni leer texto plano en la
consola. Reduce la fricción de KDD para quien vive en la terminal, sin el
peso de una app de escritorio — la alternativa liviana a `kdd-ui-tauri`
(que sigue existiendo, para quien prefiera GUI).

## Arquitectura: un core, tres pieles

```
        scripts/mcp_gate_dispatch.py   (Python, YA EXISTE)
        logica pura de despacho de gates: GATE_SPECS, run_gate,
        run_all_level1, seal_tests -- este proyecto la EXTIENDE
        (browsing, scaffolding, lifecycle), no la reemplaza.
                    |
      +-------------+-------------+
      |             |             |
   MCP server     CLI --json    (el CLI es lo que consume el TUI)
   (YA EXISTE,   (NUEVO: kdd
   14 tools)     command, Python)
                      |
                   TUI (Go + Bubble Tea, NUEVO)
                   shellea al CLI, parsea JSON,
                   CERO logica de KDD propia --
                   mismo patron que lazygit shellea a `git`.
```

- **Piel 1 — MCP** (agente de IA): `scripts/mcp_server.py`, ya existe (14
  tools). Este proyecto lo extiende si las capacidades nuevas
  (browsing/scaffolding/lifecycle) tienen sentido como tools de agente
  también, no solo de humano.
- **Piel 2 — CLI con `--json`** (nueva, Python): comando `kdd`, envuelve
  el dispatch existente y devuelve JSON estructurado — no texto para
  humanos. Es el puente que consume la Piel 3; también sirve suelta para
  cualquiera que quiera scriptear KDD sin MCP.
- **Piel 3 — TUI** (nueva, Go + Bubble Tea): shellea a la Piel 2, parsea
  el JSON. Sin lógica de KDD propia — si mañana el core cambia, el TUI no
  se toca mientras el JSON no cambie de forma.

## Capacidades objetivo

Sin fasear todavía — el orden real de implementación se decide al
empezar a delegar tareas, no acá:

- Correr gates (Nivel 1 completo o individual) y ver el resultado.
- Browsing de `knowledge/`/contratos (listar, leer).
- Scaffolding de un contrato nuevo desde `TEMPLATE-task-contract.md`.
- Estado de ciclo de vida por contrato (`draft`/`validated`/
  `implemented`/`verified`), no solo el pass/fail crudo del gate.

## Por qué es un caso de estudio válido

- No es dogfooding vacío: `lazykdd` tiene valor externo real — cualquiera
  que use KDD lo querría, independientemente de que se haya construido
  con KDD.
- Primer proyecto multi-lenguaje real de KDD (Python core + Go TUI) —
  cierra el gap identificado hoy ("multi-lenguaje: un solo ejemplo vivo,
  y trivial" — ver `knowledge/contracts/example-node-greet.md` en KDD).
- Reusa el patrón ya probado hoy mismo en KDD: separar lógica pura
  (`mcp_gate_dispatch.py`) del wiring específico de cada interfaz
  (`mcp_server.py`) — este proyecto solo agrega dos pieles más al mismo
  core.

## Fuera de alcance (explícito)

- No se reimplementa lógica de gates en Go — el TUI SIEMPRE pasa por el
  CLI Python, nunca reimplementa un check.
- No se toca `kdd-ui`/`kdd-ui-tauri` — siguen siendo la alternativa GUI de
  escritorio, proyectos aparte.
- Nombre del binario Go, forma exacta de los comandos del CLI JSON,
  layout de paneles del TUI — eso es implementación, se define en los
  contratos de cada tarea, no acá.
