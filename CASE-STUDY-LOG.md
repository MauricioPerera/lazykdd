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

## 2026-07-14 — Instanciación de la plantilla

- `python scripts/init_project.py --apply --name "lazykdd"`: 50 archivos
  de ejemplo eliminados (dominios de pagos, fronteras, workflows, ruteo,
  editorial, MCP registry, agent wiring, ejemplo Node), `knowledge/index.md`
  reescrito, H1 de `README.md` renombrado. `validate_contracts.py`: 0
  errores, 21 contratos remanentes (los propios de la plantilla, no de
  ejemplo). Commit `7a5fa1e`.

## 2026-07-14 — Piel 2 (CLI Python): las 4 capacidades objetivo

Cuatro tareas delegadas a instancias efímeras de GLM-5.2, cada una
verificada de forma independiente (Nivel 1, suite completa 2x, gate CCDD
en vivo, demo real end-to-end) antes de integrar — no solo por el reporte
del dev.

- `kdd gates run-all --json` (commit `6c05987`): primer subcomando,
  despacha al motor de gates existente (`mcp_gate_dispatch.py`).
- `kdd contracts list --json` (`3b27047`): browsing, reusa
  `validate_contracts.parse_frontmatter`/`_collect_files`.
- `kdd contracts scaffold <task> --json` (`5c8132c`): crea contratos desde
  `TEMPLATE-task-contract.md`, valida kebab-case, nunca sobreescribe.
- `kdd contracts status --json` (`fc4e490`): ciclo de vida
  draft/validated/implemented/verified por contrato, reusa
  `validate_test_commands.run_all`.

Bug real encontrado al verificar (`e59d0e7`, `0cd6bde`): el gate CCDD
externo (`ccdd-complexity` MCP) resolvía `target`/`tests` siempre
relativos al directorio del contrato, incompatible con la convención de
esta plantilla (rutas relativas a la raíz). Arreglado en el repo externo
`MauricioPerera/ccdd-gate` (fallback a la raíz del repo vía ancestro con
`.git`), PR [#100](https://github.com/MauricioPerera/ccdd-gate/pull/100)
mergeado. De paso, destapado un segundo bug: las claves de budget del
frontmatter (`max_cyclomatic_complexity`/`max_nesting_depth`) nunca
coincidían con las que el gate real lee (`cyclomatic_max`/etc.) — Nivel 2
pasaba vacuo en los 21 contratos preexistentes. Arreglado en los 21 con
las métricas reales medidas.

## 2026-07-14 — Repo público

`gh repo create MauricioPerera/lazykdd --public`, verificado sin secretos
reales antes de publicar (`scan_secrets.py`). https://github.com/MauricioPerera/lazykdd

## 2026-07-14/15 — Piel 3 (TUI Go): bootstrap + interactividad completa

Primer proyecto KDD genuinamente multi-lenguaje: primer contrato
`language: go` del repo. Mismo bug de cwd que en la Piel 2 reapareció
específico de Go (`test_command` necesita `-C tui` + `test_cwd: ../..`
para satisfacer tanto el gate externo como el Nivel 1 propio de este
repo, que siempre corre `test_command` desde la raíz) — documentado
explícito en cada spec siguiente para no repetirlo.

- Bootstrap del módulo (`7bc9ae8`): `tui/go.mod`, smoke-testeado.
- `Summarize` (`480f2d9`): pipe no-interactivo Go→CLI Python probado
  primero, deliberadamente sin Bubble Tea.
- Primera capa interactiva con Bubble Tea (`4c5f75b`): arquitectura Elm,
  `UpdateModel`/`View` puras y testeadas, wiring de I/O separado.
- Segundo panel, contratos, toggle g/c (`7ce970f`).
- Tecla `r`, refresco sin reiniciar (`9aa771d`): recursión evitada
  (`Init()` dispara `gates run-all`, que corre `go test` de este mismo
  contrato — pipe tests reales opt-in vía env var).
- Scaffolding interactivo, tecla `n` (`6ed96d1`): cierra la última
  capacidad mayor de `DEFINITION.md`. `UpdateModel` refactorizada a
  dispatcher delgado por primera vez (ya estaba cerca del tope de
  complejidad) — patrón reusado en la tarea siguiente.
- Panel de contratos navegable + lectura de detalle (`68d2684`): flechas +
  Enter leen el `.md` real de disco (`os.ReadFile` directo, no shell-out
  — única excepción documentada a "el TUI siempre pasa por el CLI",
  justificada por ser I/O trivial sin lógica de negocio).

## 2026-07-15 — Deuda técnica: 7 funciones sobre-complejas refactorizadas

El bug de mismatch de claves de budget (ver arriba) había estado
enmascarando complejidad real en 6 funciones de la plantilla heredada,
destapada recién al arreglarlo. Los 7 refactors (cyclomatic o
`function_length` real, no lo que el contrato viejo declaraba) son
puros de comportamiento: oráculo congelado intocado (hash idéntico
verificado en cada uno) + comparación A/B independiente contra el
original (`git show HEAD:<archivo>` cargado como módulo aparte) con
casos propios distintos a los de cada dev, no solo el reporte.

| Función | Antes → Después | Commit |
|---|---|---|
| `rule_engine.py::evaluate` | cyclomatic 101 → 10 | `b58b5ed` |
| `assemble_context.py::assemble` | cyclomatic 29 → 7 | `4b1b17c` |
| `validate_skills.py::validate_skills` | cyclomatic 27 → 7 | `5097a7e` |
| `export_gate_contract.py` | lines 93 → 65 | `6e1062d` |
| `validate_rules.py::validate_rules` | lines 104 → 22 | `e592c34` |
| `validate_changelog.py` | lines 84 → 38 | `c345a10` |
| `validate_perimeter.py` | lines 83 → 33 | `8076507` |

## 2026-07-15 — CI real corriendo Go

El CI público nunca había corrido Go: el step "Run project test suite"
seguía siendo el placeholder no-op heredado de la plantilla. Agregado
`actions/setup-go` + `go -C tui test ./...` + `go -C tui build` (`7cbcd25`),
más `cache-dependency-path: tui/go.sum` (`7b9fbf6`). Verificado en
GitHub real (no solo local): ambas plataformas (ubuntu-latest,
windows-latest) verdes, sin anotaciones bloqueantes.

## Pendiente conocido (no ejecutado, documentado explícito)

- Correr un gate individual (no solo los 11 juntos) — único hueco literal
  de `DEFINITION.md` sin cubrir, ni en el CLI ni en el TUI.
- Sin proceso de release/distribución del binario Go.
- `ccdd-gate` tiene ~13 sitios más con el mismo patrón de resolución de
  rutas que se arregló solo en `tc_lint`/`task_gate` — no tocado.
- Limitaciones de UX del TUI aceptadas: carreras en refrescos repetidos,
  sin scroll en el detalle de contrato, `r` durante el detalle dispara un
  refresh silencioso, sin colores/estilos, sin búsqueda/filtro.
