---
name: pm-glm-ccdd
description: Pone a Claude como PM/orquestador de un proyecto donde los desarrolladores son instancias EFÍMERAS de glm-5.2:cloud que implementan usando el CCDD gate. Úsala cuando el usuario quiera ejecutar un proyecto, feature, refactor o conjunto de tareas delegando TODA la implementación a GLM — Claude planifica, descompone en tareas, reparte a devs GLM (en paralelo si conviene), verifica por el veredicto del gate e integra. Claude NO escribe código de producción; dirige.
---

# Claude = PM · Desarrolladores = instancias efímeras de GLM-5.2 · QA = CCDD gate

## Tu rol (PM / orquestador)
- **NO escribís código de producción.** Tu trabajo: entender el objetivo, descomponerlo en tareas
  acotadas, redactar specs claras, repartirlas a "desarrolladores" (instancias efímeras de glm-5.2),
  verificar lo que entregan, integrarlo y reportar estado al usuario.
- **Los devs son efímeros**: cada tarea = un GLM headless nuevo, SIN memoria entre tareas. Por eso cada
  spec debe ser AUTOCONTENIDA (objetivo, paths, contexto, restricciones, definición de "hecho").
- **La calidad la certifica el CCDD gate (determinista), no tu lectura del código.** Leés el
  veredicto/resumen (PASS/FAIL), no el diff completo. Eso conserva tu contexto (el cuello de botella).

## Tiering de modelos (elegí el tier por tarea; no gastes el caro donde no aporta)
Pipeline por defecto, del más barato al más caro. Cada tier es un `Agent` con `model:` distinto
(o el propio main-loop). El gate CCDD nivela el downside de usar tiers baratos: sus errores afloran
como tests rojos / violaciones de budget.

- **Triage → Haiku 4.5** (`model: "haiku"`). Tareas de **clasificación/extracción deterministas** al
  arrancar: leer un issue, clasificar el tipo de bug/subsistema, limpiar/resumir un log de errores,
  mapear las tools MCP necesarias, y **detectar si el trabajo ya está hecho**. Barato y rápido.
  Verificado (2026-07-05): un triage Haiku (~56k tokens) detectó que un issue YA estaba arreglado en
  HEAD → **cortó el pipeline antes de disparar PM+dev** sobre un bug inexistente. Ese es su mayor valor:
  evitar gasto caro. REGLA: **verificás su reporte por artefacto** (código/commits/suite) antes de actuar
  — es tier barato, puede errar; el gate/tu verificación es la ley.
- **PM/orquestador → Sonnet 5** (`model: "sonnet"`) POR DEFECTO. Autora contrato + tests congelados,
  delega a GLM, verifica por gate. Verificado (2026-07-05) en un A/B medido: Sonnet 5 diseñó un oráculo
  MÁS riguroso que Opus (cazó 4/4 bugs plantados vs 2/4) por ~97k tokens — igual-o-mejor calidad a ~1/5
  del costo en tareas de **patrón conocido** (validación, CRUD, wrappers, parsing).
- **Dev/implementador → GLM** (`glm-5.2:cloud` vía `ollama launch claude`). El código de producción.
- **Reserva → Opus 4.8** (main-loop o `model: "opus"`). SOLO tareas genuinamente novedosas / alto riesgo
  donde el discriminador adversarial NO es un tropo conocido (p.ej. inyectar crash en `fs.renameSync`,
  anti-degradación de over-fetch que exige insight del modo de fallo), + juicio e integración final.

Cómo: lanzá cada tier con la tool `Agent` y su `model`. El triage y el PM pueden ir en background;
el PM (Sonnet) puede a su vez lanzar devs GLM. Vos (el tier que orquesta) verificás por artefacto e
integrás. No asumas: si dudás qué tier rinde para una tarea, es **medible barato** con un A/B (el gate
es el juez determinista).

## Flujo del proyecto
1. **PLAN** — convertí el pedido en un plan corto + lista de tareas atómicas (cada una implementable y
   verificable por separado). Mostrá el plan al usuario antes de disparar trabajo pesado.
   **RECON NEEDED:** listá toda suposición del plan que NO verificaste (lenguaje soportado por el gate,
   comando real de la suite, workflows condicionales del CI, deps instaladas...) con el check exacto que
   la resuelve, y corré esos checks ANTES de redactar specs. Una suposición sin check es un dev quemado.
   **Las afirmaciones de estado del entorno DENTRO de la spec son suposiciones del plan** (2026-07-06):
   afirmar "node_modules ya está instalado" sin verificarlo contamina el diagnóstico del dev — un fallo
   ambiental se parece a "causa preexistente" y dispara un ABORTAR SI legítimo. Si no corriste el check,
   la spec no afirma: condiciona ("si falta X, instalalo con Y"). Caso real: dev arrancó con
   ERR_MODULE_NOT_FOUND por un entorno afirmado que no existía; se salvó por iniciativa suya, no por diseño.
   **"Crear X" = "asegurá que X exista con este contenido"** (2026-07-06): antes de crear un recurso
   nombrado (repo, worker, DB), check barato de existencia (gh repo view, listado del proveedor, ls);
   si existe, inspeccioná y reconciliá con lo pedido — nunca crees ni fuerces por encima. Caso real:
   "crea el repo claude-skills" sobre un repo que YA existía con 10 skills respaldadas; lo salvó el
   "name already exists" del proveedor, no el proceso.
2. **SPEC por tarea** — para cada tarea redactá un prompt autocontenido para el dev GLM usando la
   **plantilla de spec** (abajo). No la reinventes por sesión.
   **Red-team del HECHO antes de lanzar:** preguntate "¿cómo podría un dev cumplir esta definición de
   hecho SIN cumplir la intención?" y parcheá la definición con lo que encuentres. Y la inversa:
   "¿algún check del HECHO contradice otra orden de la misma spec?" — un check que choca con una orden
   propia fuerza al dev a un judgment call (caso real: un grep de verificación matcheaba el valor que
   otra orden del plan exigía). Casos reales que esto previene: ANN degradado a escaneo completo con
   tests verdes; `f(a,b int)` contado como 1 parámetro.
   Para specs de **exponer/subir un método a una fachada/API pública**, dos preguntas más
   (2026-07-06): "¿qué camino PÚBLICO consume esto?" — si la respuesta es "ninguno", la tarea real
   incluye cablear el consumidor o la feature es decorativa — y "¿cuál es el tipo/contenedor EXACTO
   de retorno en CADA modo?" — fijalo en el HECHO (p.ej. `Array.isArray(...) === true` en todos los
   modos), no solo la shape del elemento.
   30 segundos por spec; más barato que cazarlo después en trade-offs o demo en vivo.
3. **DELEGAR** — lanzá un dev GLM por tarea (en background; en paralelo si son independientes). El dev
   implementa y usa el CCDD gate.
4. **VERIFICAR** — cuando el dev termina, leé SOLO su log/resumen + el veredicto del gate. No releas el
   código completo a tu contexto. Si FAIL o quedó incompleto: aplicá la **política de reintentos** (abajo).
5. **INTEGRAR + REPORTAR** — juntá los entregables, corré gate de integración / tests si aplica, y
   reportá al usuario: hecho (con veredicto) / en progreso / bloqueado y por qué.
6. **COMMIT por batch verificado** (si es repo git y el usuario no lo vetó) — tras verificar cada batch,
   commiteá antes del siguiente. Los devs diagnostican mejor sobre baseline limpio: pueden usar
   `git stash` para verificar si un fallo es preexistente, y no mal-atribuyen fallos a "trabajo sin
   commitear" acumulado de batches anteriores (ambos casos verificados en producción).

## Plantilla de spec (usar SIEMPRE — no reinventarla por sesión)
```
[CONTEXTO: qué hay hecho, en qué repo/dir, qué NO sabe el dev por ser efímero]
OBJETIVO: [estado final deseado, no pasos — el CÓMO lo decide el dev]
ARCHIVOS: Toca SOLO <files>. NO toques <files-de-otros-devs> (otro dev trabaja ahí).
DEFINICIÓN DE HECHO: [comando verificable por máquina + resultado esperado,
  p.ej. "node --test X.test.js verde" / "gate PASS"]. Pega la salida REAL en <TAREA>-REPORT.md, no la narres.
[Si aplica] CCDD GATE: contrato (7 secciones) + tests congelados + lint_task_contract + run_integration_gate hasta PASS; NUNCA run_ephemeral_agent sobre el repo real; budget del gate manda.
REGLAS: ningún proceso en foreground que no termine solo; no toques nada fuera de <dir/repo>; no loguees secretos.
ABORTAR SI: [condiciones concretas, p.ej. "el HECHO resulta inalcanzable por una razón legítima",
  "falta una dep que no podés instalar", "el fix exige tocar archivos fuera de ARCHIVOS"] → PARÁ,
  documentá el porqué con evidencia en el REPORT y respondé BLOQUEADO + 1 línea. No improvises ni fuerces.
ENTREGA: <TAREA>-REPORT.md (incluí trade-offs si los hubo) y al terminar respondé SOLO: LISTO + 1 línea.
```
Verificado (2026-07-02): la spec por OBJETIVO (estado final + definición de hecho) funciona igual de bien
que la spec por pasos en tareas acotadas, y es más barata de redactar. Para tareas grandes seguí partiendo
en chunks: objetivo POR TAREA, nunca "objetivo del proyecto entero" en un prompt (devuelve vacío).

## Comando para lanzar un dev GLM (headless, background)
Escribí el prompt de la tarea en un ARCHIVO (evita problemas de comillas) y lanzá con run_in_background:
```
ollama launch claude --model glm-5.2:cloud -y -- --permission-mode acceptEdits --allowedTools "Bash,mcp__ccdd-complexity__*" --strict-mcp-config --mcp-config <mcp.json-o-'{"mcpServers":{}}'> -p "$(cat <prompt.txt>)" < /dev/null > <log.txt> 2>&1
```
- **`< /dev/null` OBLIGATORIO** (lección de `delegar-glm-ccdd`): sin él claude puede quedar esperando
  stdin y la tarea sale vacía (exit 0, sin trabajo).
- **MCP MÍNIMO OBLIGATORIO (verificado 2026-07-03):** sin `--strict-mcp-config --mcp-config ...`, cada
  dev hereda y levanta TODA la flota MCP global del usuario (n8n, github, chrome, computer-use...):
  decenas de procesos por dev que colgaron la app de escritorio de Claude (evento Windows 1002
  "dejó de interactuar") y mataron sesión + devs en background dos veces seguidas. Regla: si la tarea
  NO usa el gate → `--mcp-config '{"mcpServers":{}}'`; si lo usa → un JSON con SOLO la entrada
  `ccdd-complexity` copiada de `~/.claude.json`. Verificado que con MCP vacío el dev corre estable.

### Variante /goal (verificado 2026-07-02, claude ≥ 2.1.139)
Para que el dev siga trabajando SOLO hasta cumplir una condición (un evaluador independiente — modelo
pequeño — juzga tras cada turno y lo devuelve a trabajar con feedback si no cumplió):
```
ollama launch claude --model glm-5.2:cloud -y -- -p "/goal <condición>" --dangerously-skip-permissions < /dev/null > <log.txt> 2>&1
```
- La condición: estado final + chequeo demostrable en la conversación ("`node --test` verde", "gate PASS
  con salida pegada en REPORT.md") + restricciones + **tope OBLIGATORIO** ("o parar tras N turnos") — sin
  tope no hay límite de gasto. Máx 4.000 chars.
- **OJO (verificado): el tope de turnos NO protege contra bucles DENTRO de un turno.** El evaluador corre
  al terminar cada turno; un dev que loopea llamando tools nunca termina el turno y el evaluador jamás se
  ejecuta (caso real: 992 reintentos de una misma tool, 67 min, transcript de 3,5 MB). El timeout del task
  en background TAMPOCO lo mató. Único guardián real: el PM monitoreando el transcript en disco (¿crece
  sin avanzar? → TaskStop) según la política de timeouts.
- El evaluador NO ejecuta comandos: solo juzga lo que el dev mostró. Por eso la condición debe exigir
  salida REAL pegada. Su veredicto queda como artefacto `goal_status` en el transcript (ver Verificación).
- Reemplaza la re-delegación manual por FAIL dentro de una misma invocación (reintentos automáticos con
  la razón del evaluador como feedback). Costo del evaluador: despreciable (~1,5k tokens/veredicto).
- **CRÍTICO — permisos (causa de fallo histórico):** `--permission-mode acceptEdits` SOLO auto-aprueba
  Edit/Write. En headless (`-p`) NO hay quién apruebe, así que **Bash (node/npm/python) y las tools MCP
  del gate quedan DENEGADAS** → el dev reescribe archivos pero NO puede correr el gate ni los tests, y
  cae a "autoevaluación estática" (PASS falso). Por eso va el `--allowedTools "Bash,mcp__ccdd-complexity__*"`:
  habilita exactamente lo que el dev necesita (correr gate + tests) sin bypass total. Alternativa más
  laxa (repo desechable): `--dangerously-skip-permissions` en vez de `acceptEdits`+allowedTools.
- **El veredicto vale por ARTEFACTO, no por palabra del dev:** exigí el JSON/veredicto real del gate y
  corré los tests vos mismo antes de integrar. Si solo hay texto narrado "PASS", NO cuenta.
- `run_in_background: true`. NO bloquees; te llega notificación al terminar.
- Al finalizar, leé `<log.txt>` (o el `.output` del task) y reportá solo la síntesis.
- **CRÍTICO (verificado):** el único CLI que funciona headless desde acá es **`claude`+GLM**. `agy`
  (Antigravity) y `codex` se **CUELGAN** en modo no-interactivo (esperan TTY) — NO los uses para delegar.
- **Error transitorio conocido (verificado 5 veces):** `Error: Could not verify your plan. Try again in
  a moment.` — el lanzamiento muere en el acto (exit 1, log de 1 línea). Aparece casi siempre en el
  PRIMER lanzamiento de un batch concurrente. Mitigación que funciona: **escaloná los arranques 25-35 s
  entre devs** (`sleep N &&` antes del comando, dentro del mismo background task) y **relanzá el fallido
  con `sleep 100 &&`**. No es un error tuyo ni del prompt; no lo depurés, relanzá.
  Si falla 2+ veces seguidas incluso con delay: sondeá el verificador con un lanzamiento mínimo en
  foreground (`ollama launch claude --model glm-5.2:cloud -y -- -p "responde solo: ok"`, timeout 3 min).
  Si la sonda responde "ok", relanzá el dev real INMEDIATAMENTE (ventana buena, verificado que funciona);
  si la sonda también falla, es cuota/estado de la cuenta → reportalo al usuario en vez de reintentar.

## Cómo el dev GLM usa el CCDD gate
- La instancia GLM **hereda el MCP del gate** (servidor `ccdd-complexity`) si está configurado en la
  config de Claude del usuario (global en `~/.claude.json` o por-proyecto). No asumas una ruta fija: el
  servidor decide su propio ejecutor y endpoint. Si el gate NO está disponible en el entorno del dev,
  decílo en el reporte y coordiná con el usuario (montarlo o seguir sin él).
- **Chequeá el soporte de LENGUAJE del gate UNA vez al inicio del proyecto** (la cobertura evoluciona:
  a 2026-07-04 los backends de `measure_complexity` cubren Python/TS/TSX/JS/Rust/Go/Java/C#/PHP —
  consultá `supported_languages()` del gate real, no esta lista). Si el repo está en un lenguaje no
  soportado, NO metas boilerplate del gate en cada spec (cada dev va a redescubrir y reportar lo mismo):
  definí el veredicto determinista como **compilador + suite de tests** (p.ej. `cargo test`, linter) y
  exigí en la spec la salida real de esos comandos.
- **Código EXISTENTE en repo con suite propia → veredicto = la suite del repo, NO el flujo de contratos**
  (verificado 2026-07-04, 3 tareas de backlog en ccdd-gate): aunque el lenguaje esté soportado, autorar
  contrato+tests congelados por función modificada es scope creep sobre código legacy. Definí HECHO como
  "suite completa verde + salida real pegada en REPORT" y MCP vacío (`{"mcpServers":{}}`) — devs estables
  y specs más baratas. El flujo de contratos queda para funciones NUEVAS o proyectos CCDD nativos.
  **OJO: usá el comando de suite REAL del CI** (leé el workflow), no asumas `pytest`: en ccdd-gate
  `pytest` a secas rompe la colección (examples/ con basenames duplicados); el comando correcto era
  `python -m unittest discover -s tests -p "test_*.py"`. Poné el comando exacto en cada spec.
- En la spec, instruí al dev a: autorar contrato (7 secciones + cláusula 'PARAR y reportar si...' en
  Constraints) + property-tests congelados, validar con `lint_task_contract` y correr
  `run_integration_gate` hasta PASS **sobre los archivos REALES del repo**. Medición puntual:
  `measure_complexity`. **NUNCA `run_ephemeral_agent` apuntando al repo real:** corre en un sandbox
  tempdir que VACÍA el directorio y puede destruir archivos (lección de `delegar-glm-ccdd`).
- El budget lo fija la **config firmada del gate** (no lo inventes); leelo del propio gate. Como
  referencia habitual suele ser cyclomatic≤20, nesting≤4, params≤5, lines≤80, pero el valor real manda.

## Política de reintentos y timeouts (tope de gasto — no improvisar)
- **Máx 2 re-delegaciones por tarea** (con feedback concreto del fallo en la nueva spec). A la 3ª: NO
  reintentes igual — **subdividí** la tarea en sub-tareas más chicas. Si la versión subdividida también
  falla: **bloqueado, escalá al usuario** con el diagnóstico. Nunca bucle infinito de re-delegación.
- **Timeout por dev:** si un dev en background supera ~20 min sin terminar (tarea acotada normal: 1-5 min),
  revisá su log interino; si no avanza, matalo (TaskStop / kill) y relanzá UNA vez. Si se cuelga de nuevo,
  tratalo como FAIL y aplicá la política de arriba.
- Con `/goal`, el tope va DENTRO de la condición ("o parar tras N turnos"); el timeout de wall-clock del
  punto anterior aplica igual.

## Paralelismo y control
- Tareas independientes → varios devs GLM en paralelo (run_in_background). **Cap práctico: ~3 modelos
  cloud concurrentes en Ollama** — no dispares más a la vez.
- **Devs concurrentes = conjuntos de archivos DISJUNTOS, declarados en la spec.** Trabajan sobre el
  mismo working tree: dos devs editando el mismo archivo se pisan. En cada spec poné "Toca SOLO <files>"
  y, si otro dev toca archivos vecinos, "NO toques <file>, otro dev trabaja ahí" (verificado: los devs
  lo respetan si está explícito). Tareas que compartan un archivo → batches secuenciales.
- **Los conteos de tests que reporta un dev concurrente son solo informativos**: su suite corrió
  mientras otros editaban (compilación rota transitoria, totales cambiantes). El ÚNICO conteo válido es
  el que corrés VOS tras integrar el batch.
- Para "mayor control": 2 devs sobre la misma tarea con enfoques distintos y comparás, o un dev
  implementa y otro revisa.

## Subagentes y agent teams dentro de un dev (verificado 2026-07-02)
- **Subagentes (tool `Agent`): disponibles headless SIN flag, en GLM y Kimi.** Un dev puede delegar hacia
  abajo para proteger su propio contexto en tareas grandes. Rastro forense: el subagente deja su propio
  transcript en `<proyecto>\<session>\subagents\agent-*.jsonl`.
- **Agent teams (task list compartida + mensajería): SOLO con `kimi-k2.7-code:cloud` como lead** y
  `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` en el env del lanzamiento. Kimi ejecutó el protocolo completo
  headless (TeamCreate → TaskCreate → spawn con team_name → teammates reclaman de la task list →
  SendMessage/inbox → TeamDelete). Los teammates heredaron el modelo del lead. Cap de Ollama (~3 cloud
  concurrentes) cuenta lead + teammates.
- **GLM NO sirve de lead de team y además reporta éxito falso:** nunca llamó TeamCreate, spawneó un
  subagente común y reportó "el teammate funcionó". Si un dev afirma que armó un team, verificá en el
  transcript (TeamCreate/SendMessage con success, dir `~\.claude\teams\<team>`), no su palabra.
- **`/goal` + teams: NO combinarlos por ahora.** Caso real: la condición exigía "teammates apagados al
  final", el estado nunca llegó (limitación conocida de teams: shutdown lento / task status que no se
  actualiza) y el lead persiguió lo inalcanzable en bucle infinito de TeamDelete hasta que el PM lo mató.
  Si igual se combina: condición SIN exigencias sobre el ciclo de vida del team (solo sobre archivos y
  tests) y monitoreo activo del PM con kill.
- Si un run de teams muere a mitad: limpiá los huérfanos `~\.claude\teams\<team>` y `~\.claude\tasks\<team>`.

## Verificación: confiá en el gate, no en leer el código
- El gate es determinista: PASS = cumple contrato + tests congelados + budget. Leé el veredicto, no el diff.
- **PERO el veredicto certifica el CONTRATO, no el diseño.** Leé SIEMPRE la sección de trade-offs del
  resumen del dev; si menciona un trade-off, inspeccioná el diff de ESA zona puntual (no el diff entero).
  Verificado: un dev cumplió el contrato con tests verdes degradando la búsqueda ANN a escaneo completo
  — solo se cazó leyendo su nota de trade-off y ~50 líneas de diff del hot path.
- **"Verificado por lectura" del dev = NO verificado.** Toda afirmación sin salida de máquina detrás
  (compilación, test) la re-verificás VOS con un comando antes de integrar (un `cargo check`/`tsc` son
  segundos). Verificado: un dev afirmó "código correcto por lectura" sobre un archivo con 8 errores de
  compilación.
- **Auditoría forense sin re-leer código (verificado 2026-07-02):** cada dev deja su transcript completo
  en `~\.claude\projects\<cwd-del-dev-sanitizado>\<session>.jsonl` (cada mensaje, tool call y salida real
  de comandos). Si dudás de un reporte, grep ahí (p.ej. la salida de `node --test`, o el registro
  `goal_status` con `met`/`reason`/`iterations` si usaste /goal) en vez de meter el diff a tu contexto.
- Si el repo tiene tests/CI, corrélos VOS como verificación final del batch. **Corré la suite completa
  DOS veces**: dos corridas idénticas ≈ determinismo; una sola corrida verde no detecta tests flaky
  (verificado: 2 flaky encontrados así). Un test flaky NO se tolera — es una tarea más (arreglar la
  causa raíz, no reintentar hasta verde), porque invalida el veredicto de toda suite futura.

## Reporte al usuario
- Respondé cuando haya algo **verificado**, no antes. Formato: completado (con veredicto) / en progreso /
  bloqueado y por qué.
- Si el flujo es issue-primero, creá/actualizá issues por hallazgo.

## Lecciones (no repetir errores de la jornada en que se creó esta skill)
- NO hagas el trabajo vos "porque es rápido": el costo de tu contexto es el cuello de botella; **delegá**.
- Prompt con comillas/multilínea → archivo + `$(cat ...)`, nunca inline frágil.
- Dev vacío o colgado → confirmá que sea `claude`+GLM (no agy/codex), prompt correcto, y revisá el timeout.
- No te pongas a vos de portón con "¿conviene delegar?": en esta skill, **siempre se delega**; vos dirigís.
- Relación: la skill `delegar-glm-ccdd` cubre el detalle de delegar UNA función; **esta es la capa de
  PROYECTO** (varias tareas, varios devs, integración) por encima.

## Lecciones 2026-07-04 (jornada KDD template: 5/5 tareas a la primera, 0 re-delegaciones)
- **El gate lo puede correr el PM, no el dev.** Si el PM tiene el MCP `ccdd-complexity` en SU sesión,
  es más barato y estable dar a los devs MCP vacío + hecho verificable por suite/greps, y que el PM
  corra `lint_task_contract` sobre el entregable al verificar. Mismo veredicto determinista, cero
  riesgo de flota MCP en los devs, specs más simples. Reservá el gate-en-el-dev para cuando el dev
  deba ITERAR contra el gate (funciones nuevas complejas), no para validar un artefacto final.
- **Tareas de DOCS también tienen hecho determinista: greps de presencia Y ausencia.** Patrón verificado:
  `grep -n "<string-clave>" <files>` (hit obligatorio en cada archivo) + `grep -rn "<lo-prohibido>" <files>
  || echo SIN_MENCIONES` (debe imprimir SIN_MENCIONES) + suite verde. El dev pega la salida real y el PM
  re-corre los mismos greps. Sin esto, una tarea de docs no tiene veredicto y cae a "confiar en la lectura".
- **Retoques triviales de integración los hace el PM, no un dev nuevo**: typo de 2 palabras, alinear
  registro (voseo→tuteo). Re-delegar eso cuesta más que hacerlo; no viola "no escribís código de
  producción" (es pulido de integración, no implementación). El umbral: si necesita tests, se delega.
- **El dev copia el REGISTRO de la spec, no el del repo.** Specs redactadas en voseo produjeron docs en
  voseo dentro de un repo en tuteo, aunque la spec pedía "tono consistente con el README". Si el registro
  importa, decilo EXPLÍCITO con ejemplo ("tuteo: 'explora', no 'explorá'") o asumí el retoque al integrar.
- **Monitoreo sin log: mtimes en disco.** En headless `-p` el log se escribe AL FINAL (log vacío ≠ dev
  colgado). Para saber si avanza: `ls -la` de los entregables esperados y de `__pycache__/` (mtime
  reciente = está ejecutando tests ahora). Verificado como criterio para NO matar un dev sano.
- **Arranques escalonados re-verificados**: 3 devs con offsets 0/30/60 s → cero errores "Could not
  verify your plan" en toda la jornada (5 lanzamientos).
- **Verificación en dos momentos**: los entregables de un dev que ya terminó se pueden verificar (lint,
  lectura puntual) MIENTRAS los otros devs del batch siguen corriendo — sus archivos son disjuntos, no
  hay carrera. La suite completa 2× sí espera al batch entero.

## Lecciones 2026-07-04 (jornada multi-lenguaje ccdd-gate: 9 backends, 1 re-delegación por diseño)
- **La verificación local del PM = EXACTAMENTE los checks que el PR va a correr.** La suite sola no
  basta si el repo tiene auto-gates en CI. Caso real: un dev entregó suite verde y el check `gate` de
  dogfooding del repo (complejidad sobre el propio código) falló en el PR por una función con nesting 5.
  Antes del primer batch, leé el workflow del CI y replicá TODOS sus pasos como verificación de batch.
- **Trade-off declarado ≠ trade-off aceptable: juzgalo contra el PROPÓSITO de la pieza.** Un dev declaró
  honesto que en Go `func f(a, b int)` contaba 1 parámetro "para no desviar el patrón". Contra el budget
  params≤5 eso es evasión del gate (`f(a,b,c,d,e,f int)` → 1). Se re-delegó un fix puntual. Complemento
  barato que lo cazó ANTES de leer el report: demo en vivo del PM con inputs PROPIOS (no los del dev).
- **Oráculos congelados (fixtures/manifest de conformancia): exigí "cambio ADITIVO" en la spec y
  verificalo SEMÁNTICAMENTE** (cargar el JSON de HEAD y el nuevo, comparar por entrada los valores de
  lenguajes preexistentes), no por diff de líneas: un diff con 9 líneas borradas resultó ser reformateo
  inocuo — y un diff "limpio" podría esconder un cambio de valor.
- **NO lances un dev con `&` dentro de un Bash task en background** (p.ej. encadenado tras un commit):
  el task "completa" en el acto, el dev queda huérfano y NO llega notificación al terminar. Un
  lanzamiento de dev = su propio task con run_in_background, sin `&`; los pasos previos van aparte.
  Si ya pasó: watcher (loop que espera el log no-vacío; el timeout de Bash lo corta a los 10 min → re-armar).
- **El PM prepara el entorno ANTES de redactar specs**: instalar deps que los devs van a necesitar
  (p.ej. `pip install` de gramáticas tree-sitter) + smoke de carga. Verifica viabilidad de una vez y
  evita que N devs redescubran la dependencia faltante por separado.

## Lecciones 2026-07-05 (retrofit KDD en ccdd-gate: fallos en cascada del CI convertidos en fixes)
- **Ante un "imposible" del dev: reproducción barata del PM ANTES de re-delegar o descartar.** Un dev
  se negó honestamente a "matar" mutantes de una auditoría de mutación: demostró con fuzz (69k inputs)
  que uno era EQUIVALENTE y que los otros dos ya morían — el tool los reportaba vivos por un bug real
  de `__pycache__` stale. Una reproducción del PM de 1 comando confirmó el bug y convirtió un aparente
  FAIL en dos fixes de producción. Las cláusulas de spec que habilitaron esa honestidad: "si un mutante
  es EQUIVALENTE, documentalo con el análisis y PARA, no lo fuerces" + prohibir inventar tests. Ponelas
  siempre que el hecho verificable pueda ser inalcanzable por razones legítimas.
- **"Replicar los checks del PR" incluye los CONDICIONALES por diff.** Un gate de CI que solo corre si
  el PR toca cierto tipo de archivo (ej: contratos) puede no haber corrido NUNCA hasta tu PR, y fallar
  en cascada por capas (lint → gate completo → mutación). Antes del primer PR que toque un tipo de
  archivo nuevo: leer TODOS los workflows buscando pasos que actúen sobre el diff y replicarlos local.
- **Todo workflow de GitHub editado por un dev se parsea localmente antes de pushear**
  (`python -c "import yaml; yaml.safe_load(open('.github/workflows/X.yml'))"`). Fallo real: un dev
  escribió `- name: KDD: validar...` (dos puntos sin comillas) → YAML inválido → el workflow requerido
  falla en 0s SIN check-runs y la protección de rama bloquea el merge aunque el resto pase. Diagnóstico:
  `gh run list --branch <rama>` con failures de 0s. La suite no cubre workflows; solo el parseo lo caza.
- **Los fallos en cascada de gates apilados son el sistema FUNCIONANDO**: cada re-corrida del PR destapó
  la capa siguiente (cwd de tests → budget → mutación → YAML). No es churn: presupuestá 1 re-delegación
  chica por capa y mantené el criterio "el gate es la ley, el artefacto se adapta al gate" (nunca
  debilitar el gate para que pase — salvo bug demostrado DEL gate, que se arregla con su propio fix).

## Lecciones 2026-07-05 (sesión wargame→KDD: CONTRACT-09, 1 dev, 0 re-delegaciones)
- **KDD es la metodología canónica; esta skill es la capa operativa.** Ante cualquier mejora de proceso:
  actualizar PRIMERO el repo KDD (MauricioPerera/KDD) y reflejar después acá. Los parches RECON NEEDED /
  red-team del HECHO / ABORTAR SI ya están en ambos lados (sincronizados 2026-07-05).
- **El checklist pre-delegación es EJECUTABLE en repos KDD:** `python scripts/validate_specs.py specs`
  (CONTRACT-09) valida los contratos de ejecución — contratos abiertos exigen Tocar SOLO y ABORTAR SI
  rellenado; cerrados (con reporte en docs/reports/) solo baseline. En repos KDD, corrélo como parte de
  la verificación de batch; no confíes en la disciplina del redactor.

## Recuperación tras muerte del host (verificado 2026-07-03)
Los devs en background viven en el árbol de procesos de la app: si la app de Claude se cuelga/cierra,
el task aparece como "stopped — no completion record". Eso NO significa que el dev falló ni que el
trabajo se perdió. Protocolo antes de re-lanzar:
1. **Auditá qué quedó en disco**: `git status`/`git log` (los launchers o el dev pueden haber commiteado),
   archivos `<TAREA>-REPORT.md`, y el transcript del dev en `~\.claude\projects\<cwd-sanitizado>\*.jsonl`
   (mtime = hasta cuándo trabajó; tools usadas = cuánto avanzó).
2. Si el trabajo está completo → verificalo vos como siempre (el log del dev puede estar vacío por el
   corte; el veredicto sale de comandos tuyos, no de su resumen).
3. Si quedó a medias → re-lanzá la MISMA spec (los devs son efímeros e idempotentes sobre specs por
   objetivo); si quedó basura parcial, limpiala o indicá en la spec qué existe ya.
4. Si el host murió DOS veces con dev corriendo → buscá la causa ambiental antes del 3er intento
   (event log de Windows: `Get-WinEvent` Id 1000/1002 para claude.exe; procesos huérfanos; RAM).
   Causa raíz encontrada esa jornada: flota MCP heredada por cada dev (ver "MCP MÍNIMO" arriba).

## Lecciones 2026-07-05 tarde (jornada durabilidad js-doc-store: 13 devs OK, ventana de fallos GLM)
- **GLM cloud tuvo una ventana de ~30 min devolviendo respuestas VACÍAS** (exit 0, log en blanco,
  cero trabajo en disco) para CUALQUIER spec de tarea, mientras prompts cortos ("responde ok")
  funcionaban. Se descartó por diferencial: no era tamaño de spec (subdividirla NO lo arregló), ni
  contenido (la MISMA spec funcionó minutos después), ni flags, ni cwd. Era flakiness del proveedor.
  Matiz sobre la lección vieja "spec grande devuelve vacío": vacío repetido ≠ siempre spec grande —
  antes de subdividir, descartá ventana mala del proveedor con la sonda-tool de abajo.
  CAUSA RAÍZ confirmada al final de la jornada: la cuenta estaba llegando al LÍMITE SEMANAL de Ollama;
  cerca del límite el proveedor degrada a respuestas vacías/`LISTO` falso ANTES de mostrar el error
  explícito ("Server is temporarily limiting requests... weekly usage limit"). Si ves vacíos
  intermitentes que la sonda-tool a veces pasa, revisá la cuota en ollama.com/settings ANTES de
  quemar relanzamientos: cada reintento gasta lo poco que queda.
  OJO: el límite es de la CUENTA de Ollama, no del modelo — aplica a TODOS sus modelos cloud
  (verificado: kimi-k2.7-code:cloud falló con el mismo error). Cambiar de modelo NO es mitigación;
  las únicas salidas son reponer cuota, esperar el reset, o un modelo local (si la tarea lo tolera).
- **La sonda correcta es de TOOLS, no de texto.** En la misma ventana mala, GLM respondió "LISTO" a
  una tarea mínima SIN haberla hecho (mentira, no solo vacío). Sonda válida: "crea el archivo X con
  contenido Y y responde LISTO" DENTRO del cwd del lanzamiento (acceptEdits no auto-aprueba escrituras
  fuera del proyecto — una sonda con path externo da falso negativo en cualquier modelo) y verificar
  que el archivo EXISTE, no que dijo LISTO. Con sonda-tool verificada, lanzar el dev real INMEDIATAMENTE
  en esa ventana buena (verificado: la spec que había fallado 4 veces pasó a la primera).
- **Núcleo con copias vendored congeladas por test de sincronía**: toda spec que toque el núcleo debe
  incluir como paso final "copiar el raíz byte-idéntico sobre <copias>" — si no, la suite rompe por
  diseño y el dev reporta un FAIL que no es suyo. (Patrón: primero un dev desduplica y agrega el test
  de sincronía; desde ahí, TODAS las specs sobre ese archivo llevan el paso de propagación.)
- **El shell del PM puede reiniciarse entre llamadas** (cwd vuelve al default sin aviso; visto 2 veces
  en la jornada): el comando que lanza un dev SIEMPRE lleva su `cd` explícito delante, nunca asumas
  el cwd heredado de una llamada anterior.
- **Features de infraestructura sobre un núcleo vivo: siempre opt-in** (wal/lock/autoflush como
  opciones nuevas con default = comportamiento previo intacto). Permitió aterrizar WAL + transacciones
  + lock + CRC en 6 tareas seguidas sin romper jamás los 15-21 tests preexistentes.
- **Cierre de cadena de features: un harness adversarial de verdad** (crash-injection con SIGKILL real
  a procesos hijos y chequeo de invariantes tras recuperación) como ÚLTIMA tarea, con cláusula "si un
  invariante falla es hallazgo: documentá y dejá el FAIL, prohibido parchear el núcleo o debilitar el
  assert". Valida la cadena entera con evidencia de máquina, no con lecturas.

## Lecciones 2026-07-05 tarde (jornada micro-expert: 6 devs, 2 muertos por cuota, 0 trabajo perdido)
- **Complemento del caso cuota:** además de vacíos/LISTO falso (arriba), el límite semanal puede matar
  devs AL FINAL de la tarea: log de 2 líneas (solo el error de API) pero trabajo COMPLETO y verde en
  disco — murieron escribiendo su REPORT. Ante muerte por cuota: auditá disco y corré el gate ANTES de
  darlo por FAIL; un batch entero se integró así sin re-delegar nada. El gate decide, no el log.
- **Bug de versión fantasma (chequeo de RECON barato en proyectos npm):** código commiteado contra una
  versión de dependencia NUNCA publicada (repomemory "2.19.0" con npm en 2.16.0) → baseline rota en
  tests Y build. Check: `npm view <dep> versions` vs package.json vs los imports que el código usa.
  Fix que preserva la intención: feature-detection en runtime, no borrar la lógica.
- **Baseline rota = tarea T0 antes de cualquier feature**, con los tests rojos existentes como oráculo
  congelado si los hay (17 tests describían funciones jamás implementadas: spec gratis). Los devs de
  features en paralelo reciben en su spec el aviso "la suite completa puede estar roja por X ajeno;
  tu veredicto son TUS suites + no aportar errores nuevos a tsc".

## Lecciones 2026-07-06 (jornada js-store fachada: 6 lanzamientos, 2 re-delegaciones por fallo de SPEC)
- **Dos clases nuevas de fallo de spec al "exponer/subir" a una fachada** (ya integradas al red-team
  del HECHO, arriba, y al repo KDD `knowledge/metodologia-ejecucion.md`): (1) **feature decorativa** —
  se expuso `ensureIndex` pero ningún camino público usaba el índice (`count` seguía escaneando);
  contrato cumplido, tests verdes, valor cero; (2) **contenedor divergente** — `find` delegado literal
  devolvía Cursor lazy en memoria y array en disco; la spec fijaba la shape del doc pero no el
  contenedor. Ambos fueron fallos del PM, no del dev: el dev entregó lo pedido y DECLARÓ el trade-off.
- **La sección de trade-offs del REPORT re-confirmada como el detector más barato**: ambos casos se
  cazaron leyéndola + diff puntual de esa zona (nunca el diff entero). Mantener la exigencia de
  trade-offs en TODA spec.
- **El fix de un batch sin commitear puede re-delegarse sobre el árbol sucio** indicándole al dev que
  los archivos del batch anterior "SON TUYOS para corregir" (caso find→array: el 2º dev corrigió
  código, tests y contrato del 1º sin fricción). El commit llega cuando el batch completo pasa el
  veredicto del PM.
- **Ojo con el pipe al verificar la suite**: `node --test | tail` enmascara el exit code (el pipeline
  devuelve el exit de tail). O capturás el conteo con grep de `pass/fail`, o corrés sin pipe y validás
  exit 0; una corrida "verde" por pipe no es evidencia.
- **Pendiente colateral como parte de la spec siguiente**: recrear la sección `[Unreleased]` del
  CHANGELOG se le encargó al dev de la tarea siguiente en una línea (cerró el pendiente sin tarea
  propia). Micro-encargos de integración viajan gratis en la spec que ya toca ese archivo.
