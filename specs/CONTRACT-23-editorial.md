# Contrato 23 — Contrato editorial: el estilo de un artículo como gate

Prerrequisitos: contratos 01-22 cerrados, release v1.2.0, HEAD `c41032f`, suite 260 verde
2×, CI verde en ambas patas. Quinto dominio de ejemplo: **reglas editoriales de un
artículo de newsletter** (registro, largo, estructura, prohibiciones léxicas) — reglas que
hoy viven en prosa (una skill que un LLM interpreta) y que en su mayoría son verificables
por máquina. El contrato las convierte en gate: un borrador se valida ANTES de publicar.

Decisiones de diseño (fijadas acá):
- **Este dominio es CÓDIGO, y decirlo es el hallazgo**: las reglas editoriales son
  propiedades de TEXTO (longitud de título, conteo de palabras, presencia de patrones) y
  las familias declarativas no tienen `length` ni `matches` — cuarta clase de frontera
  medida ("propiedades de texto"). NO se agregan familias especulativamente (doctrina:
  evidencia = repetición en otro dominio); el dominio entero va como task contract, forma
  C16. No hay rule-set decorativo con métricas pre-extraídas por código.
- **La tabla de estilo entra por argumento** (`style`): frases prohibidas, tope de título,
  rango de palabras, rango de H2, rango del SEO description, caracteres vetados — datos
  del llamador, función pura (patrón `limits`/`routing`).
- **Fronteras del dominio declaradas**: calidad del hook, tono no condescendiente y humor
  son JUICIO — territorio de eval Tier 2 (juez auditado) o revisión humana, jamás de este
  checker. "Párrafos de ≤4 líneas en pantalla" depende del render — se aproxima por
  palabras-por-párrafo como dato de estilo, con la aproximación documentada.
- Artefactos de EJEMPLO (al `MANIFEST`).

## T1 — `validate_article` (dev efímero)

OBJETIVO: `src/validate_article.py` con
`def validate_article(article: dict, style: dict) -> list:` que hace pasar el oráculo
congelado `tests/test_validate_article.py` (autorado y sellado por el orquestador).
Checks fijados por el oráculo: título obligatorio y dentro del tope; cuerpo dentro del
rango de palabras; cero caracteres vetados (em-dash); cero frases prohibidas
(case-insensitive); sin tablas markdown; sin H1 en el cuerpo; conteo de H2 dentro del
rango; sin URLs crudas (los links van con texto de anclaje markdown); SEO description
dentro de su rango; párrafos dentro del tope de palabras. Acumula todas las violaciones,
cada una nombra el campo (`title`/`body`/`seo_description`); pura; nunca lanza.

## T2 — Dominio como nodo (autoría del orquestador)

OBJETIVO: `knowledge/data_models/editorial_style.md` (Data Model indexado): el record, la
tabla de estilo, el mapeo regla-editorial → check, y las fronteras (juicio y render)
declaradas. Task contract `knowledge/contracts/validate-article.md` sellado. Los 4
artefactos al `MANIFEST`.

## Criterios de aceptación

- [ ] `python -m unittest tests/test_validate_article.py` verde SIN modificar el oráculo
  (sello vigente).
- [ ] Adversarial PM: un borrador con em-dash, "robusto" y una tabla markdown produce ≥3
  violaciones que nombran `body`; un borrador conforme produce `[]`.
- [ ] `python scripts/validate_contracts.py knowledge/contracts` exit 0 (contrato nuevo
  sellado), `python scripts/validate_okf.py knowledge` exit 0,
  `python scripts/validate_specs.py specs` exit 0,
  `python scripts/lint_ascii.py scripts` exit 0 y
  `python scripts/validate_rules.py examples/rules` exit 0 (4 dominios intactos).
- [ ] `python -m unittest discover -s tests -p "test_*.py"` suite completa 2× verde
  (incluye `test_init_project` con el MANIFEST ampliado).
- [ ] Final: CI verde en ambas patas.

## Restricciones

- Tocar SOLO — T1 (dev): `src/validate_article.py` (+ su REPORT en `.agents/logs/`).
  T2 (orquestador): `knowledge/contracts/validate-article.md` (nuevo, sellado),
  `tests/test_validate_article.py` (nuevo, congelado),
  `knowledge/data_models/editorial_style.md` (nuevo), `knowledge/index.md` (enlace),
  `scripts/init_project.py` (MANIFEST), `CHANGELOG.md`, el spec y el reporte.
- Motor, gate, rule-sets y goldens existentes NO se tocan. NO se agregan familias
  declarativas (la frontera se documenta, no se tapa).
- Los specs `CONTRACT-01..22` y sus reportes son históricos: read-only.
- Python stdlib puro (se permite `re`); sin red; sin LLM; mensajes ASCII; determinista.
- NO commitear hasta verificar. Si algo no se puede sin romper otro criterio, PARAR y
  reportar.
- ABORTAR SI: el oráculo congelado fuera internamente contradictorio, o algún check
  exigiera juicio no determinista (eso pertenece a las fronteras declaradas, no al
  checker). PARAR, documentar con evidencia y marcar BLOQUEADO.

## Checklist antes de delegar

- [x] RECON corrido (2026-07-08): las reglas editoriales de la skill de newsletter son
  en su mayoría deterministas (largo, léxico, estructura); las familias del motor no
  tienen length/matches (verificado en rule-contract-spec: las 8 familias operan sobre
  valores, no sobre propiedades de strings) — dominio de código, frontera nueva anotada.
- [x] Todo criterio tiene comando + resultado esperado.
- [x] Red-team hecho: la tabla de estilo por argumento evita hardcodear el estilo de UNA
  newsletter en el checker (reusable); "URL cruda" se define exacto en el oráculo (http
  fuera de sintaxis de link markdown) para no dejarle el criterio al implementador; los
  juicios (hook, tono) quedan fuera POR CONTRATO para que nadie los finja deterministas.
- [x] Perímetro declarado; una tarea de código (T1); cableado del orquestador (T2).
- [x] Condiciones de aborto explícitas.
