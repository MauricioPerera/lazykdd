# Registro del caso de estudio KDD

Este archivo NO es parte de la metodología KDD (no lo lee ningún gate, no
sigue el formato OKF). Es un diario aparte: el registro externo de que este
proyecto se construyó con KDD de punta a punta, para servir de evidencia
real cuando se documente como caso de estudio (gap identificado: KDD nunca
se probó fuera de sí mismo).

Cada entrada: fecha, qué se hizo, por qué, evidencia (comando + resultado
si aplica). Sin relleno — si no hay nada verificable que registrar, no se
agrega entrada.

---

## 2026-07-14 — Setup

- Clonado desde `MauricioPerera/KDD` en el tag `v1.6.0` (commit `8bb82f4`).
- Repo desenganchado del remoto de KDD (`git remote remove origin`); este
  proyecto no trackea upstream por git — los upgrades futuros de plantilla
  siguen el procedimiento manual de `knowledge/plantilla-upgrade.md`
  (clonar el nuevo release aparte y diffear la infraestructura a mano).
- Plantilla dejada SIN instanciar (`init_project.py` no corrido todavía):
  los artefactos de ejemplo (`sample_task.md`, dominios de ejemplo, etc.)
  siguen presentes como referencia hasta que se defina el alcance real del
  proyecto — instanciar pide un `--name` que todavía no existe.
- Verificado sano antes de arrancar: `validate_contracts.py` 0 errores (29
  contratos), suite completa 573/573 verde.

## 2026-07-14 — Definición del proyecto: lazykdd

- Proyecto elegido: `lazykdd`, TUI estilo lazygit/lazydocker para operar
  un repo KDD. Motivación: gap identificado en el análisis de posiciona-
  miento de KDD (nunca se probó en un proyecto real no-toy) + fricción
  real de esta misma sesión (leer texto plano de 12 gates a mano).
- Definición cerrada en `DEFINITION.md`: arquitectura de un core (Python,
  `mcp_gate_dispatch.py`, ya existe en KDD) + tres pieles (MCP ya existe,
  CLI `--json` nuevo, TUI en Go+Bubble Tea nuevo que shellea al CLI sin
  reimplementar lógica).
- Decisión de stack: Go + Bubble Tea para el TUI (no Python+Textual) —
  elegido a pesar de requerir un puente CLI en vez de import directo,
  porque encaja con la tradición real del género lazyapp (mismo autor de
  lazygit) y distribuye como binario único. Hace de este el primer
  proyecto KDD genuinamente multi-lenguaje (Python core + Go TUI).
- Capacidades objetivo listadas (correr gates, browsing de contratos,
  scaffolding desde TEMPLATE, estado de ciclo de vida) SIN fasear
  todavía — el orden real se decide al empezar a escribir contratos.
- Todavía NO hay contratos CCDD ni código: por diseño, esos se escriben
  tarea por tarea, justo antes de delegar cada una.

## Próximo paso (pendiente, no ejecutado)

1. `python scripts/init_project.py --apply --name "lazykdd"`.
2. Fasear las capacidades objetivo en tareas atómicas y escribir el
   primer task contract (probablemente: el comando `kdd gates run-all
   --json`, la pieza más chica y ya con lógica 100% resuelta en
   `mcp_gate_dispatch.py`).
3. Agregar una entrada acá por cada milestone real (primer contrato verde,
   primera delegación a un agente efímero, primer incidente, etc.) — la
   evidencia de que el método se siguió, no una narración post-hoc.
