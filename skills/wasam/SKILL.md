---
name: wasam
description: >-
  Crear, servir y operar web apps locales sobre PHP (WebAssembly) + SQLite con la
  CLI `wasam`, e interactuar con ellas por API HTTP o por CLI. Úsala cuando el
  usuario quiera levantar una app local PHP+SQLite sin instalar PHP/Apache/MySQL,
  exponer una REST API en localhost para que otra app o un agente la consuma, o
  cuando mencione "wasam", "php-wasm", "app local php sqlite", o pida que un agente
  interactúe por CLI/HTTP con una app local.
---

# wasam — web apps locales PHP-WASM + SQLite

`wasam` corre apps PHP (compilado a WebAssembly, sin instalar PHP/Apache/MySQL) con
SQLite, **server-side en Node**, cada app en su propio puerto loopback
(`127.0.0.1:<port>`). Dos vías de interop, ambas disponibles a la vez:

- **API HTTP**: cualquier proceso pega a `http://localhost:<port>/...` (curl, fetch, otra app).
- **CLI**: `wasam call <app> <MÉTODO> <ruta> [json]` hace la request por ti (ideal para un agente).

## Modelo mental (importante)

- El **paquete** (`wasam-kit`, el runtime) está instalado globalmente; tú no lo tocas.
- Los **datos** viven en un **workspace = el directorio actual**: un `registry.json`
  (mapa app→puerto) y una carpeta `apps/`. Cada app es `apps/<app>/public/index.php`
  (front controller PHP) + `apps/<app>/store/app.sqlite` (su base, archivo real en disco).
- Antes de crear apps en un directorio, hay que inicializarlo una vez con `wasam init`.

## Instalación (una vez)

Si `wasam` no está disponible (`wasam help` falla), instálalo desde el repo del kit:

```bash
cd <ruta-a-wasam-kit> && npm install && npm link    # binario global `wasam`
# o local, sin global:  npm install   y luego  node bin/wasam.cjs <cmd>
```

Requiere Node ≥ 18.

## Comandos

```
wasam init [dir]                          inicializa el workspace (registry.json + apps/) en el dir actual o <dir>
wasam new <app>                           crea apps/<app> desde el starter y le asigna un puerto libre
wasam start <app>                         arranca el server de la app (detached) y guarda su PID
wasam stop <app>                          detiene la app
wasam list                                tabla: app | puerto | estado (running/stopped)
wasam call <app> <MÉTODO> <ruta> [json]   request HTTP a la app (la auto-arranca si está parada)
wasam help                                ayuda
```

`call` **auto-arranca** la app si no está corriendo y la deja viva para llamadas
sucesivas. Su **stdout** es solo `status` + `body` (parseable); las notas van a stderr.

## Flujo típico (para un agente)

```bash
wasam init                                   # una vez por directorio de trabajo
wasam new miapp                              # crea apps/miapp, p.ej. en puerto 3001
# ... editar apps/miapp/public/index.php con la lógica deseada (ver abajo) ...
wasam call miapp GET /info                   # auto-arranca y responde
wasam call miapp POST api/notes '{"text":"hola"}'
wasam call miapp GET api/notes
# interop directa equivalente, sin la CLI:
curl -s localhost:3001/api/notes
```

## Ruta en `call` y el shell (gotcha real)

git-bash (MSYS) convierte un argumento que **empieza con `/`** en una ruta Windows
antes de que llegue al programa. Para evitarlo:

- **git-bash**: pasa la ruta **sin barra inicial** → `wasam call miapp GET api/notes`
  (o exporta `MSYS_NO_PATHCONV=1`). El CLI también intenta recuperar rutas ya mangled.
- **PowerShell / cmd**: usa la barra inicial normal → `wasam call miapp GET /api/notes`.

## Cómo es una app (el `index.php`)

`apps/<app>/public/index.php` es un front controller PHP que recibe cada request y
responde. La ruta de la base SQLite llega en `$_SERVER['DB_PATH']`. Esqueleto mínimo:

```php
<?php
header('Content-Type: application/json; charset=utf-8');
$db = new PDO('sqlite:' . ($_SERVER['DB_PATH'] ?? '/app/app.sqlite'));
$db->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
$db->exec('PRAGMA journal_mode=WAL');
$db->exec('PRAGMA busy_timeout=5000');
$db->exec('CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)');

$method = $_SERVER['REQUEST_METHOD'] ?? 'GET';
$path   = rtrim(parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH), '/') ?: '/';

if ($path === '/info' && $method === 'GET') {
    echo json_encode(['app' => 'miapp', 'php' => PHP_VERSION, 'sqlite' => true]); exit;
}
if ($path === '/api/items' && $method === 'GET') {
    echo json_encode($db->query('SELECT * FROM items')->fetchAll(PDO::FETCH_ASSOC)); exit;
}
if ($path === '/api/items' && $method === 'POST') {
    $in = json_decode(file_get_contents('php://input'), true) ?: [];
    $st = $db->prepare('INSERT INTO items (name) VALUES (:n)');
    $st->execute([':n' => (string)($in['name'] ?? '')]);
    http_response_code(201);
    echo json_encode(['id' => (int)$db->lastInsertId()]); exit;
}
http_response_code(404);
echo json_encode(['error' => 'no encontrada', 'path' => $path]);
```

La app que crea `wasam new` trae de ejemplo una REST API de "notas"
(`GET /info`, `GET|POST /api/notes`, `POST /api/notes/{id}/toggle`,
`DELETE /api/notes/{id}`, y `GET /` sirve `app.html`). Úsala como referencia y
reescribe `index.php` con la lógica que necesites: tienes PHP 8.x + PDO SQLite completo.

## Notas y límites

- **Concurrencia**: una instancia PHP por app, requests serializados. Apropiado para
  herramienta local de un usuario, no para alta concurrencia.
- **Persistencia**: la DB vive en el FS en-memoria de PHP y se vuelca a
  `apps/<app>/store/app.sqlite` tras cada request (evita el "disk I/O error 10" de
  NODEFS). El archivo es SQLite real, legible por otras herramientas.
- **Puertos**: se asignan incrementando desde 3001; míralos con `wasam list`.
- **Aislamiento**: cada app es su carpeta + su puerto + su SQLite; copiar la carpeta
  `apps/<app>` (y registrar el puerto) replica la app en otro workspace.
