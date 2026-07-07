# Contrato 14 — Versionado de la plantilla: CHANGELOG, historia de upgrade y primer release

Prerrequisitos: contratos 01-13 cerrados, HEAD `6fc016e`, suite 168 verde 2×, CI verde en
ambas patas. Gap declarado en el análisis externo (2026-07-07): quien instanció la
plantilla con `init_project` no puede traer mejoras posteriores del template — no hay
versiones, no hay CHANGELOG, y no está documentado qué archivos son infraestructura
sobreescribible desde upstream vs. propiedad del proyecto. RECON: 0 tags en local y en
remoto; el README no menciona versionado.

> Capa: este es un **contrato de ejecución** (nivel proyecto). La tarea lleva su
> **task contract** CCDD en `knowledge/contracts/versioning-plantilla.md` (autorado por
> el orquestador; target = el test de coherencia, patrón de C02).

Decisiones de diseño (fijadas acá): versionado **semver** arrancando en `v1.0.0` (la
plantilla ya está completa y probada: 13 contratos, 3 gates + lint, nivel 2 operativo);
el tag lo crea y pushea el **PM al cierre** (no el dev); la historia de upgrade es
**manual documentada** (comparar release upstream y sobreescribir SOLO infra) — nada de
tooling de merge automático en este contrato.

## VERSIONADO (T1) — CHANGELOG + nodo de upgrade + README + test de coherencia

FIX/OBJETIVO:
1. `CHANGELOG.md` (raíz, nuevo): formato Keep-a-Changelog simplificado; entrada `## v1.0.0
   — 2026-07-07` con resumen del estado (qué incluye la plantilla) y, debajo, historia
   retroactiva breve POR CONTRATO (C01→C13, 1-2 líneas cada uno, destiladas de
   `docs/reports/` — sin inventar: cada línea rastreable a su reporte).
2. `knowledge/plantilla-upgrade.md` (nuevo, type `Concept`, OKF-válido, enlazado desde
   `index.md` sección Referencia): qué es INFRA sobreescribible desde un release upstream
   (scripts/ del tooling, `.agents/`, CI, `OKF-SPEC.md`, `metodologia-ejecucion.md`,
   `validacion.md`, contratos de infra, tests de infra — coherente con los INTACTABLES de
   `tests/test_init_project.py` y el manifiesto de `init_project`, ENLAZANDO esas fuentes
   sin duplicar listas) vs. qué es del PROYECTO (KB propia, `src/`, tests propios,
   contratos propios); procedimiento manual de upgrade en 4-5 pasos (bajar release,
   comparar infra, sobreescribir, re-correr los gates, sellar hashes si cambian tests de
   infra); advertencia honesta: upgrade = re-validar con los propios gates, no merge ciego.
3. README (EN y ES): subsección corta "Versioning / Versionado" tras la de validación:
   semver, enlace a `CHANGELOG.md` y al nodo de upgrade. Sin duplicar contenido (OKF §4).
4. `tests/test_versioning.py` (reemplaza el stub sellado): coherencia por máquina —
   `CHANGELOG.md` existe y su primera entrada `## v` matchea semver (`\d+\.\d+\.\d+`);
   README menciona `CHANGELOG.md` en la parte EN y en la ES; `knowledge/plantilla-upgrade.md`
   existe; `knowledge/index.md` lo enlaza. Mensajes de aserción que nombren qué falta y
   dónde (estilo `test_agents_rules.py`). El dev re-sella `tests_sha256` en
   `knowledge/contracts/versioning-plantilla.md` al terminar.
5. PM al cierre (fuera del dev): `git tag v1.0.0` + push del tag; el criterio lo verifica
   en remoto.

## Criterios de aceptación

- [ ] `python -m unittest tests/test_versioning.py` → OK (sin skips).
- [ ] `python scripts/validate_okf.py knowledge` exit 0 (nodo nuevo enlazado, sin
  huérfanos) y `python scripts/validate_contracts.py knowledge/contracts` exit 0 (10
  contratos, hash re-sellado vigente).
- [ ] `grep -n "CHANGELOG.md" README.md` con ≥2 hits (EN y ES).
- [ ] `python scripts/lint_ascii.py scripts` exit 0 (sin regresiones).
- [ ] Cierre PM: `git ls-remote --tags origin v1.0.0` devuelve el tag.
- [ ] Final: `python -m unittest discover -s tests -p "test_*.py"` suite completa 2×
  verde (dos corridas idénticas); CI verde en ambas patas.

## Restricciones

- Tocar SOLO: `CHANGELOG.md` (nuevo), `knowledge/plantilla-upgrade.md` (nuevo),
  `knowledge/index.md` (SOLO agregar el enlace), `README.md` (SOLO la subsección nueva
  EN/ES), `tests/test_versioning.py` (reemplaza el stub),
  `knowledge/contracts/versioning-plantilla.md` (SOLO re-sellar `tests_sha256`).
- Los specs `CONTRACT-01..13`, sus reportes y `docs/reports/` son históricos: read-only
  (el CHANGELOG los RESUME, no los edita).
- La historia retroactiva no inventa: cada línea sale de un reporte existente.
- NO commitear ni crear tags (el PM commitea por tarea verificada y taggea al cierre).
  Si algo no se puede sin romper otro criterio, PARAR y reportar.
- ABORTAR SI: la coherencia con los INTACTABLES exigiera editar `tests/test_init_project.py`
  o `scripts/init_project.py` (eso es un hallazgo para otro contrato); o el nodo nuevo no
  pudiera quedar OKF-válido sin tocar estructura del index más allá del enlace -> PARAR,
  documentar con evidencia en el reporte y marcar BLOQUEADO.

## Checklist antes de delegar

- [x] RECON corrido (2026-07-07): 0 tags en local y remoto; README sin mención de
  versionado (secciones mapeadas para ubicar la subsección); INTACTABLES y manifiesto ya
  existen como fuentes enlazables (test_init_project.py / init_project.py).
- [x] Todo criterio tiene comando + resultado esperado.
- [x] Red-team hecho: el test de coherencia impide CHANGELOG decorativo (semver en la
  primera entrada) y README sin enlace; la regla "cada línea rastreable a un reporte"
  impide historia inventada; el tag lo verifica el PM en REMOTO (no basta el local).
- [x] Perímetro declarado; disjunto de C15 (corren en paralelo).
- [x] Condiciones de aborto explícitas.
