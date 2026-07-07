---
name: delegar-ollama
description: Cómo lanzar y verificar CUALQUIER modelo servido por Ollama (glm-5.2:cloud, kimi-k2.7-code:cloud, etc.) en modo headless vía `ollama launch claude`, agnóstico al modelo y a la tarea. Cubre: comando de lanzamiento, probe de vida, `< /dev/null` obligatorio, MCP mínimo, anti-cuelgue, verificación de que respondió de verdad (no solo que "dijo LISTO"), y comportamiento de cuota. Úsala como capa base de mecánica de delegación desde cualquier skill que orqueste un modelo vía Ollama (p.ej. `pm-glm-ccdd`, `delegar-glm-ccdd`). NO decide qué tarea delegar ni valida contratos CCDD — eso es de la skill que te trajo acá.
---

# Delegar a un modelo vía Ollama (headless) — mecánica agnóstica al modelo

Patrón de lanzamiento reutilizable, independiente del modelo (`<MODEL>`: `glm-5.2:cloud`, `kimi-k2.7-code:cloud`, etc.) y del repo (`<REPO>`: cwd salvo que se indique otro). Esta skill NO sabe de CCDD, contratos ni de qué tarea estás delegando — solo de cómo hablarle a un modelo por Ollama sin que se cuelgue o devuelva vacío.

## Comando base
```bash
ollama launch claude --model <MODEL> -y -- --strict-mcp-config --mcp-config '{"mcpServers":{}}' -p "$(cat <prompt.txt>)" --dangerously-skip-permissions < /dev/null > <log.txt> 2>&1
```
- **`< /dev/null` OBLIGATORIO.** Sin él, `claude` espera stdin y el lanzamiento sale VACÍO (exit 0, sin trabajo).
- **`--strict-mcp-config --mcp-config ...` OBLIGATORIO** (verificado 2026-07-03/04): sin él, cada lanzamiento hereda y levanta TODA la flota MCP global del usuario (n8n, github, chrome, computer-use...) — decenas de procesos que colgaron la app anfitriona dos veces (evento Windows 1002 "dejó de interactuar"). Regla: si la tarea NO usa el gate CCDD → `'{"mcpServers":{}}'`; si lo usa → un JSON con SOLO la entrada `ccdd-complexity` copiada de `~/.claude.json`.
- Prompt en ARCHIVO + `$(cat ...)`, nunca inline: evita problemas de comillas/multilínea.
- **Permisos:** `--dangerously-skip-permissions` es lo más simple (repo desechable). Alternativa más contenida: `--permission-mode acceptEdits --allowedTools "Bash,mcp__ccdd-complexity__*"` — ojo que `acceptEdits` SOLO auto-aprueba Edit/Write; en headless no hay quién apruebe Bash/MCP, así que sin `--allowedTools` explícito el modelo reescribe archivos pero NO puede correr tests/gate y cae a "autoevaluación estática" (PASS falso). Usá `--allowedTools` con exactamente lo que la tarea necesita.
- El modelo hereda el **cwd** desde el que lanzás — `cd <REPO>` antes, o pasalo en el prompt.
- Tareas largas: `run_in_background: true`, leé el log/`.output` al llegar la notificación de fin.

## Variante `/goal` (verificado 2026-07-02, claude ≥ 2.1.139)
Para que el modelo siga trabajando SOLO hasta cumplir una condición (un evaluador independiente juzga tras cada turno y lo devuelve a trabajar con feedback si no cumplió):
```bash
ollama launch claude --model <MODEL> -y -- -p "/goal <condición>" --dangerously-skip-permissions < /dev/null > <log.txt> 2>&1
```
- La condición: estado final + chequeo demostrable en la conversación + restricciones + **tope OBLIGATORIO** ("o parar tras N turnos", máx 4.000 chars) — sin tope no hay límite de gasto.
- **El tope de turnos NO protege bucles DENTRO de un turno.** El evaluador corre al TERMINAR cada turno; un modelo que loopea llamando tools nunca termina el turno y el evaluador jamás se ejecuta (caso real: 992 reintentos de una misma tool, 67 min). El timeout del task en background TAMPOCO lo mata. Único guardián real: monitorear el transcript en disco (¿crece sin avanzar? → matar el proceso).
- El evaluador NO ejecuta comandos: solo juzga lo que el modelo mostró — la condición debe exigir salida REAL pegada. Veredicto queda como `goal_status` en el transcript.
- Reemplaza la re-delegación manual por FAIL dentro de una misma invocación (reintentos automáticos con la razón del evaluador como feedback). Costo del evaluador: despreciable (~1,5k tokens/veredicto).

## Probe de vida
```bash
ollama launch claude --model <MODEL> -- -p "Responde: VIVO" --permission-mode plan < /dev/null
```
Debe imprimir `VIVO`. Modelos cloud requieren `ollama signin`. Si no responde, no sigas a ciegas — decilo tajante al usuario y ofrecé alternativa.

**Sonda de TOOLS, no de texto, si sospechás degradación** (ver "Cuota" abajo): "creá el archivo X con contenido Y y respondé LISTO" DENTRO del cwd real, y verificá que el archivo EXISTE — no que dijo LISTO. Un modelo degradado puede responder LISTO sin haber hecho nada.

## Anti-cuelgue
- **Ningún proceso en foreground que no termine solo.** Un server bloqueante (`npm start`/`node server.js` a secas) cuelga el lanzamiento para siempre. Instruí explícito: server en BACKGROUND, matarlo al final, todo proceso debe terminar solo.
- **No lances el modelo con `&` dentro de un Bash task en background** (p.ej. encadenado tras un commit): el task "completa" en el acto, el proceso queda huérfano y NUNCA llega notificación de fin. Un lanzamiento = su propio task con `run_in_background`, sin `&`; los pasos previos van aparte.
- **CLI que funciona headless desde acá: solo `claude` (vía `ollama launch claude`).** `agy` (Antigravity) y `codex` se CUELGAN en modo no-interactivo (esperan TTY) — no los uses para delegar.

## Log vacío ≠ colgado
En headless `-p` el log se escribe AL FINAL — log vacío no significa que no avanza. Para saber si un proceso sigue vivo: `ls -la` de los entregables esperados y de `__pycache__/` u otro artefacto de build (mtime reciente = está corriendo AHORA). Recién si nada cambia en disco por varios minutos, tratalo como colgado.

## Error transitorio "Could not verify your plan"
El lanzamiento muere al instante (exit 1, log de 1 línea). No es culpa del prompt ni del modelo — no lo depures, relanzá.
- Aparece casi siempre en el PRIMER lanzamiento de un batch concurrente. Mitigación que funciona: **escaloná arranques 25-35s entre lanzamientos** (`sleep N &&` antes del comando) y relanzá el fallido con `sleep 100 &&`.
- Si falla 2+ veces seguidas incluso con delay: sondeá el verificador con un lanzamiento mínimo en foreground (probe de vida arriba, timeout 3 min). Si la sonda responde, relanzá el real INMEDIATAMENTE (ventana buena). Si la sonda también falla, es cuota/estado de cuenta — reportalo, no reintentes.

## Cuota y disponibilidad (de CUENTA, no de modelo)
El límite de uso es de la **cuenta** de Ollama, no del modelo puntual — aplica a TODOS sus modelos cloud (verificado con `glm-5.2:cloud` Y `kimi-k2.7-code:cloud` fallando por la misma causa).
- Cerca del límite semanal, el proveedor puede degradar a **respuestas vacías** (exit 0, log en blanco, cero trabajo en disco) O a **"LISTO" falso** (responde que terminó sin haber hecho nada) ANTES de mostrar el error explícito ("Server is temporarily limiting requests... weekly usage limit").
- Si ves vacíos/LISTO-falso intermitentes que una sonda de texto a veces "pasa": usá la sonda de TOOLS (arriba) y revisá cuota en ollama.com/settings ANTES de quemar relanzamientos — cada reintento gasta lo poco que queda.
- Cambiar de modelo NO es mitigación (el límite es de cuenta). Únicas salidas: reponer cuota, esperar el reset, o un modelo local si la tarea lo tolera.
- La cuota también puede matar un proceso al FINAL de una tarea ya completa: log de 2 líneas (solo el error de API) pero trabajo COMPLETO y verde en disco. Ante una muerte por cuota, auditá disco/corré la verificación ANTES de dar la tarea por FAIL.

## Subagentes y agent teams dentro de un modelo delegado (verificado 2026-07-02)
- **Subagentes (tool `Agent`): disponibles headless SIN flag**, verificado en GLM y Kimi. Deja su propio transcript en `<proyecto>\<session>\subagents\agent-*.jsonl`.
- **Agent teams (task list compartida + mensajería): protocolo disponible headless con `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`** en el env del lanzamiento (TeamCreate → TaskCreate → spawn con team_name → teammates reclaman de la task list → SendMessage/inbox → TeamDelete). Cap de Ollama (~3 cloud concurrentes) cuenta lead + teammates.
- **Qué modelo sirve de lead es específico de cada modelo — no asumas que cualquiera puede.** Verificalo en la skill que orquesta ese modelo puntual (p.ej. `pm-glm-ccdd` documenta que GLM no sirve de lead y reporta éxito falso).

## Recuperación tras muerte del host (verificado 2026-07-03)
Un proceso lanzado en background vive en el árbol de la app anfitriona: si esta se cuelga/cierra, el task aparece "stopped — no completion record". Eso NO significa que el trabajo se perdió.
1. Auditá disco: `git status`/`git log`, archivos de reporte esperados, y el transcript en `~\.claude\projects\<cwd-sanitizado>\*.jsonl` (mtime = hasta cuándo trabajó).
2. Si el trabajo está completo → verificalo como siempre (el veredicto sale de comandos reales, no del resumen).
3. Si quedó a medias → relanzá la MISMA spec/condición (los lanzamientos son efímeros e idempotentes sobre specs por objetivo).
4. Si el host murió DOS veces con el mismo lanzamiento corriendo → buscá causa ambiental antes del 3er intento (event log de Windows `Get-WinEvent` Id 1000/1002; procesos huérfanos; RAM; flota MCP heredada — ver "MCP mínimo" arriba).

## Paralelismo
- Cap práctico: **~3 modelos cloud concurrentes en Ollama** — no dispares más a la vez.
- Lanzamientos concurrentes sobre el MISMO repo → cada uno necesita su perímetro de archivos disjunto (lo declara la skill que orquesta la tarea, no esta).
