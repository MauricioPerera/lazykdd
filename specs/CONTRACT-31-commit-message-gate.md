# Contrato 31 — Formato de mensaje de commit: la frontera mecánico/juicio en git

Prerrequisitos: contratos 01-30 cerrados, HEAD `f082393`, suite 433 verde 2×, CI verde en
ambas patas. Nace de una pregunta directa del usuario ("¿podría tener contratos para git:
issues, PRs, commits?"). RECON honesto: este repo NO tiene `.github/PULL_REQUEST_TEMPLATE.md`
ni `ISSUE_TEMPLATE/`, y su propio historial de commits (`C30: ...`, `release: vX.Y.Z ...`,
`docs: ...`) NO sigue Conventional Commits — es una convención informal de esta sesión, no
un estándar documentado. Alcance deliberadamente ACOTADO a una sola cosa limpia (precedente:
separar C24 de C25 en vez de mezclar skills+MCP): SOLO formato de mensaje de commit.
Plantillas de PR/issue quedan para un contrato futuro (evidencia insuficiente hoy: cero
plantillas reales en este repo para calibrar contra ellas).

> Capa: contrato de ejecución. T1 (código, dev efímero) lleva su task contract en
> `knowledge/contracts/commit-message-gate.md`. T2 (ejemplo + cableado + docs) es del
> orquestador. Herramienta OPT-IN, NO gate de CI de este repo — el propio historial de KDD
> no sigue esta convención; forzarla retroactivamente sería absurdo. Es infraestructura de
> plantilla para que un proyecto instanciado la adopte en su propio commit-msg hook/CI si
> quiere (mismo estatus que `benchmark_gates.py`: existe, se prueba, no se impone).

Honestidad de alcance — la MISMA frontera mecánico/juicio que ya midieron C23/C30, con
la MISMA disciplina de C28/C30: calibrar contra un estándar público real, no inventar
reglas propias. Calibrado contra
[Conventional Commits v1.0.0](https://www.conventionalcommits.org/) (el estándar de facto)
y las reglas por defecto de `commitlint` (linter de referencia del ecosistema):

**Mecánico, contratable (parsing de texto puro, sin git, sin subprocess)**:
- `HEADER_MALFORMED` (ERROR) — la primera línea no matchea la gramática
  `tipo(scope opcional)!?: descripción`.
- `TYPE_UNKNOWN` (ERROR) — el `tipo` no está en la lista configurada (dato, no
  hardcodeado — ver más abajo).
- `SCOPE_REQUIRED` (ERROR) — la config exige scope y no hay `(scope)`.
- `BLANK_LINE_MISSING` (ERROR) — hay cuerpo (línea 3+) pero la línea 2 no está en blanco;
  regla real de Git mismo (`git commit`, `git log --format`), no inventada.
- `SUBJECT_TOO_LONG` (WARNING) — el header excede el largo configurado. WARNING porque
  commitlint lo trae como regla configurable de nivel warning por defecto, no hard error.
- `SUBJECT_TRAILING_PERIOD` (WARNING) — la descripción termina en punto; regla real de
  commitlint (`subject-full-stop`), WARNING por el mismo motivo.

**Frontera declarada, FUERA (no este contrato)**:
- Si el commit realmente introduce un breaking change y lo declaró bien (`!` o footer
  `BREAKING CHANGE:`) — no se puede verificar desde el TEXTO del mensaje solo, exigiría
  conocer el diff real; fuera de alcance.
- Plantillas de PR/issue reales en GitHub, o verificar PRs/issues vía API — exige red;
  fuera del nivel 1 por doctrina (mismo argumento del servidor MCP vivo en C25).
- Si el mensaje EXPLICA BIEN el por qué del cambio — juicio humano, declarado fuera, misma
  lección de C23/C30. "Verificar un PR y mergear" YA EXISTE como patrón sin nombre nuevo:
  CI verde en ambas patas antes de cerrar un contrato (esta sesión, cada contrato) y rama
  protegida + 2 checks obligatorios (`ccdd-gate`) — no se reconstruye acá, solo se
  documenta la referencia cruzada en el nodo de este contrato.

## T1 — `scripts/validate_commit_message.py` (dev efímero)

OBJETIVO: implementar contra el oráculo congelado
`tests/test_validate_commit_message.py` (autorado y sellado por el orquestador):
`parse_commit_message(msg) -> dict|None` (grafo de la gramática: type, scope, bang,
description, body, header) y `check_commit_message(msg, config) -> list` (findings
`{'level','rule','msg'}` — SIN 'file': un mensaje de commit no es un archivo del repo).
`config` es un dict simple: `{'types': [...], 'scope_required': bool,
'max_subject_length': int}`. `main(argv) -> int`: CLI que lee el mensaje desde
`--message <texto>`, `--file <ruta>`, o `-` (stdin, para uso real en un hook
`commit-msg`), y la config desde un JSON (path posicional); exit 1 solo si hay ≥1 ERROR.
Estilo `validate_changelog.py`; ASCII; stdlib puro (`re`, `json`).

## T2 — Ejemplo + cableado (autoría del orquestador)

`examples/git/commit-convention.json` (config EXAMPLE con los tipos reales de
Conventional Commits: feat, fix, docs, refactor, test, chore, build, ci, perf, revert;
`scope_required: false`; `max_subject_length: 72`); artefacto al MANIFEST de
`init_project`; `knowledge/data_models/commit_message_contract.md` (la gramática, la
tabla de severidad, la frontera, y la referencia cruzada explícita al patrón
"CI verde en ambas patas antes de cerrar" ya en uso, sin construirlo de nuevo); índice;
README EN/ES (mención breve, dejando claro que NO es paso de CI de este repo);
`knowledge/validacion.md`; CHANGELOG.

## Criterios de aceptación

- [ ] `python -m unittest tests/test_validate_commit_message.py` verde SIN modificar el
  oráculo.
- [ ] `python scripts/validate_commit_message.py examples/git/commit-convention.json --message "feat(gate): agrega validador de commits"` → exit 0.
- [ ] Mutación PM (fixtures propias): mensaje sin `:` en el header →
  `HEADER_MALFORMED` (ERROR), exit 1; mensaje con tipo inventado ("banana: algo") →
  `TYPE_UNKNOWN` (ERROR); header de 100 caracteres → `SUBJECT_TOO_LONG` (WARNING),
  exit SIGUE en 0 (WARNING no bloquea).
- [ ] `.github/workflows/validate.yml` NO se toca — se verifica explícitamente que no
  hay paso nuevo de CI en este contrato (grep negativo).
- [ ] Los 8 gates existentes exit 0; suite completa 2× verde; post-init neutral (el
  ejemplo se borra).
- [ ] Final: CI verde en ambas patas (sin cambios al workflow).

## Restricciones

- Tocar SOLO — T1 (dev): `scripts/validate_commit_message.py` (+ su REPORT local). T2
  (orquestador): `tests/test_validate_commit_message.py` (nuevo, congelado),
  `knowledge/contracts/commit-message-gate.md` (nuevo, sellado),
  `examples/git/commit-convention.json` (nuevo), `knowledge/data_models/
  commit_message_contract.md` (nuevo), `knowledge/index.md`, `scripts/init_project.py`
  (SOLO MANIFEST), `knowledge/validacion.md`, `README.md` (EN/ES), `CHANGELOG.md`, el
  spec y el reporte.
- `.github/workflows/validate.yml` NO se toca — esta herramienta NO es gate de CI de
  este repo (el propio historial de KDD no sigue esta convención).
- Los specs `CONTRACT-01..30` y sus reportes son históricos: read-only.
- Python stdlib puro; sin red; sin subprocess; sin llamadas a git; mensajes ASCII;
  determinista.
- NO commitear hasta verificar. Si algo no se puede sin romper otro criterio, PARAR y
  reportar.
- ABORTAR SI: la gramática de Conventional Commits no pudiera parsearse
  determinísticamente con una regex razonable (no debería pasar, es una gramática
  simple y pública); o el alcance empezara a exigir conocer el diff real (breaking
  changes) — eso es un hallazgo de frontera, no algo para forzar con una aproximación
  débil.

## Checklist antes de delegar

- [x] RECON corrido (2026-07-08): sin plantillas de PR/issue en este repo (alcance
  acotado a solo commits); historial propio de KDD no sigue Conventional Commits
  (declarado honestamente: la herramienta es opt-in, no retroactiva, no es gate de CI).
- [x] Evidencia del diseño: calibrado contra un estándar público real (Conventional
  Commits) y un linter de referencia (`commitlint`), no contra reglas inventadas —
  misma disciplina que C28 (Shepherd) y C30 (design.md).
- [x] Todo criterio tiene comando + resultado esperado.
- [x] Red-team hecho: "verificar un PR y mergear" reconocido como patrón YA EXISTENTE
  (CI ambas patas, rama protegida en ccdd-gate) en vez de reconstruido; breaking-change
  declarado explícitamente fuera de alcance (exigiría el diff, no solo el mensaje).
- [x] Perímetro declarado; una tarea de código (T1); ejemplo + cableado del
  orquestador (T2).
- [x] Condiciones de aborto explícitas.
