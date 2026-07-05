# Contrato 03 — Validador OKF: hacer cumplir la spec sobre toda la KB

Prerrequisitos: Contratos 01-02 completados (41 tests verdes). `knowledge/OKF-SPEC.md`
define la conformidad de nodos (§1-§5) pero solo los task contracts se validan hoy: un
nodo huérfano, con `type` inválido o con enlaces rotos pasa CI en verde. Este contrato
convierte la spec OKF en un gate determinista, como C02 hizo con las reglas de agentes.

> Capa: contrato de ejecución. La tarea lleva su task contract CCDD en
> `knowledge/contracts/validate-okf.md`.

## V-OKF (T1) — `scripts/validate_okf.py` + tests + CI

OBJETIVO: validador de la KB completa (`knowledge/**/*.md`), stdlib puro, espejo del
patrón/salida de `scripts/validate_contracts.py`:

1. **§1-§2 Frontmatter**: presente, YAML parseable (mismo parser/enfoque que el validador
   existente), claves `type/title/description/tags` presentes; `tags` lista no vacía y en
   minúsculas.
2. **§3 Tipos**: `type` exactamente uno de `'Task Contract' | 'Data Model' | 'Architecture'
   | 'Concept'`.
3. **§4 Enlaces**: todo enlace markdown relativo que apunte dentro de `knowledge/` debe
   resolver a un archivo existente; enlace roto = ERROR. Enlaces externos (http, rutas
   fuera del bundle) se ignoran (la spec solo prohíbe tratarlos como nodos).
4. **§5 Huérfanos**: todo nodo debe ser alcanzable desde `knowledge/index.md` — enlace
   directo, o vía enlace a su carpeta (convención existente del index con `contracts/`).
   `index.md` es la raíz. Nodo inalcanzable = ERROR con mensaje que nombre el archivo.
5. CLI: `python scripts/validate_okf.py knowledge` → mismo estilo de salida y resumen que
   `validate_contracts.py`; exit 0 sin errores · 1 con ≥1 ERROR.
6. Tests `unittest` en `tests/test_validate_okf.py` con fixtures en tempdir (nodo huérfano,
   enlace roto, type inválido, frontmatter ausente/roto, tags vacías, KB válida) + un test
   contra la KB real del repo (debe pasar limpia).
7. CI: paso nuevo en `.github/workflows/validate.yml` (`python scripts/validate_okf.py
   knowledge`), sin tocar los pasos existentes.

Regla dura: si el validador nuevo encuentra problemas en nodos existentes de la KB, se
ARREGLA el nodo (reportándolo), no se relaja el check.

## Criterios de aceptación

- [ ] `python scripts/validate_okf.py knowledge` → exit 0 sobre la KB actual.
- [ ] `python scripts/validate_contracts.py knowledge/contracts` → exit 0 (incluye el task
  contract nuevo).
- [ ] `python -m unittest discover -s tests -p "test_*.py"` verde (41 + los nuevos), 2× al
  cierre.
- [ ] Mutaciones verificadas: nodo sin enlace en index → exit 1 nombrándolo; enlace roto →
  exit 1; `type` inventado → exit 1.
- [ ] CI con el paso nuevo; pasos existentes intactos.

## Restricciones

- Tocar SOLO: `scripts/validate_okf.py` (nuevo), `tests/test_validate_okf.py` (nuevo),
  `.github/workflows/validate.yml` (solo agregar paso), y nodos de `knowledge/` SOLO si el
  validador encuentra un problema real preexistente (reportarlo). NO tocar
  `scripts/validate_contracts.py`, `scripts/assemble_context.py`, `ccdd/`, `src/`, tests
  existentes, `.agents/` (salvo el REPORT en logs), README.
- Python stdlib puro en el target; sin red; sin subprocess (los tests sí pueden usar
  subprocess para el CLI).
- NO commitear. Si algo no se puede sin romper otro criterio, PARAR y reportar.
