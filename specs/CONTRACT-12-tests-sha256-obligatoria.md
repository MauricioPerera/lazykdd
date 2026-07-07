# Contrato 12 — `tests_sha256` obligatoria: todo oráculo queda congelado por máquina

Prerrequisitos: contratos 01-11 cerrados, HEAD `e4fbd15`, suite 148 verde 2×, CI verde en
ambas patas. C10/T1 introdujo `tests_sha256` como opcional (ausente = WARNING): el sello
existe pero sigue siendo opt-in — un contrato nuevo sin la clave pasa CI en verde y su
oráculo queda sin congelar. Pendiente declarado en `docs/reports/CONTRACT-10-REPORT.md`.
RECON (2026-07-07): los 8 contratos del repo ya están sellados; los fixtures de T1 ya
ejercitan la clave; la doc normativa (`knowledge/validacion.md`, skill
`kdd-okf-ccdd-hybrid`) aún no menciona `tests_sha256` (0 hits).

> Capa: este es un **contrato de ejecución** (nivel proyecto). Las tareas que impliquen código
> delegado a un agente efímero llevan además su **task contract** CCDD en
> `knowledge/contracts/<task>.md` (validado por `scripts/validate_contracts.py`).

Decisión de diseño (fijada acá, no la decide el dev): obligatoria para **TODO** task
contract — sin heurísticas ni markers para distinguir "oráculo pre-delegación" de
"tooling": la distinción es un hecho del proceso, no derivable del archivo, y un sello
universal es determinista y simple. El costo para el autor se paga con un helper.

## SHA-OBLIGATORIA (T1) — ausente pasa de WARNING a ERROR + helper de sellado + doc

FIX/OBJETIVO:
1. `scripts/validate_contracts.py`: la clave `tests_sha256` pasa a REQUERIDA — ausente o
   vacía = ERROR `FM_TESTS_FROZEN` (hoy WARNING). Las reglas existentes no cambian:
   presente con hash distinto = ERROR con ambos hashes; formato inválido = ERROR; si
   `tests` no existe, `FM_PATH_tests` reporta sin duplicar error de hash.
2. Helper de sellado: `python scripts/validate_contracts.py --hash RUTA` imprime el
   sha256 normalizado (LF) de ese archivo y sale con exit 0 — el autor sella sin
   "correr a fallar". Determinista, stdlib, mismo algoritmo que la verificación (un solo
   camino de cálculo compartido, no dos implementaciones).
3. `tests/test_validate_contracts.py`: el test "ausente = WARNING" se invierte a
   "ausente = ERROR y CLI exit 1"; los fixtures que hoy omiten la clave se sellan con el
   helper/algoritmo; test nuevo del `--hash` (imprime el hash correcto del fixture y
   coincide con el que la validación acepta). No debilitar ningún test existente.
4. Doc normativa alineada (hoy 0 menciones): `knowledge/validacion.md` (nodo canónico,
   sección nivel 1) gana 2-3 líneas: qué es `tests_sha256`, que es obligatoria, cómo
   sellar con `--hash`, y que el hash se recalcula en cada cambio legítimo del oráculo
   (el diff del sello hace visible el cambio en review). La skill
   `.agents/skills/kdd-okf-ccdd-hybrid/SKILL.md` agrega la clave a su lista de CCDD
   Fields (sección 2) y al ejemplo de frontmatter, referenciando `validacion.md` sin
   duplicar (regla de no-duplicación OKF §4).

Invariantes: los 8 contratos del repo ya sellados → el repo pasa con 0 errores y 0
warnings sin editar contratos; `init_project --apply` sigue dejando los 3 gates verdes en
la copia; el parser de frontmatter NO se toca (`test_parser_coherence` lo fija); el
export gate-nativo no cambia; `test_agents_rules` sigue verde (la skill conserva sus
referencias al ensamblador).

Trade-off aceptado (documentarlo en `validacion.md`, no ocultarlo): es un cambio de
formato para proyectos ya instanciados desde la plantilla — sus contratos sin sello
pasarán de WARNING a ERROR al actualizar el validador. Mitigación: el mensaje de ERROR de
clave ausente debe nombrar el comando de sellado (`--hash`) para que el fix sea un
copy-paste.

## Criterios de aceptación

- [ ] `python scripts/validate_contracts.py knowledge/contracts` exit 0 sobre el repo
  (8 contratos, 0 errores, 0 warnings).
- [ ] Mutación (fixture): contrato sin `tests_sha256` → exit 1 con ERROR
  `FM_TESTS_FROZEN` cuyo mensaje menciona `--hash`; con la clave sellada → exit 0.
- [ ] Helper: `python scripts/validate_contracts.py --hash tests/test_sample.py`
  imprime 64 hex y exit 0; sellar un fixture con ese valor lo deja en verde.
- [ ] Doc: `grep -n "tests_sha256" knowledge/validacion.md
  .agents/skills/kdd-okf-ccdd-hybrid/SKILL.md` con hit en ambos archivos.
- [ ] `python scripts/validate_specs.py specs` exit 0,
  `python scripts/validate_okf.py knowledge` exit 0 y
  `python -m unittest tests/test_agents_rules.py` OK.
- [ ] Final: `python -m unittest discover -s tests -p "test_*.py"` suite completa 2×
  verde (dos corridas idénticas); CI verde en ambas patas.

## Restricciones

- Tocar SOLO: `scripts/validate_contracts.py`, `tests/test_validate_contracts.py`,
  `knowledge/validacion.md`, `.agents/skills/kdd-okf-ccdd-hybrid/SKILL.md`.
- Los contratos de `knowledge/contracts/` NO se tocan (ya están sellados); los specs
  `CONTRACT-01..11` y sus reportes son históricos: read-only.
- Python stdlib puro en el target; sin red; sin subprocess en el script (los tests sí
  pueden usar subprocess para el CLI).
- NO commitear (el PM commitea por tarea verificada). Si algo no se puede sin romper otro
  criterio, PARAR y reportar.
- ABORTAR SI: mantener verde un test existente exigiera cambiar su lógica más allá de
  sellar fixtures; o la obligatoriedad rompiera `init_project`/`test_init_project` de una
  forma que exija tocar archivos fuera del perímetro; o el helper no pudiera compartir el
  camino de cálculo con la verificación sin refactor fuera de alcance -> PARAR,
  documentar el porqué con evidencia en el reporte y marcar BLOQUEADO.

## Checklist antes de delegar

- [x] RECON corrido (2026-07-07): 8/8 contratos con `tests_sha256` (grep); fixtures de
  T1 ya ejercitan la clave; 0 menciones en `validacion.md`/skill/README; suite 148 verde
  2× y CI verde en ambas patas en el HEAD de partida.
- [x] Todo criterio tiene comando + resultado esperado.
- [x] Red-team hecho: el helper comparte el camino de cálculo con la verificación (dos
  implementaciones podrían divergir y sellar hashes que la validación rechaza); el
  mensaje de ausente nombra `--hash` (sin eso, cada autor redescubre el sellado); los
  contratos del repo no se editan, así que un dev no puede "arreglar" un rojo re-sellando
  el repo real.
- [x] Perímetro declarado; una sola tarea, sin concurrencia.
- [x] Condiciones de aborto explícitas (con `->` legítimo — permitido desde C10/T3).
