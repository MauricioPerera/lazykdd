# Contrato 28 — Perímetro verificable: "Tocar SOLO" pasa de prosa a máquina

Prerrequisitos: contratos 01-27 cerrados, HEAD `52b10ba`+, suite 341 verde 2×, CI verde
en ambas patas. Idea importada del análisis de Shepherd (shepherd-agents, arXiv
2605.10913): allí la firma de una task ES su superficie de permisos, forzada en el
syscall. El nivel correcto para KDD (plantilla cross-platform, sin jail) es la
verificación POST-HOC del diff: el contrato declara el perímetro como dato y un gate
verifica que los archivos tocados por el dev caigan dentro. Evidencia propia: el PM
verificó el perímetro A MANO con `git status` en C24, C25, C26 y C27 — práctica manual
repetida ⇒ gate, por doctrina.

RECON (2026-07-08): 19 task contracts; solo 4 declaran "Tocar SOLO" en prosa; 2 casos
borde con `target == tests` (agents-context-rule, versioning-plantilla: el entregable ES
un test). `tests/test_validate_contracts.py` es test de INFRA sin sello (libre de
reforzar sin re-sellado). El parser mini-YAML tiene 3 copias fijadas a 3 vías.

> Capa: contrato de ejecución. T1 (código, dev efímero) lleva su task contract en
> `knowledge/contracts/perimeter-gate.md`. T2 (refuerzo de oráculo de infra + migración
> de los 19 contratos + docs) es del orquestador. El gate nuevo es INFRAESTRUCTURA.

Decisiones de diseño (fijadas acá):
- **`touch_only:`** clave OBLIGATORIA del frontmatter de task contracts (precedente
  C12: tests_sha256 de prosa a clave): lista inline no vacía de rutas/patrones
  repo-relativos estilo posix, semántica `fnmatch` (un `*` cruza `/`; documentado).
- **Checks estructurales en `validate_contracts.py`** (corren en CI vía el gate
  existente): `FM_KEY_touch_only` (presencia, vía REQUIRED_KEYS); `FM_TOUCH_ONLY`
  (forma: lista no vacía de strings no vacíos); `FM_TOUCH_TARGET` (el `target` debe
  estar cubierto por el perímetro — un dev que no puede tocar su target es un contrato
  roto); `FM_TOUCH_TESTS` (el archivo `tests` NO debe estar cubierto — el oráculo
  congelado queda FUERA del perímetro — SALVO cuando `tests == target`, el caso
  contrato-cuyo-entregable-es-un-test).
- **Gate nuevo `scripts/validate_perimeter.py`** (herramienta del PM en verificación,
  con oráculo congelado en la suite — que SÍ corre en CI): recibe el contrato y la
  lista de archivos cambiados (stdin, uno por línea, o `--changed f1 f2 ...`) y falla
  si alguno cae fuera de `touch_only`. El `git diff --name-only` lo corre el CALLER
  (PM o pipeline): el gate queda stdlib puro, sin subprocess, determinista y testeable.
  Honestidad de alcance: NO se agrega como paso de CI del repo — un commit mergeado
  mezcla legítimamente archivos del PM; el diff del DEV solo existe en el momento de la
  verificación, y ahí es donde este gate corta. La cobertura de CI viene por (a) los
  checks estructurales en validate_contracts y (b) el oráculo del gate en la suite.
- Cuarta copia del parser mini-YAML en el gate nuevo; `test_parser_coherence` se
  extiende a 4 vías (precedente C24).
- Lista vacía de cambiados → exit 0 con Resumen honesto (nada cambiado = dentro).

## T1 — `validate_perimeter.py` + checks en `validate_contracts.py` (dev efímero)

OBJETIVO: (a) implementar `scripts/validate_perimeter.py` contra el oráculo congelado
`tests/test_validate_perimeter.py` (sellado por el PM); (b) agregar los 4 checks
estructurales a `scripts/validate_contracts.py` contra `tests/test_validate_contracts.py`
REFORZADO por el PM antes de delegar (test de infra, sin sello); (c) extender
`tests/test_parser_coherence.py` a 4 vías. Estilo validate_skills; findings
`{'file','level','rule','msg'}`; ASCII; stdlib.

## T2 — Migración + docs (autoría del orquestador)

`touch_only:` en los 19 contratos existentes (derivado de su `target` + los 4 con prosa
+ los perímetros reales de C24/C25) ANTES de delegar (el DoD del dev exige
validate_contracts verde con la clave obligatoria); task contract nuevo (con su propio
`touch_only`, auto-ejemplar); `knowledge/validacion.md` (la clave y el gate del PM);
README EN/ES (mención breve); `.agents/AGENTS.md` si aplica; CHANGELOG; reporte.

## Criterios de aceptación

- [ ] `python -m unittest tests/test_validate_perimeter.py` verde SIN modificar el
  oráculo (sellado).
- [ ] `python -m unittest tests/test_validate_contracts.py` verde (reforzado por PM).
- [ ] `python scripts/validate_contracts.py knowledge/contracts` exit 0 con los 20
  contratos migrados (clave obligatoria).
- [ ] Dogfood real: `git diff --name-only` del propio batch de C28 filtrado al
  perímetro del dev → `validate_perimeter` exit 0 contra
  `knowledge/contracts/perimeter-gate.md`; con un archivo fuera inyectado → exit 1
  nombrándolo.
- [ ] Mutación PM: quitar `touch_only` de una copia de contrato → `FM_KEY_touch_only`;
  perímetro que cubre el oráculo (tests != target) → `FM_TOUCH_TESTS`.
- [ ] `test_parser_coherence` OK a 4 vías; los 7 gates exit 0; suite 2× verde.
- [ ] Final: CI verde en ambas patas.

## Restricciones

- Tocar SOLO — T1 (dev): `scripts/validate_perimeter.py`,
  `scripts/validate_contracts.py` (SOLO agregar los checks nuevos; sin debilitar),
  `tests/test_parser_coherence.py` (SOLO extender a 4 vías) (+ su REPORT local). T2
  (orquestador): `tests/test_validate_perimeter.py` (nuevo, congelado),
  `tests/test_validate_contracts.py` (SOLO reforzar, antes de delegar),
  `knowledge/contracts/*.md` (SOLO agregar `touch_only:` + el contrato nuevo),
  `knowledge/validacion.md`, `README.md`, `.agents/AGENTS.md`, `CHANGELOG.md`, el spec
  y el reporte.
- Los sellos `tests_sha256` existentes NO cambian (la migración toca frontmatter de
  contratos, jamás archivos de tests sellados).
- Los specs `CONTRACT-01..27` y sus reportes son históricos: read-only.
- Python stdlib puro; sin red; sin subprocess; mensajes ASCII; determinista.
- NO commitear hasta verificar. Si algo no se puede sin romper otro criterio, PARAR y
  reportar.
- ABORTAR SI: la migración exigiera cambiar CONTENIDO de un contrato histórico más
  allá de agregar la clave (eso es un hallazgo para decidir con el usuario); o el caso
  `target == tests` no pudiera expresarse sin debilitar la exclusión del oráculo para
  el resto. PARAR y documentar.

## Checklist antes de delegar

- [x] RECON corrido (2026-07-08): 19 contratos mapeados a su touch_only (target + 4
  prosas + perímetros reales de C24/C25); caso borde target==tests identificado en 2
  contratos y resuelto en el diseño; oráculo de validate_contracts confirmado SIN
  sello (infra); parser en 3 copias listas para la 4ª.
- [x] Todo criterio tiene comando + resultado esperado.
- [x] Red-team hecho: el gate NO va a CI del repo (los commits mezclan PM+dev — se
  documenta el porqué, no se finge cobertura); fnmatch documentado (un `*` cruza
  `/`); lista vacía definida; el contrato nuevo se auto-verifica (dogfood en el DoD).
- [x] Perímetro declarado; una tarea de código (T1); migración del orquestador (T2).
- [x] Condiciones de aborto explícitas.
