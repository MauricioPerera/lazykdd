# Contrato 30 — Gate de UX/accesibilidad: la frontera mecánico/juicio en una página web

Prerrequisitos: contratos 01-29 cerrados, HEAD `5c06bbd`+, suite 394 verde 2×, CI verde en
ambas patas. Nace de evidencia real de ESTA sesión: al construir un landing page de KDD
(fuera del repo, en el scratchpad), el PM verificó A MANO — balance de tags HTML, cruce de
80 claves de i18n contra dos diccionarios, contraste de color por inspección computada,
presencia de guardas `prefers-reduced-motion`, IDs referenciados por JS — la misma clase de
práctica manual repetida que disparó C28. RECON honesto: hoy el repo no tiene NINGÚN
artefacto HTML propio; este contrato construye la herramienta genérica y su primer
ejemplo real bajo `examples/`, dejando la decisión de publicar el landing page a GitHub
Pages completamente aparte (no es parte de este contrato).

> Capa: contrato de ejecución. T1 (código, dev efímero) lleva su task contract en
> `knowledge/contracts/ux-page-gate.md`. T2 (ejemplo + cableado + docs) es del
> orquestador. El gate es de nivel 1, capa OPCIONAL (como `validate_rules`/
> `validate_skills`): sin páginas HTML que analizar, INFO + exit 0.

Honestidad de alcance — la MISMA frontera mecánico/juicio que ya midió C23 (editorial),
aplicada a una página web en vez de un artículo:

**Mecánico, contratable hoy (todo stdlib, sin navegador real)** — dos ajustes al diseño
original, hechos ANTES de delegar, tras leer a fuente completa `google-labs-code/design.md`
(25k stars, el linter de facto para este problema): (1) el chequeo de contraste pasa de
grepear propiedades CSS libres a exigir una sección de DATOS explícita y estructurada —
exactamente la clase de robustez que ganamos al pasar el i18n de objeto-JS-literal a JSON
embebido; (2) la severidad deja de ser implícita — se calibra contra su precedente real de
producción (`contrast-ratio` es `warning` en su linter, solo referencias rotas son error):

- **HTML_UNCLOSED** (ERROR) — balance y anidamiento correcto de tags (parser de
  `html.parser`, mismo enfoque que el chequeo que el PM corrió a mano esta sesión).
- **I18N_DATA_MISSING / I18N_DATA_INVALID / I18N_MISSING** (ERROR) — toda clave
  `data-i18n`/`data-i18n-html` referenciada en el HTML debe existir en TODOS los idiomas de
  un diccionario. Requiere una convención NUEVA (no la que usa el landing page actual, que
  embebe un objeto JS literal): los datos de i18n deben vivir en
  `<script type="application/json" id="i18n-data">{"en":{...},"es":{...}}</script>` — JSON
  parseable por `json.loads`. ERROR porque una clave de i18n faltante es, en la práctica,
  una referencia rota (el equivalente exacto de `broken-ref` en design.md, que también es
  error).
- **ID_UNRESOLVED** (ERROR) — IDs referenciados por `getElementById`/`querySelector('#...')`
  (extracción best-effort por regex) deben existir como `id="..."` en el HTML — otra
  referencia rota real (JS lanzaría en runtime).
- **CONTRAST_LOW** (WARNING) — contraste WCAG 2.1 (fórmula pública, sin inventar umbrales;
  la misma luminancia relativa con corrección gamma que usa `color-parser.ts` de
  design.md, verificado independientemente). Se calcula SOLO sobre pares declarados
  explícitamente, NO sobre cualquier custom property de texto libre: un bloque
  `<script type="application/json" id="ux-contrast-pairs">[{"scope":"root","text":"#..","bg":"#.."}, {"scope":"dark","text":"#..","bg":"#.."}, {"scope":"light","text":"#..","bg":"#.."}]</script>`
  — `scope` nombra el bloque de origen (informativo, para el mensaje), no se re-deriva del
  CSS. Umbral AA texto normal: ratio >= 4.5. WARNING, no ERROR: coincide con la calibración
  real de design.md — un contraste bajo es una alerta de accesibilidad, no una ruptura
  estructural del documento.
- **MOTION_UNGUARDED** (WARNING) — presencia de una guarda
  `@media (prefers-reduced-motion: reduce)` cuando el CSS declara `@keyframes`, `animation`
  o `transition` — chequeo textual, no de comportamiento real. WARNING por el mismo
  argumento: accesibilidad recomendada, no ruptura del documento.

El exit code del CLI sigue el precedente ya establecido en `validate_contracts.py`
(`FM_KEY_forbids` es WARNING desde C10): exit 1 solo si hay >=1 finding ERROR; los WARNING
se reportan siempre pero no bloquean.

**Frontera declarada, code_only o directamente FUERA (no este contrato)**:
- Comportamiento real de layout: overflow en anchos con nombre, si un `position:sticky`
  queda pegado durante TODO el rango de scroll (bug real que el PM encontró esta sesión —
  `align-self:stretch` rompía el sticky en un motor real aunque el CSS fuera válido).
  Exige un navegador de verdad; fuera del nivel 1 por doctrina (mismo argumento que el
  servidor MCP vivo en C25).
- Errores de consola al cargar: exige ejecutar el JS en un motor real.
- Aspecto real de `:focus-visible` renderizado: exige un navegador.
- Si el diseño es lindo, si la metáfora del expediente funciona, si la paleta es la
  correcta: juicio humano, declarado FUERA — la misma lección de C23 (editorial).

## T1 — `scripts/validate_ux_page.py` (dev efímero)

OBJETIVO: implementar contra el oráculo congelado `tests/test_validate_ux_page.py`
(autorado y sellado por el orquestador): `_check_tag_balance` (ERROR),
`_check_i18n` (ERROR), `_check_ids` (ERROR), `_check_contrast` (WARNING; lee el bloque
JSON `#ux-contrast-pairs`, NUNCA parsea CSS libre; fórmula WCAG 2.1: luminancia relativa
con corrección gamma, `(L1+0.05)/(L2+0.05)`), `_check_motion` (WARNING), agregadas por
`validate_ux_page(html_path) -> list` (findings `{'file','level','rule','msg'}`
ordenados); `main(argv) -> int` (uno o más paths de archivo/directorio; capa opcional:
ausente o sin `.html` -> INFO exit 0; exit 1 solo si hay >=1 ERROR, WARNING nunca bloquea;
Resumen honesto con archivos ESCANEADOS, lección C24). Reglas, mensajes y niveles EXACTOS:
docstring del oráculo. Estilo `validate_skills.py`; ASCII; stdlib puro (`html.parser`,
`re`, `json`, `math` si hace falta para la fórmula).

## T2 — Ejemplo real + cableado (autoría del orquestador)

`examples/ux-page/demo.html` (página mínima autocontenida, NO el landing page completo —
un ejemplo proporcional como el resto de `examples/`, con los 5 aspectos verificables
presentes: HTML balanceado, i18n embebido como JSON con 2 idiomas, un bloque
`#ux-contrast-pairs` con 3 pares `root`/`dark`/`light` de contraste válido, una animación
con su guarda de reduced-motion, un `getElementById` que resuelve); `examples/ux-page/
demo-broken.html` NO se agrega (los casos rotos viven en el oráculo, no en el repo);
artefactos al MANIFEST de `init_project`; paso de CI (8vo, opcional);
`knowledge/data_models/ux_page_contract.md` (la convención JSON de i18n y de pares de
contraste, la tabla de severidades ERROR/WARNING con su justificación, la frontera
mecánico/juicio); índice; README EN/ES; `knowledge/validacion.md`; CHANGELOG.

## Criterios de aceptación

- [ ] `python -m unittest tests/test_validate_ux_page.py` verde SIN modificar el oráculo.
- [ ] `python scripts/validate_ux_page.py examples/ux-page` exit 0 sobre el ejemplo real.
- [ ] Mutación PM (sobre copia del ejemplo): romper el par `dark` de
  `#ux-contrast-pairs` → `CONTRAST_LOW` (WARNING) nombrando el scope y el ratio calculado,
  exit code SIGUE en 0 (WARNING no bloquea); agregar una `@keyframes` sin guarda de
  reduced-motion → `MOTION_UNGUARDED` (WARNING), exit 0 igual; borrar una clave de un
  idioma en `#i18n-data` → `I18N_MISSING` (ERROR), exit 1 — demuestra que el exit code
  distingue ambas clases.
- [ ] Los 7 gates existentes exit 0; suite completa 2× verde; post-init neutral (el
  ejemplo se borra, capa opcional pasa a INFO tras el borrado).
- [ ] Final: CI verde en ambas patas (8vo paso nuevo, opcional).

## Restricciones

- Tocar SOLO — T1 (dev): `scripts/validate_ux_page.py` (+ su REPORT local). T2
  (orquestador): `tests/test_validate_ux_page.py` (nuevo, congelado),
  `knowledge/contracts/ux-page-gate.md` (nuevo, sellado), `examples/ux-page/demo.html`
  (nuevo), `knowledge/data_models/ux_page_contract.md` (nuevo), `knowledge/index.md`,
  `scripts/init_project.py` (SOLO MANIFEST), `.github/workflows/validate.yml` (SOLO
  agregar paso), `knowledge/validacion.md`, `README.md` (EN/ES), `CHANGELOG.md`, el spec
  y el reporte.
- El landing page real del scratchpad (`kdd-landing.html`) NO se toca ni se commitea
  como parte de este contrato — esa es una decisión separada, pendiente, del usuario.
- Los specs `CONTRACT-01..29` y sus reportes son históricos: read-only.
- Python stdlib puro; sin red; sin subprocess; sin navegador; mensajes ASCII;
  determinista.
- NO commitear hasta verificar. Si algo no se puede sin romper otro criterio, PARAR y
  reportar.
- ABORTAR SI: la fórmula WCAG no pudiera implementarse determinísticamente a partir de
  hex puro (no debería pasar, es matemática pública, pero si hex con notación no
  estándar apareciera, es hallazgo, no parche); o separar mecánico/juicio resultara
  imposible sin que el gate empezara a opinar sobre estética (eso rompe la doctrina,
  PARAR y documentar en vez de forzarlo).

## Checklist antes de delegar

- [x] RECON corrido (2026-07-08): repo sin HTML propio hoy; el landing page del
  scratchpad usa un objeto JS literal para i18n, NO la convención JSON que este contrato
  exige — declarado honestamente, no se finge compatibilidad retroactiva.
- [x] Evidencia del gate: práctica manual repetida de ESTA sesión (i18n cruzado a mano,
  contraste verificado por inspección, sticky-range verificado en navegador real) —
  exactamente la clase de señal que la doctrina exige antes de construir un gate.
- [x] Todo criterio tiene comando + resultado esperado.
- [x] Red-team hecho: frontera mecánico/juicio explícita y con precedente (C23); lo que
  exige navegador real queda declarado FUERA, no fingido con una aproximación estática
  débil; el landing page real queda deliberadamente fuera del perímetro de este
  contrato.
- [x] Diseño calibrado contra un tercero real de producción: `google-labs-code/design.md`
  (25k stars) — su fórmula de contraste WCAG coincide con la nuestra (validación
  independiente); su severidad (`contrast-ratio` = warning, solo referencias rotas =
  error) motivó pasar `CONTRAST_LOW`/`MOTION_UNGUARDED` de ERROR implícito a WARNING
  explícito; su chequeo sobre pares estructurados (no CSS libre) motivó el bloque JSON
  `#ux-contrast-pairs` en vez de grepear `--text`/`--bg`.
- [x] Perímetro declarado; una tarea de código (T1); ejemplo + cableado del
  orquestador (T2).
- [x] Condiciones de aborto explícitas.
