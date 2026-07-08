# Contrato 29 — Herramienta de benchmark: los 7 gates + la suite, medidos y testeables

Prerrequisitos: contratos 01-28 cerrados, release v1.4.0 publicado, HEAD `2ebc4a9`,
suite 374 verde 2×, CI verde en ambas patas. Nace de un benchmark ad-hoc corrido a
pedido del usuario (2026-07-08, fuera del repo, script de scratchpad): midió los 7
gates de nivel 1 (~485ms total) y la suite (374 tests, ~13-22s por pasada según caché
de disco/OS). El hallazgo se guardó como memoria de sesión con un umbral de alarma
("si la suite se acerca a minutos, ahí sí optimizar"). Este contrato formaliza la
HERRAMIENTA de medición como activo versionado del repo — no fosiliza los números
(dependen de hardware/OS de quien la corra), solo el mecanismo para volver a medir.

> Capa: contrato de ejecución. T1 (código, dev efímero) lleva su task contract en
> `knowledge/contracts/benchmark-gates.md`. T2 (cableado/docs) es del orquestador.
> La herramienta es INFRAESTRUCTURA de mantenimiento (no va al MANIFEST de
> `init_project`: no es un ejemplo de dominio, es tooling de la plantilla como
> `assemble_context.py` o `export_gate_contract.py`).

Honestidad de diseño (la tensión central de este contrato): un benchmark real
necesita `subprocess` + reloj de pared — lo opuesto a "sin subprocess, determinista"
que exige el resto de la plantilla. Se resuelve por **inyección de dependencias**:
toda la lógica de orquestación (ejecutar N repeticiones, descartar warmup, calcular
min/mediana/max, formatear el reporte, decidir el exit code) es PURA y recibe
`run_fn`/`timer_fn` como parámetros; el oráculo congelado inyecta FAKES
deterministas y jamás dispara un subprocess ni depende del reloj real. El CLI
(`main`, sin inyección explícita) usa `subprocess.run` + `time.perf_counter` reales
— ahí, y solo ahí, vive el efecto de lado. Esta es la MISMA doctrina que separa
`rule_engine.evaluate` (puro) de `validate_rules` (I/O): el motor se testea sin
tocar el disco/red; el CLI es la capa fina que sí lo hace.

Decisiones de diseño (fijadas acá):
- **NO se agrega un 8º gate de CI.** Es una herramienta de diagnóstico para quien
  mantiene la plantilla, no un check de corrección — no tiene sentido "fallar" el
  build porque un gate tardó más un día que otro. No se toca `validate.yml`.
- **Lista de gates**: constante explícita `GATES` (mismo estilo `MANIFEST` de
  `init_project.py` — sin heurísticas, sin autodescubrir `scripts/validate_*.py`)
  con los 7 comandos reales, en el mismo orden que `knowledge/validacion.md`.
- **Repeticiones de gates**: 1 warmup descartado + `reps` medidas (default 3);
  reporta min/mediana/max por gate y sus exit codes vistos.
- **La suite** se mide aparte (semántica distinta: 2 pasadas CRUDAS, sin warmup —
  igual que el paso real de CI, `discover -s tests -p "test_*.py"` dos veces) y se
  reporta cada pasada + el total.
- **Exit code del CLI**: 0 si todos los exit codes vistos (gates + suite, todas las
  repeticiones) fueron 0; 1 si alguno falló — el benchmark no debe reportar
  números "limpios" de una corrida contra un repo roto sin decirlo fuerte.
- Ningún número de este contrato se documenta como verdad universal en el README ni
  en `knowledge/`: la baseline de v1.4.0 (measured 2026-07-08) queda en la memoria
  de sesión del usuario, no en el repo — evita fosilizar un dato dependiente de
  hardware como si fuera propiedad de la plantilla.

## T1 — `scripts/benchmark_gates.py` (dev efímero)

OBJETIVO: implementar contra el oráculo congelado `tests/test_benchmark_gates.py`
(autorado y sellado por el orquestador; SIEMPRE inyecta `run_fn`/`timer_fn` fakes,
nunca toca subprocess/reloj real): `measure_repeated` (warmup+reps, min/mediana/max,
exit codes), `measure_suite` (2 pasadas crudas + total), `benchmark_gates`
(orquesta `GATES` + la suite, agrega el reporte), `format_report` (string
determinista dado un reporte), `main(argv, run_fn=None, timer_fn=None)` (CLI; sin
inyección usa `subprocess.run`/`time.perf_counter` reales — la única rama no
testeada por el oráculo, y por diseño). Estilo del resto de `scripts/`; ASCII;
`deps_allowed: []` (subprocess/time/statistics son stdlib).

## T2 — Cableado y verificación de humo (autoría del orquestador)

`knowledge/validacion.md` gana una línea breve mencionando la herramienta como
diagnóstico opcional (NO como gate); `README.md` (EN/ES) la suma a la lista de
tooling ("Kept unchanged"/"Se conserva sin cambios"); CHANGELOG; una corrida REAL
de humo (`python scripts/benchmark_gates.py`) contra el repo real, para confirmar
que produce un reporte legible — sin commitear sus números.

## Criterios de aceptación

- [ ] `python -m unittest tests/test_benchmark_gates.py` verde SIN modificar el
  oráculo; ninguna aserción del oráculo dispara un subprocess real ni depende del
  reloj de pared (grep del archivo del dev: sin `subprocess.run(` ni
  `time.perf_counter(` fuera de los defaults de `main`).
- [ ] Corrida real de humo: `python scripts/benchmark_gates.py` contra el repo
  produce un reporte con los 7 gates + la suite, exit 0 (repo sano).
- [ ] Mutación PM: inyectar un `run_fn` fake que devuelve returncode 1 para un gate
  → `benchmark_gates`/`main` exit 1 y lo refleja en el reporte.
- [ ] Los 7 gates existentes exit 0; suite completa 2× verde; sin nuevo paso de CI.
- [ ] Final: CI verde en ambas patas (sin cambios al workflow).

## Restricciones

- Tocar SOLO — T1 (dev): `scripts/benchmark_gates.py` (+ su REPORT local). T2
  (orquestador): `tests/test_benchmark_gates.py` (nuevo, congelado),
  `knowledge/contracts/benchmark-gates.md` (nuevo, sellado),
  `knowledge/validacion.md`, `README.md` (EN/ES), `CHANGELOG.md`, el spec y el
  reporte.
- `.github/workflows/validate.yml` NO se toca (decisión: no es gate de CI).
- Los specs `CONTRACT-01..28` y sus reportes son históricos: read-only.
- Python stdlib puro (`subprocess`, `time`, `statistics`); sin red; mensajes ASCII;
  la lógica pura es determinista, el CLI real no lo es (y no se testea su output
  real, solo su forma vía inyección).
- NO commitear hasta verificar. Si algo no se puede sin romper otro criterio, PARAR
  y reportar.
- ABORTAR SI: separar orquestación pura de efecto de lado resultara imposible sin
  duplicar lógica entre `main` y las funciones inyectables (hallazgo de diseño, no
  parche); o el formato exacto del reporte no pudiera fijarse sin ambigüedad.
  PARAR y documentar.

## Checklist antes de delegar

- [x] RECON corrido (benchmark ad-hoc previo, 2026-07-08): 7 gates confirmados y su
  orden real en `knowledge/validacion.md`; comando exacto de la suite (`discover -s
  tests -p "test_*.py"`, 2 pasadas, sin warmup — el mismo patrón de CI).
- [x] Todo criterio tiene comando + resultado esperado.
- [x] Red-team hecho: la tensión subprocess-real vs. oráculo-determinista resuelta
  por inyección de dependencias ANTES de delegar (no descubierta a mitad de
  implementación); exit code no-silencioso ante fallas; ningún número fosilizado
  en documentación permanente del repo.
- [x] Perímetro declarado; una tarea de código (T1); cableado + humo del
  orquestador (T2).
- [x] Condiciones de aborto explícitas.
