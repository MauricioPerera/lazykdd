# Contrato 18 — Gate de rule contracts: la vertiente se defiende sola

Prerrequisitos: contratos 01-17 cerrados, HEAD `50e7fc8`, suite 216 verde 2×, CI verde en
ambas patas. C17 dejó la vertiente probada pero sin gate propio: hoy nada exige que un
rule-set use solo familias soportadas, que tenga golden, que el golden esté sellado, ni
que las reglas `code_only` tengan razón — el único check vive en el test de equivalencia
del EJEMPLO (que se borra al instanciar). Este contrato le da a los rule contracts lo que
`validate_contracts` le da a los task contracts: un validador determinista de nivel 1 en
CI, con el oráculo (golden) congelado por hash.

> Capa: contrato de ejecución. La tarea de código (T1) lleva su task contract CCDD en
> `knowledge/contracts/rules-gate.md`.

Decisiones de diseño (fijadas acá):
- **Ubicación**: los rule contracts viven en un directorio propio fuera de `knowledge/`
  (en la plantilla: `examples/rules/`; la convención para proyectos: cualquier dir que se
  pase al CLI). Razón: un tipo OKF nuevo exigiría abrir el conjunto cerrado de
  `OKF-SPEC.md` §3 y los `.json` chocan con la regla de enlaces §4 — costo estructural que
  hoy no paga nada. La doc del dominio sigue siendo un nodo OKF normal que referencia el
  rule-set por ruta.
- **Sello del golden**: DENTRO del rule-set — clave `golden: {path, sha256}` (ruta relativa
  al rule-set; sha256 hex 64 del golden con newlines normalizados a LF, MISMO algoritmo
  que `tests_sha256`). Se sella con `python scripts/validate_contracts.py --hash <golden>`
  (helper existente, cero herramientas nuevas).
- **Capa opcional**: un proyecto sin rule contracts es válido. Directorio ausente o sin
  `*.rules.json` → INFO + exit 0 (así el paso de CI heredado queda verde post-init).

## T1 — `scripts/validate_rules.py` (validador determinista de rule contracts)

OBJETIVO: `def validate_rules(rules_dir: str) -> list:` + CLI espejo del estilo de
`validate_okf.py` (findings `{'file','level','rule','msg'}` ordenados; exit 0 sin ERRORs ·
1 con ≥1 ERROR; dir ausente o vacío → INFO y exit 0). Para cada `*.rules.json` del dir:

1. **Estructura**: JSON parseable; solo claves conocidas (`_comment`, las 7 familias de
   [rule-contract-spec](../knowledge/rule-contract-spec.md), `code_only`, `golden`);
   familia desconocida = ERROR nombrándola (un typo en una familia NO puede pasar en
   silencio como regla ignorada).
2. **`golden` obligatorio**: `{path, sha256}` presente; el archivo existe (relativo al
   rule-set); el sha256 LF-normalizado coincide — distinto = ERROR con ambos hashes
   (mensaje que nombra el comando de sellado); formato inválido = ERROR.
3. **Golden bien formado**: `refs` dict + `cases` lista no vacía; cada caso con `name`,
   `record` dict, `violations` lista, `code_only_miss` lista ⊆ `violations`.
4. **`code_only` con razón**: cada entrada tiene `reason` no vacía (la frontera se declara,
   no se insinúa).
5. **Reproducción (el gate semántico)**: el motor real (`rule_engine.evaluate`) sobre cada
   caso del golden reproduce `violations - code_only_miss` a nivel de campo top-level;
   cualquier divergencia = ERROR nombrando el caso y ambos conjuntos. Esto es lo que hace
   al validador un GATE y no un linter de forma.

Stdlib puro; sin red; sin subprocess; sin LLM; mensajes ASCII; determinista. El oráculo
`tests/test_validate_rules.py` lo autora el orquestador ANTES (fixtures en tempdir:
válido pasa; familia desconocida, golden sin sello, sello roto, code_only sin razón,
divergencia motor↔golden fallan; dir vacío/ausente exit 0 INFO; el ejemplo real del repo
pasa limpio) y queda congelado; el implementador solo escribe el script.

## T2 — Cableado (autoría del orquestador)

`examples/rules/payment-compliance.rules.json` gana su clave `golden` sellada;
`knowledge/rule-contract-spec.md` gana la sección de conformidad/ciclo de vida (válido =
estructura + sello vigente + motor reproduce el golden; verified = eso en CI) y la
convención de ubicación/sello; `.github/workflows/validate.yml` gana el paso
`python scripts/validate_rules.py examples/rules` (solo agregar); `knowledge/validacion.md`
y el resumen de nivel 1 del README (EN/ES) ganan una línea del gate nuevo (sin duplicar).

## Criterios de aceptación

- [ ] `python -m unittest tests/test_validate_rules.py` verde (oráculo congelado, sin
  modificarlo).
- [ ] `python scripts/validate_rules.py examples/rules` exit 0 sobre el repo (ejemplo de
  pagos con sello vigente y motor reproduciendo el golden).
- [ ] Mutación PM (sobre copia): editar un caso del golden → exit 1 `GOLDEN_FROZEN` con
  ambos hashes; familia con typo → exit 1 nombrándola; divergencia inyectada en el
  rule-set → exit 1 nombrando el caso.
- [ ] Dir vacío o ausente → exit 0 con INFO (capa opcional; post-init verde).
- [ ] `python scripts/validate_contracts.py knowledge/contracts` exit 0 (task contract
  nuevo sellado), `python scripts/validate_okf.py knowledge` exit 0,
  `python scripts/validate_specs.py specs` exit 0, `python scripts/lint_ascii.py scripts`
  exit 0, y `python -c "import yaml; yaml.safe_load(open('.github/workflows/validate.yml'))"`
  sin excepción.
- [ ] `python -m unittest discover -s tests -p "test_*.py"` suite completa 2× verde
  (incluye `test_init_project`: post-init el paso de rules queda verde por capa opcional).
- [ ] Final: CI verde en ambas patas.

## Restricciones

- Tocar SOLO — T1 (dev): `scripts/validate_rules.py` (+ su REPORT en `.agents/logs/`).
  T2 (orquestador): `examples/rules/payment-compliance.rules.json` (solo la clave golden),
  `knowledge/rule-contract-spec.md`, `knowledge/contracts/rules-gate.md` (nuevo),
  `tests/test_validate_rules.py` (nuevo, congelado), `.github/workflows/validate.yml`
  (solo agregar paso), `knowledge/validacion.md` y `README.md` (línea del gate, EN/ES),
  `knowledge/index.md` solo si el validador OKF lo exige.
- Los specs `CONTRACT-01..17` y sus reportes son históricos: read-only. `rule_engine.py`
  y su oráculo NO se tocan.
- Python stdlib puro; sin red; sin subprocess; sin LLM; mensajes ASCII.
- NO commitear (el PM commitea la tarea verificada). Si algo no se puede sin romper otro
  criterio, PARAR y reportar.
- ABORTAR SI: la reproducción del golden exigiera importar el validador de código de pagos
  (los oráculos deben seguir independientes: el gate usa SOLO el motor declarativo); o la
  capa opcional no pudiera quedar verde post-init sin tocar `init_project`/sus tests. En
  ese caso PARAR, documentar con evidencia en el reporte y marcar BLOQUEADO.

## Checklist antes de delegar

- [x] RECON corrido (2026-07-08): el ejemplo de pagos existe y su equivalencia está verde
  (C17); `--hash` existente sirve para sellar el golden (mismo algoritmo LF); `validate.yml`
  actual tiene 8 pasos y el YAML parsea; post-init `examples/rules/` queda vacío (los 3
  artefactos están en el MANIFEST), de ahí la capa opcional.
- [x] Todo criterio tiene comando + resultado esperado.
- [x] Red-team hecho: familia desconocida = ERROR (mata el typo silencioso); el gate
  re-ejecuta el motor sobre el golden (mata el rule-set decorativo); el sello del golden
  mata el aflojamiento del oráculo; la capa opcional está fijada por test para que "verde
  post-init" no dependa de memoria.
- [x] Perímetro declarado; una sola tarea de código (T1); T2 es cableado del orquestador.
- [x] Condiciones de aborto explícitas.
