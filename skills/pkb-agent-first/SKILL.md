---
name: pkb-agent-first
description: Operar el sistema "PocketBase Agent-First task manager" del repo D:\Repo\pkb — backend local (PocketBase :8090 + Worker Node :8787 + MCP pocketbase) donde delegas tareas de desarrollo a sub-agentes GLM, disparadas por webhook y verificadas contra tests definidos de antemano. Úsala para: crear/lanzar/monitorear dev-tasks; definir PLANES encadenados (depends_on) que el sistema ejecuta en orden, despliega (deploy_to) y notifica al terminar (notify_url); verificar hooks de PocketBase contra una PB efímera (pb_integration); usar el backbone determinista agent_tasks; habilitar acceso VPS on-demand (needs_vps); levantar 2ª instancia PB para otro proyecto; o arrancar/parar/verificar los servicios. NO la uses para otros proyectos ni para delegación GLM genérica sin este backend.
---

# PocketBase Agent-First — guía de uso

Backend local en `D:\Repo\pkb`. Doc canónica completa: `D:\Repo\pkb\README.md`.
Dos planos: **determinista** (reglas/hooks en PocketBase, 0 tokens) y **agente** (sub-agentes GLM
solo cuando hace falta juicio). Idea del task-manager: **defines el plan, el sistema lo ejecuta,
verifica, despliega y te avisa; tú solo revisas el resultado.**

## 0. Componentes y salud (comprueba SIEMPRE primero)
- **PocketBase** `http://127.0.0.1:8090` (binario en `C:\Users\Administrador\Desktop\pocketbase_0.39.5_windows_amd64`).
- **Worker** Node `http://127.0.0.1:8787` (`D:\Repo\pkb\pb-worker`), lanza GLM (`ollama launch claude --model glm-5.2:cloud`).
- **MCP `pocketbase`** (`D:\Repo\pkb\pb-mcp`, 13 tools) — control desde una sesión de Claude.
- Colecciones: `agent_tasks` (backbone determinista) y `dev_tasks` (gestor de dev-tasks).
- Credenciales: superuser `mauricio.perera@gmial.com`; la contraseña vive SOLO en `pb-worker/.env`
  (gitignoreado). NUNCA en código ni en commits.
```
curl -s http://127.0.0.1:8090/api/health   # API is healthy
curl -s http://127.0.0.1:8787/health        # {"ok":true,"mode":"real",...}
```

## 1. Operación de servicios (Windows, DETACHED — sobreviven al cierre de shells)
```powershell
# PocketBase (si esta caido; a veces otro proceso ocupa :8090)
$d="C:\Users\Administrador\Desktop\pocketbase_0.39.5_windows_amd64"
Start-Process -FilePath (Join-Path $d "pocketbase.exe") -ArgumentList "serve","--dev","--http=127.0.0.1:8090" `
  -WorkingDirectory $d -WindowStyle Hidden -RedirectStandardOutput (Join-Path $d "pb.out.log") -RedirectStandardError (Join-Path $d "pb.err.log")
# Worker (carga .env, modo real)
powershell -ExecutionPolicy Bypass -File D:\Repo\pkb\pb-worker\start-worker.ps1 -ExecMode real -BlockedVerify on
powershell -ExecutionPolicy Bypass -File D:\Repo\pkb\pb-worker\stop-worker.ps1
```
Los **hooks** (`pb_hooks/*.pb.js`) NO tienen hot-reload fiable → reiniciar `pocketbase.exe` tras cambiarlos.

## 2. Delegar una dev-task (flujo principal)
Defines la tarea CON sus tests antes que el código; al marcarla `ready`, el hook dispara el webhook
al worker, que lanza GLM y verifica. En modo real reintenta hasta `MAX_ATTEMPTS=2` si `failed`.

**Vía MCP** (preferido, con el MCP `pocketbase` cargado en la sesión):
1. `create_dev_task(title, spec, test_kind, tests, target_files?, work_dir?, needs_vps?, depends_on?, plan?, deploy_to?)` → crea en `draft`.
2. `mark_dev_task_ready(id)` → dispara el pipeline.
3. `get_dev_task(id)` / `list_dev_tasks(status?)` para ver estado. El worker escribe `status`,
   `result` (json), `logs`, `attempts`. Artefactos del agente en `pb-worker/runs/<taskId>/`.

**Vía REST** (si el MCP no está cargado — p.ej. tras rotar la contraseña): autenticar y POST/PATCH
a `/api/collections/dev_tasks/records` con la password de `pb-worker/.env`.

### Campos de `dev_tasks`
| Campo | Para qué |
|-------|----------|
| `title`, `spec` | Título y descripción de qué implementar |
| `test_kind` | Cómo se verifica (ver §3) |
| `tests` | El test/oráculo congelado (formato según test_kind) |
| `target_files` (json) | Archivos que el agente debe producir |
| `work_dir` | Dónde trabaja (default `pb-worker/runs/<id>`) |
| `status` | draft→ready→running→passed/failed/needs_review; `waiting` (esperando deps) |
| `result`, `logs`, `attempts` | Salida del worker |
| `needs_vps` (bool) | Acceso VPS on-demand (§5) |
| `depends_on` (json) | Ids de dev_tasks que deben estar `passed` antes (plan runner, §2.1) |
| `plan` (text) | Etiqueta para agrupar y consultar `/api/plan/{plan}` |
| `deploy_to` (text) | Directorio destino: al `passed`, copia ahí los `target_files` (§2.2) |
| `notify_url` (text) | URL a la que POSTear al terminar (§2.3) |

### 2.1 Planes multi-tarea (define el plan, revisa/espera el aviso al final)
Crea N tareas con `depends_on` (ids) + mismo `plan`, márcalas TODAS `ready`. El sistema ejecuta EN
ORDEN: las que tienen deps sin cumplir quedan en `waiting`; al `passed` de una dep, el worker libera
las dependientes; si una dep termina `failed`/`needs_review`, sus dependientes pasan a `failed` en
**cascada** (no se quedan colgadas). Consulta: `GET /api/plan/{plan}` (superuser) → `{done, counts, tasks}`.

### 2.2 Deploy del artefacto verificado (`deploy_to`)
Si la task trae `deploy_to` (directorio), al `passed` el worker copia los `target_files`
**verificados** ahí y lo registra en `result.deployed`. Así lo probado ES lo desplegado, sin
integración manual (para archivos; NO cubre transformaciones como inlinear en un hook goja → usa `pb_integration`).

### 2.3 Notificación de fin (`notify_url`)
El worker POSTea al terminar. Con `plan`: una sola notificación cuando TODAS terminan
(`{type:'plan', plan, done, counts, tasks}`). Sin plan: `{type:'task', id, status}`. Apunta
`notify_url` a tu canal (ntfy/Slack/n8n/endpoint local) para enterarte sin poll-ear. (El push va a
esa URL, no a una sesión de Claude.)

## 3. test_kind — el campo `tests` cambia por tipo
- **plain_pytest**: `tests` = archivo pytest. Worker corre `pytest`; exit 0 → passed.
- **plain_node**: `tests` = test `node --test`.
- **ccdd**: `tests` = pytest congelado (oráculo INDEPENDIENTE del target). El agente implementa con
  el CCDD gate y escribe `_gate_verdict.json`; el worker re-congela el oráculo y lo corre él mismo
  (solo confía en la señal `blocked` del verdict). Un `blocked` se somete a un **refuter adversario**
  (2º GLM); si lo refuta → `passed`.
- **oop** (out-of-process, anti-código-adversario): `tests` = JSON
  `{"import_from":"mymod","cases":[{"fn":"f","args":[2,3],"expect":5}]}`. El worker ejecuta el target
  en subproceso aislado y compara por igualdad profunda. Úsalo si no confías en el implementador.
- **pb_integration**: verifica un **hook de PocketBase real** contra una **PB efímera**.
  `target_files` = los `.pb.js`; `tests` = test `node --test` que golpea la PB viva
  (env `PB_URL`/`PB_ADMIN_*`) y assertiona los efectos. El worker levanta la PB efímera con el hook,
  corre el test y la mata. Cierra el punto ciego de verificar hooks integrados. Env `PB_BIN` = binario.
- **go_test**: implementación en **Go** (tipada, framework PocketBase) verificada con `go test`.
  `target_files` = `.go` (package `shop`); `tests` = `*_test.go` congelado. El worker asegura
  `go.mod`, corre `go mod tidy` + `go test ./...`. Sin footguns de goja; para lógica de negocio
  seria. (PoC de binaria custom en `pb-go-poc/`.)
- **none**: sin verificación → `needs_review`.

**Resultados:** `passed` (OK) · `failed` (impl mala pero satisfacible → reintenta) · `needs_review`
(vía `blocked` con `result.reason`, o `test_kind=none`; no reintenta).

## 4. Acceso VPS on-demand (`needs_vps`)
Bool, **default false = SIN acceso** (seguro). Con `true`, el worker añade `mcp__vps__*` a los
allowedTools del sub-agente (VPS Ubuntu root `31.220.22.176`, tiene claude+ollama+glm) y le indica el
host. Solo en tareas que necesiten Linux/despliegue/más cómputo. Requiere el MCP `vps` en la config
de Claude de la máquina. Gating verificado en ambas direcciones.

## 5. Backbone determinista (`agent_tasks`) — 0 tokens
Cola donde reglas fijas resuelven lo resoluble; solo lo ambiguo escala a IA.
- `create_task(type, input, priority?)` → el hook asigna `done` si una regla aplica (`classify` con
  `input.rules` keyword→categoría; `decide` con `input.value`+`threshold`), si no `needs_ai`.
- `pull_pending_tasks(type?, limit?)` → solo los `needs_ai` (endpoint `GET /api/agent/pending`).
- `submit_task_result(id, output, status="done")` → cierra el loop del agente.

## 6. Segunda instancia PocketBase (otro proyecto, sin conflicto)
Cambiar el puerto NO basta: cada instancia necesita su propio `--dir`.
```
pocketbase.exe serve --http=127.0.0.1:8091 --dir "C:\ruta\inst2\pb_data" --hooksDir "C:\ruta\inst2\pb_hooks"
```
Crea su superuser antes: `pocketbase.exe superuser upsert <email valido con TLD> <pass> --dir <pb_data>`.
Ejemplo montado en el repo: `shop-pb/` (:8091), una tienda order-taking (products/buyers/orders +
hook determinista de pedidos). Apunta los componentes a otra instancia con env: worker `PB_URL`,
MCP `-e PB_URL=...`, hook `dev_tasks.pb.js` → URL del webhook.

## 7. Verificar el sistema (selftests deterministas, sin gastar GLM)
```
# PARA el worker real de :8787 antes (comparte webhook y robaria las tareas)
cd D:\Repo\pkb\pb-worker
node selftest.mjs; node selftest_hybrid.mjs; node selftest_refuter.mjs; node selftest_oop.mjs   # 19/19
# reinicia el worker en real al terminar
```
Camino GLM real / pb_integration: una dev_task sencilla y polling (cuesta 1 lanzamiento GLM, barato).

## 8. Gotchas y notas operativas de ESTA máquina
- **git se cuelga en Git Bash** por filtros git-lfs globales → usa **PowerShell** con
  `-c filter.lfs.process=` (ej. `git -C D:\Repo\pkb -c filter.lfs.process= add ...`). `.env` gitignoreado; nunca commitear secretos.
- Lanza servicios **detached** (Start-Process), no como background del shell (mueren → exit 127).
- Las tools `mcp__pocketbase__*` se cargan al arrancar la sesión; si rotaste la contraseña, reinicia
  Claude Code para refrescar la conexión (mientras tanto usa REST).
- PocketBase 0.39.5: helpers de hooks DENTRO del handler; `record.get(campoJson)` devuelve bytes
  (JsonRaw, `Array.isArray` es true) → decodifica bytes→string→`JSON.parse`; un number `required`
  rechaza `0`; email de superuser necesita TLD válido.

## 9. Como orquestador (PM) delegando a GLM
Este sistema ES el canal de delegación: en vez de `ollama launch claude` a mano, crea `dev_tasks`
con tests congelados y deja que el worker lance/verifique/despliegue/notifique. Redacta specs
autocontenidas; **verifica por artefacto** (status + tests reales + archivos en `runs/`), no por la
palabra del agente. Para trabajo grande, define un **plan** encadenado y espera el `notify_url`.
Complementa la skill `pm-glm-ccdd`.
