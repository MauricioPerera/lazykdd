# Contrato 05 — Integración del gate CCDD nivel 2 real

Prerrequisitos: Contratos 01-04 (80 tests, ciclo demostrado). El README declara el nivel 2
(gate real vía MCP `ccdd-complexity`) como opcional pero no había forma probada de usarlo.
Sonda de viabilidad ejecutada por el orquestador con el gate REAL (2026-07-04):

- `lint_task_contract` ACEPTA el formato híbrido OKF+CCDD (contrato de C04 en versión
  ASCII → `ok: true, 0 errors`, tests referenciados).
- Fricción 1 — **encoding**: el mismo contrato con acentos/em-dashes españoles falla
  (INVALID en lint leyendo del disco; y errores de surrogates en el transporte MCP,
  reproducidos 2×).
- Fricción 2 — **rutas**: el gate resuelve `target`/`tests` relativos al `.md` del
  contrato; KDD los declara relativos a la raíz del repo.

FIX: un exportador determinista que emite la variante gate-nativa de un contrato KDD.
Los contratos fuente NO cambian (el español con acentos es legítimo en la KB); el export
es un artefacto derivado.

## E-GATE (T1) — `scripts/export_gate_contract.py` + docs de nivel 2

1. CLI: `python scripts/export_gate_contract.py <contrato.md> [--out-dir .agents/gate-exports]`
   → escribe `<out-dir>/<task>.md` con: (a) **normalización ASCII** de todo el texto
   (NFKD sin diacríticos; `—`/`→`/`≤` etc. a equivalentes ASCII `-`/`->`/`<=`; cualquier
   otro no-ASCII eliminado de forma segura), preservando intactas las claves ya-ASCII
   críticas (`signature`, rutas, código); (b) **reescritura de `target` y `tests`** para
   que resuelvan relativos a la ubicación del export (p. ej. desde
   `.agents/gate-exports/`: `../../src/users.py`); (c) el resto del contrato verbatim.
   Determinista: mismo input → export byte-idéntico. Exit 0 ok · 1 I/O · 2 contrato sin
   frontmatter/claves necesarias.
2. `.gitignore`: agregar `.agents/gate-exports/` (artefacto derivado, no fuente).
3. Docs de nivel 2: en README (sección "Nivel 2") y `.agents/AGENTS.md` (regla 4, nivel
   2), añadir 1-2 líneas: el gate real se corre sobre el EXPORT
   (`export_gate_contract.py`), con `lint_task_contract` (texto del export + tests) y
   `run_integration_gate` (ruta del export). Sin duplicar doc.
4. Tests `unittest` (`tests/test_export_gate_contract.py`): normalización ASCII (salida
   100 % ASCII; acentos/em-dashes/flechas mapeados), reescritura de rutas correcta,
   idempotencia/determinismo byte a byte, frontmatter preservado en claves y orden,
   contrato real de C04 exportado queda ASCII con rutas válidas (los archivos apuntados
   existen), exit codes.

## Criterios de aceptación

- [ ] Suite `unittest` verde (80 + nuevos), 2× al cierre; ambos validadores exit 0.
- [ ] Export del contrato de C04 → 100 % ASCII, rutas `target`/`tests` resuelven desde el
  export a archivos existentes.
- [ ] **Evidencia del gate REAL (la produce el orquestador, que tiene el MCP):**
  `lint_task_contract` sobre el export → `ok: true`; `run_integration_gate` sobre el
  export en disco → veredicto registrado en el reporte del contrato (PASS esperado; si
  falla por causa ambiental del gate, se documenta el detalle tal cual — honestidad sobre
  optimismo).
- [ ] CI sin cambios de pasos (el discover recoge los tests nuevos).

## Restricciones

- Tocar SOLO: `scripts/export_gate_contract.py` (nuevo), `tests/test_export_gate_contract.py`
  (nuevo), `.gitignore` (1 línea), README (sección nivel 2, mínimo), `.agents/AGENTS.md`
  (regla 4, mínimo). NO tocar contratos existentes, validadores, ensamblador, src/, ccdd/.
- Python stdlib puro; sin red; sin subprocess en el target; determinista.
- NO commitear. Si algo no se puede sin romper otro criterio, PARAR y reportar.
