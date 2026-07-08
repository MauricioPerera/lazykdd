# Contrato 27 — Gate de coherencia CHANGELOG↔reportes: el incidente hecho máquina

Prerrequisitos: contratos 01-26 cerrados, release v1.3.0 publicado, HEAD `d24ac67`, suite
327 verde 2×, CI verde en ambas patas. Séptimo gate de nivel 1, con evidencia de incidente
REAL: en el ciclo de v1.2.0, tres entradas del CHANGELOG (C20-C22) se perdieron por un
`str.replace` que no matcheó y falló EN SILENCIO; se recuperaron recién al cortar el
release ("nothing to commit"). La regla operativa que salió de ahí ("toda edición
programática de docs se verifica con grep antes de commitear") es humana y falible — este
contrato la convierte en gate determinista. RECON (2026-07-08): hoy 26 reportes
`CONTRACT-NN-REPORT.md` ↔ 26 entradas `**Contract NN` ↔ 26 links de reporte; el gate nace
midiendo un estado coherente y su primera entrada nueva (la de este contrato) se valida a
sí misma.

> Capa: contrato de ejecución. T1 (código, dev efímero) lleva su task contract en
> `knowledge/contracts/changelog-gate.md`. T2 (cableado) es del orquestador. El gate es
> INFRAESTRUCTURA (no va al MANIFEST).

Decisiones de diseño (fijadas acá):
- **Checks** (todos ERROR): `ENTRY_MISSING` — existe `docs/reports/CONTRACT-NN-REPORT.md`
  pero el CHANGELOG no tiene entrada `**Contract NN` (LA clase del incidente);
  `REPORT_MISSING` — entrada `**Contract NN` sin su reporte en disco (fantasmas/typos);
  `LINK_MISSING` — entrada sin link `(docs/reports/CONTRACT-NN-REPORT.md)` en su línea;
  `ENTRY_DUP` — el mismo NN con más de una entrada.
- Solo cuentan archivos con patrón EXACTO `CONTRACT-<NN>-REPORT.md` (dígitos) —
  `TEMPLATE-REPORT.md` y similares se ignoran. Entradas: líneas que EMPIEZAN con
  `**Contract <NN>` (el formato real de las 26 existentes).
- **Capa opcional**: CHANGELOG ausente o directorio de reportes ausente/sin reportes
  CONTRACT-* → INFO + exit 0 (un proyecto instanciado puede podar la historia).
- CLI: `python scripts/validate_changelog.py [changelog] [reports_dir]` (defaults
  `CHANGELOG.md docs/reports`); Resumen honesto con cuántos contratos se verificaron
  (lección C24: el conteo sale de lo ESCANEADO, nunca solo de los findings).

## T1 — `scripts/validate_changelog.py` (dev efímero)

OBJETIVO: el gate contra el oráculo congelado `tests/test_validate_changelog.py`
(autorado y sellado por el orquestador: par coherente pasa; reporte sin entrada;
entrada sin reporte; entrada sin link; NN duplicado; TEMPLATE ignorado; capa opcional
INFO exit 0; el repo REAL pasa limpio; Resumen honesto; determinismo; exit codes).
Estilo `validate_skills`; findings `{'file','level','rule','msg'}` ordenados; stdlib puro;
ASCII; determinista.

## T2 — Cableado (autoría del orquestador)

Paso de CI `python scripts/validate_changelog.py` (8º); task contract sellado;
`knowledge/validacion.md` + README (EN/ES) con la línea del gate; entrada de C27 en un
`## Unreleased` recreado (que el propio gate valida); `knowledge/casos-reales.md` gana el
incidente v1.2.0 como caso con su regla ahora automatizada, si el nodo existe con esa
estructura.

## Criterios de aceptación

- [ ] `python -m unittest tests/test_validate_changelog.py` verde SIN modificar el oráculo.
- [ ] `python scripts/validate_changelog.py` exit 0 sobre el repo REAL (27 contratos
  verificados tras agregar la entrada de C27 + su reporte).
- [ ] Mutación PM (sobre copia): borrar la entrada de un contrato con reporte → exit 1
  `ENTRY_MISSING` nombrando el NN; agregar entrada `**Contract 99` fantasma → exit 1
  `REPORT_MISSING`.
- [ ] Los 6 gates previos exit 0 y suite completa 2× verde.
- [ ] Final: CI verde en ambas patas (8º paso nuevo).

## Restricciones

- Tocar SOLO — T1 (dev): `scripts/validate_changelog.py` (+ su REPORT local). T2
  (orquestador): `tests/test_validate_changelog.py` (nuevo, congelado),
  `knowledge/contracts/changelog-gate.md` (nuevo, sellado),
  `.github/workflows/validate.yml` (solo agregar paso), `knowledge/validacion.md`,
  `README.md` (línea del gate EN/ES), `knowledge/casos-reales.md` (solo agregar el caso),
  `CHANGELOG.md` (recrear Unreleased + entrada C27), el spec y el reporte.
- Los demás gates, oráculos, dominios y skills NO se tocan.
- Los specs `CONTRACT-01..26` y sus reportes son históricos: read-only.
- Python stdlib puro; sin red; sin LLM; mensajes ASCII; determinista.
- NO commitear hasta verificar. Si algo no se puede sin romper otro criterio, PARAR y
  reportar.
- ABORTAR SI: el formato real de las 26 entradas existentes no fuera capturable por UNA
  regla determinista sin reescribir el CHANGELOG histórico (los históricos son read-only:
  si el gate exige normalizarlos, eso es un hallazgo para decidir CON el usuario, no un
  parche). PARAR y documentar.

## Checklist antes de delegar

- [x] RECON corrido (2026-07-08): 26↔26↔26 coherentes; formato de entrada uniforme
  (`**Contract NN` a inicio de línea, link `(docs/reports/...)` en la misma línea);
  `TEMPLATE-REPORT.md` identificado como exclusión necesaria.
- [x] Evidencia del gate: incidente real v1.2.0 (replace silencioso, 3 entradas perdidas),
  registrado en memoria y en el reporte de v1.2.0 — no es gate especulativo.
- [x] Todo criterio tiene comando + resultado esperado.
- [x] Red-team hecho: patrón exacto de archivo excluye TEMPLATE; ENTRY_DUP cubre el caso
  "recuperación duplicó una entrada"; Resumen cuenta lo escaneado (lección C24); la
  entrada del propio C27 queda bajo el gate (auto-validación).
- [x] Perímetro declarado; una tarea de código (T1); cableado del orquestador (T2).
- [x] Condiciones de aborto explícitas.
