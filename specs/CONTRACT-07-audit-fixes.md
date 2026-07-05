# Contrato 07 — Correcciones del audit externo (precisión spec/implementación)

Prerrequisitos: C01-C06 completados, HEAD `825d402`, suite 106 verde 2×, ambos validadores
exit 0. Un audit externo de fuente completa (2026-07-04) certificó cero discrepancias
claim/realidad y reportó 6 hallazgos menores de precisión entre specs, nombres y código.
Este contrato los cierra sin cambiar ninguna funcionalidad prometida.

> Capa: este es un **contrato de ejecución** (nivel proyecto). Las tareas que impliquen código
> delegado a un agente efímero llevan además su **task contract** CCDD en
> `knowledge/contracts/<task>.md` (validado por `scripts/validate_contracts.py`).

## OKF-LINKS (T7) — §4 de la spec y el validador dicen lo mismo

`knowledge/OKF-SPEC.md` §4 exige que los enlaces apunten a "un archivo `.md` existente dentro
de `knowledge/`", pero `_validate_links` (`scripts/validate_okf.py:316`) solo chequea
`os.path.exists`: un enlace a `./raro.txt` o a una carpeta pasa limpio. El index enlaza
carpetas a propósito (§5 las usa para alcanzabilidad), así que la regla real es otra.

FIX/OBJETIVO: regla única en ambos lados — un enlace válido apunta, dentro de `knowledge/`,
a (a) un archivo existente con extensión `.md`, o (b) una carpeta existente. Archivo existente
no-`.md` → ERROR. Spec §4 redactada exactamente así; validador la aplica; task contract
`validate-okf.md` coherente. Invariante: el repo actual sigue validando exit 0.

## CTX-HONESTO (T8) — el ensamblador cumple lo que sus nombres prometen

Tres imprecisiones en `scripts/assemble_context.py`: (1) `_regex_deny` (línea 290) hace
`pat in context` — substring literal bajo un nombre y un contrato que prometen "patrón";
quien escriba `password\s*[:=]` obtiene matching literal en silencio. (2) El modo `summarize`
es el mismo corte por chars que `truncate` con otro marcador — el nombre sobre-promete.
(3) El reporte imprime `regex_deny: ok` / `reference_check: ok` aunque esos guardrails no
estén configurados.

FIX/OBJETIVO: (1) `regex_deny` evalúa con `re.search` real (stdlib, determinista); los
patrones existentes de `ccdd/context.json` se migran preservando su intención (escapar
metacaracteres si los hay); patrón inválido → error claro, no silencio. (2) `summarize` se
mantiene aceptado por compatibilidad pero contrato + docstring + reporte declaran explícito
que ambos modos son corte por caracteres y solo difiere el marcador. (3) El reporte solo
lista guardrails configurados. Task contract `assemble-context.md` y sus tests congelados
actualizados en el mismo cambio. Invariante: mismo output byte a byte para configs sin
regex-metachars ni guardrails ausentes.

## EXPORT-CWD (T9) — convención explícita, parsers fijados, código muerto fuera

(1) `scripts/export_gate_contract.py:279` usa `os.getcwd()` como repo root: invocado desde
otro directorio reescribe rutas mal sin fallar, y el test calcula el esperado también con
`getcwd()` — auto-consistente, no fija la convención. (2) El parser YAML (~120 líneas) está
duplicado entre `validate_contracts.py` y `validate_okf.py` deliberadamente (autocontención),
pero nada fija que sigan siendo el mismo dialecto. (3) `validate_contracts.py:196` tiene un
chequeo muerto (`not s.startswith('### ')` tras `startswith('## ')`).

FIX/OBJETIVO: (1) `--repo-root` explícito con default `.`, resuelto a absoluto; el export es
independiente del cwd de invocación y el test lo fija con rutas explícitas. (2) Nuevo
`tests/test_parser_coherence.py`: mismas fixtures parseadas por ambos parsers → outputs
idénticos (fija el dialecto sin acoplar los scripts). (3) Código muerto eliminado. Task
contract `export-gate-contract.md` coherente con el CLI nuevo.

## Criterios de aceptación

- [ ] Por tarea: `python scripts/validate_contracts.py knowledge/contracts` exit 0 y
  `python -m unittest discover -s tests -p "test_*.py"` verde (UNA corrida).
- [ ] T7: `python scripts/validate_okf.py knowledge` exit 0 sobre el repo; un nodo de prueba
  enlazando un `.txt` existente produce ERROR; enlazar una carpeta existente pasa.
- [ ] T8: un patrón regex real (p.ej. `secret\s*:`) matchea vía `re.search` en los tests;
  config actual de `ccdd/context.json` produce el mismo veredicto que antes; el reporte de un
  contrato sin `regex_deny` configurado no menciona `regex_deny`.
- [ ] T9: export invocado desde un cwd distinto con `--repo-root` produce salida idéntica
  (`cmp`) a la invocación desde la raíz; `tests/test_parser_coherence.py` verde; el chequeo
  muerto ya no existe.
- [ ] Final: suite completa 2× verde (dos corridas idénticas ≈ sin flaky); CI verde.

## Restricciones

- Tocar SOLO (conjuntos disjuntos, devs concurrentes):
  - T7: `scripts/validate_okf.py`, `tests/test_validate_okf.py`, `knowledge/OKF-SPEC.md`,
    `knowledge/contracts/validate-okf.md`.
  - T8: `scripts/assemble_context.py`, `tests/test_assemble_context.py`, `ccdd/context.json`,
    `knowledge/contracts/assemble-context.md`.
  - T9: `scripts/export_gate_contract.py`, `tests/test_export_gate_contract.py`,
    `scripts/validate_contracts.py` (solo el chequeo muerto), `tests/test_parser_coherence.py`
    (nuevo), `knowledge/contracts/export-gate-contract.md`.
- Sin dependencias nuevas (stdlib salvo aprobación explícita); sin red ni subprocess en
  scripts deterministas.
- Respetar OKF: todo nodo nuevo en `knowledge/` con frontmatter válido y enlazado desde
  `knowledge/index.md`; los task contracts pasan el validador.
- NO commitear (el PM commitea por tarea verificada). Si algo no se puede sin romper otro
  criterio, PARAR y reportar.
