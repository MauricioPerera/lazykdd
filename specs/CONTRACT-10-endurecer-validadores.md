# Contrato 10 — Endurecer el nivel 1: oráculo congelado por máquina, rutas existentes y placeholders honestos

Prerrequisitos: contratos 01-09 cerrados, HEAD `fe9c185`, suite 136 verde 2×, los 3
validadores exit 0. Tres huecos donde la promesa determinista del nivel 1 aún depende de
disciplina humana: el oráculo congelado se verifica a mano (en C04 fue hash manual del PM),
un `target`/`tests` renombrado sin actualizar el contrato pasa CI en verde, y la regla
ABORTAR de `validate_specs` prohíbe los caracteres de ángulo crudos — un `->` legítimo en
el bullet da falso ERROR (reproducido en RECON, 2026-07-07).

> Capa: este es un **contrato de ejecución** (nivel proyecto). Las tareas que impliquen código
> delegado a un agente efímero llevan además su **task contract** CCDD en
> `knowledge/contracts/<task>.md` (validado por `scripts/validate_contracts.py`).

Orden de ejecución: **T3 primero** (modifica `tests/test_validate_specs.py`), después
**T2**, y **T1 al final** porque sella los hashes del estado FINAL de los archivos de
tests. Las tareas comparten archivos (`validate-specs.md`, `validate_contracts.py`):
secuenciales, nunca concurrentes.

## SPECS-PLACEHOLDER (T3) — placeholder por patrón, no por caracteres sueltos

La regla ABORTAR de `scripts/validate_specs.py` marca ERROR si el texto del bullet
contiene `<` o `>` crudos. Falso positivo reproducido: un contrato abierto con
`- ABORTAR SI: ... -> PARAR y reportar.` da `ERROR [ABORTAR]` (exit 1) sin tener
placeholder alguno.

FIX/OBJETIVO: la regla detecta placeholders reales con el patrón `<[^<>\n]+>`
(`re.search`, stdlib) sobre el texto del bullet + sus líneas de continuación, en vez de
los caracteres sueltos. Invariantes: el caso `<condicion del template>` sigue dando ERROR;
`->` (y la flecha `→`) en el bullet pasan; los contratos 01-09 siguen pasando sin
editarse; el task contract `knowledge/contracts/validate-specs.md` (Invariants/Examples)
queda alineado con la regla nueva. Tests nuevos congelan ambos lados de la regla.

## PATHS-EXIST (T2) — target y tests deben existir

`validate_contracts.py` solo valida presencia de claves: un contrato cuyo `target` o
`tests` fue renombrado o borrado pasa el validador y CI en verde (drift silencioso
contrato↔repo).

FIX/OBJETIVO: `target` y `tests` deben resolver a archivos existentes; inexistente =
ERROR nombrando clave y ruta. Convención de raíz explícita (precedente C07/T9 del
exportador): las rutas del contrato se interpretan relativas a la raíz del repo,
`--repo-root` explícito con default `.` resuelto a absoluto; el paso de CI no cambia
(corre desde la raíz). Los tests fijan la convención con rutas explícitas sobre fixtures
que crean la estructura completa (raíz temporal con `knowledge/contracts/` + `src/` +
`tests/`), NO con el cwd implícito (auto-consistencia prohibida, lección de T9); los
fixtures existentes de `tests/test_validate_contracts.py` se actualizan para crear los
archivos apuntados. RECON verificado: los 8 contratos reales resuelven (target y tests
existen todos).

## FREEZE-ORACLE (T1) — el oráculo congelado lo verifica la máquina

Hoy "tests congelados" es disciplina del proceso, no gate: C04 lo verificó con hash
manual del PM y nada impide que un implementador edite su oráculo con la suite en verde.

FIX/OBJETIVO: clave opcional `tests_sha256` en el frontmatter del task contract — sha256
hex completo del contenido del archivo `tests`, leído UTF-8 con newlines normalizados a
LF antes de hashear. La normalización es OBLIGATORIA, no cosmética: este working tree
tiene LF en disco pero `core.autocrlf=true` (RECON), otro clon puede materializar CRLF y
un hash de bytes crudos rompería entre plataformas/checkouts. Reglas: clave presente con
hash distinto = ERROR nombrando archivo, esperado y actual; clave ausente = WARNING
(recomendada, no bloquea — compatibilidad con fixtures y proyectos ya instanciados).
Los 8 contratos del repo ganan la clave con su hash real, sellado TRAS T3 (T3 modifica
`tests/test_validate_specs.py`). Invariantes: el export gate-nativo no cambia (la clave
viaja verbatim: es hex ASCII); `init_project` sigue dejando los gates verdes en la copia
(los contratos de ejemplo se borran junto con sus tests; los de infra conservan hashes
válidos); mutar cualquier archivo de tests referenciado pone `validate_contracts` (y por
lo tanto CI) en rojo.

## Criterios de aceptación

- [ ] `python scripts/validate_contracts.py knowledge/contracts` exit 0 sobre el repo
  (8 contratos con `tests_sha256` vigente, 0 errores, 0 warnings por hash).
- [ ] Mutación T1 (sobre fixture o copia, nunca el repo real): editar el archivo de tests
  referenciado → `python scripts/validate_contracts.py` sobre el fixture da exit 1 con
  ERROR que nombra el archivo y ambos hashes.
- [ ] Mutación T2: fixture con `target` inexistente → exit 1 nombrando la ruta; fixture
  íntegro → exit 0.
- [ ] T3: fixture abierto con `->` en su ABORTAR SI → `python scripts/validate_specs.py`
  sobre el fixture da exit 0; con `<placeholder>` → exit 1.
- [ ] `python scripts/validate_specs.py specs` exit 0 y
  `python scripts/validate_okf.py knowledge` exit 0 sobre el repo.
- [ ] Final: `python -m unittest discover -s tests -p "test_*.py"` suite completa 2×
  verde (dos corridas idénticas); CI verde.

## Restricciones

- Tocar SOLO (secuencial, en este orden):
  - T3: `scripts/validate_specs.py`, `tests/test_validate_specs.py`,
    `knowledge/contracts/validate-specs.md`.
  - T2: `scripts/validate_contracts.py`, `tests/test_validate_contracts.py`.
  - T1: `scripts/validate_contracts.py`, `tests/test_validate_contracts.py`, y los 8
    `knowledge/contracts/*.md` SOLO para agregar la clave `tests_sha256` (ningún otro
    cambio en los contratos).
- Los contratos `specs/CONTRACT-01..09` y sus reportes son históricos: read-only.
- Python stdlib puro en los targets; sin red; sin subprocess en los scripts (los tests sí
  pueden usar subprocess para los CLI).
- NO commitear (el PM commitea por tarea verificada). Si algo no se puede sin romper otro
  criterio, PARAR y reportar.
- ABORTAR SI: sellar los hashes exigiera editar un contrato histórico de specs o relajar
  un check existente; o la normalización LF no bastara para hashes estables entre
  plataformas; o un test existente no pudiera seguir verde sin cambiar su lógica más allá
  de los fixtures autorizados. En ese caso PARAR, documentar el porqué con evidencia en el
  reporte y marcar BLOQUEADO.

## Checklist antes de delegar

- [x] RECON corrido (2026-07-07): falso positivo de `->` reproducido con fixture propio
  (`ERROR [ABORTAR]`, exit 1); los 8 contratos reales tienen `target` y `tests`
  existentes; working tree con LF en disco y `core.autocrlf=true` → la normalización de
  newlines del hash es obligatoria; suite 136 verde 2× en este host Windows.
- [x] Todo criterio tiene comando + resultado esperado.
- [x] Red-team hecho: un validador que siempre devuelve 0 no pasa las mutaciones; los
  hashes se sellan tras T3 para que el orden no deje un hash stale; la clave ausente es
  WARNING para no romper fixtures ni proyectos instanciados; la mutación de oráculo se
  prueba sobre copia, nunca sobre el repo real.
- [x] Perímetro declarado por tarea; tareas secuenciales (comparten archivos; el orden
  T3, T2, T1 importa).
- [x] Condiciones de aborto explícitas.
