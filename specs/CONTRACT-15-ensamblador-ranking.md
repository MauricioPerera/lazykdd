# Contrato 15 — Ensamblador a escala: ranking del retriever, corte honesto por nodo y chars/token configurable

Prerrequisitos: contratos 01-13 cerrados (independiente de C14: perímetros disjuntos),
HEAD `6fc016e`. Tres límites de escala del ensamblador detectados en el análisis externo
(2026-07-07) y confirmados en RECON: (a) el retriever es binario (match/no-match) y el
slot `okf_nodes` concatena TODO lo seleccionado y compacta la CONCATENACIÓN — en una KB
grande, `truncate` corta la cola en orden alfabético y los nodos del final quedan fuera
en silencio; (b) el reporte no declara qué nodos quedaron cortados o afuera; (c) la
heurística 1 token ≈ 4 chars está hardcodeada en DOS lugares (`_tokens` línea 45 y
`_compact` línea 207) y subestima en español.

> Capa: este es un **contrato de ejecución** (nivel proyecto). La tarea actualiza el
> task contract existente `knowledge/contracts/assemble-context.md` (Invariants/Examples
> + re-sello) — precedente C07/T8.

Decisiones de diseño (fijadas acá):
- **Ranking determinista**: score por nodo = cantidad de señales que matchean (mención
  del nombre de archivo en la tarea cuenta 2; cada tag del frontmatter que matchea como
  palabra cuenta 1). Orden de ensamblado: score descendente, empate por nombre
  alfabético. Sin matches → fallback actual (todos, score 0, orden alfabético) — ese
  camino queda **byte-idéntico** al actual cuando todo cabe (el smoke del CI no cambia).
- **Corte por nodo, no por concatenación**: en `okf_nodes` se incluyen nodos ENTEROS en
  orden de ranking mientras quepan; el primero que no cabe se compacta según el modo del
  slot (`truncate`/`summarize`, marcador incluido); los siguientes se OMITEN.
- **Reporte honesto**: el slot `okf_nodes` declara `selected` (compat: alfabético, como
  hoy), y además `cut` (el nodo compactado, si hubo) y `omitted_nodes` (los que quedaron
  fuera, si hubo) — claves ausentes cuando no aplica (misma doctrina que los guardrails
  de T8: no mencionar lo no ocurrido).
- **`budget.chars_per_token`** opcional (entero ≥1, default 4): `_tokens` y `_compact`
  lo comparten desde UN solo lugar (hoy son dos constantes independientes que pueden
  divergir); inválido → `ValueError` que lo nombra.

## ASSEMBLE-RANK (T1) — retriever con ranking + corte honesto + config de tokens

FIX/OBJETIVO: `scripts/assemble_context.py` implementa las 4 decisiones de arriba.
`ccdd/context.json` NO se toca (no necesita cambios: sin `chars_per_token` aplica el
default). El task contract `knowledge/contracts/assemble-context.md` actualiza
Invariants/Examples para describir ranking, corte por nodo, reporte honesto y
`chars_per_token`, y el dev re-sella `tests_sha256` al terminar (sus tests cambian).
Tests nuevos en `tests/test_assemble_context.py`: ranking (nodo mencionado por nombre
gana a match por tag único; empate → alfabético); corte por nodo (con presupuesto justo,
el mejor rankeado entra entero, el segundo aparece en `cut` con marcador, el tercero en
`omitted_nodes`); reporte sin `cut`/`omitted_nodes` cuando todo cabe; fallback sin
matches byte-idéntico al comportamiento actual (fijarlo con un caso); `chars_per_token=2`
duplica el costo en tokens de un contenido dado; `chars_per_token` inválido →
`ValueError`; determinismo 2× se conserva.

Invariantes duros: determinismo estricto (mismas entradas → stdout byte a byte
idéntico); stdlib puro; sin red; sin subprocess; sin relojes; los tests existentes del
archivo se conservan (solo se ajustan si un cambio de comportamiento FIJADO ACÁ los
afecta, documentando cuál en el REPORT); `python scripts/assemble_context.py
ccdd/context.json "smoke"` sigue exit 0 (paso de CI).

## Criterios de aceptación

- [ ] `python -m unittest tests/test_assemble_context.py` → OK.
- [ ] `python scripts/assemble_context.py ccdd/context.json "smoke"` → exit 0; dos
  invocaciones → stdout byte a byte idéntico (`cmp`).
- [ ] `python scripts/validate_contracts.py knowledge/contracts` exit 0 (hash de
  `assemble-context.md` re-sellado vigente).
- [ ] `python scripts/lint_ascii.py scripts` exit 0 (mensajes nuevos en ASCII).
- [ ] Mutación PM (fixture propio): KB con 3 nodos y presupuesto justo → el reporte
  declara `cut` y `omitted_nodes` exactos; tarea sin matches con presupuesto holgado →
  el reporte NO menciona `cut` ni `omitted_nodes`.
- [ ] Final: `python -m unittest discover -s tests -p "test_*.py"` suite completa 2×
  verde (dos corridas idénticas); CI verde en ambas patas.

## Restricciones

- Tocar SOLO: `scripts/assemble_context.py`, `tests/test_assemble_context.py`,
  `knowledge/contracts/assemble-context.md`.
- `ccdd/context.json` NO se toca (tiene trabajo en progreso ajeno en el working tree).
- Los specs `CONTRACT-01..13` y sus reportes son históricos: read-only.
- Python stdlib puro; sin red; sin subprocess; mensajes ASCII (el lint de C13 lo exige).
- NO commitear (el PM commitea por tarea verificada). Si algo no se puede sin romper
  otro criterio, PARAR y reportar.
- ABORTAR SI: el fallback sin matches no pudiera quedar byte-idéntico al actual sin
  romper otro invariante fijado acá; o un test existente exigiera un cambio de lógica
  no derivado de las 4 decisiones de diseño; o mantener el smoke del CI en exit 0
  exigiera tocar `ccdd/context.json` -> PARAR, documentar con evidencia en el reporte y
  marcar BLOQUEADO.

## Checklist antes de delegar

- [x] RECON corrido (2026-07-07): 4 chars/token hardcodeado en 2 lugares independientes
  (líneas 45 y 207 — pueden divergir hoy); `selected` se emite `sorted()` (línea 386,
  compat preservada); concatenación única confirmada (`"\n\n".join` sobre todos los
  seleccionados); suite del ensamblador OK en el HEAD de partida.
- [x] Todo criterio tiene comando + resultado esperado.
- [x] Red-team hecho: "fallback byte-idéntico" fijado con caso de test (impide que el
  ranking reordene el camino sin matches y rompa el smoke); el reporte honesto omite
  claves cuando no aplica (doctrina T8, testeado en ambas direcciones); `chars_per_token`
  compartido desde un solo lugar (dos copias divergentes es exactamente el bug-clase que
  `test_parser_coherence` caza en los validadores).
- [x] Perímetro declarado; disjunto de C14 (corren en paralelo).
- [x] Condiciones de aborto explícitas.
