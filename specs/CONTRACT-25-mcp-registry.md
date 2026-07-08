# Contrato 25 — Registro MCP como dominio + familia `matches` (propiedades de texto)

Prerrequisitos: contratos 01-24 cerrados, HEAD `a1e684e`, suite 305 verde 2×, CI verde en
ambas patas. Séptimo dominio de la vertiente rule-contract, y la extensión evidencia-primero
que C23 dejó anunciada: "solo se agregarían familias de texto si otro dominio repite la
clase". RECON (2026-07-08, config global real del usuario): 5 servidores MCP registrados
(vps, n8n, ccdd-complexity, wp-abilities, pocketbase) — 3 de ellos con SECRETOS LITERALES
en `env` (contraseñas de VPS/PocketBase/WordPress). La política central de un registro MCP
commiteable ("los secretos van como referencias `${VAR}`, nunca literales") es una
propiedad de TEXTO (patrón sobre string): la MISMA clase de frontera que el dominio
editorial midió (C23). Segunda aparición ⇒ la doctrina habilita la familia declarativa.

> Capa: contrato de ejecución. T1 (código, dev efímero) va contra los oráculos congelados
> del motor y del gate (REFORZADOS y RE-SELLADOS por el PM ANTES de delegar). T2 (datos +
> nodo + manifest) es del orquestador. Los artefactos del dominio son EJEMPLO (MANIFEST);
> la familia `matches` es INFRA del motor. NUNCA se commitea la config real del usuario
> (contiene secretos): el ejemplo es sintético con la MISMA forma.

Qué se contrata y qué NO (honestidad de alcance):
- SÍ (nivel 1, datos): la forma del registro — transporte válido, stdio⇒command,
  streamable-http⇒url https, nombres kebab-case, y env sin secretos literales (todo valor
  debe matchear `^\$\{[A-Z_][A-Z0-9_]*\}$`).
- NO: el comportamiento del servidor VIVO (handshake, tools reales, latencia) — exige red,
  fuera del nivel 1 por doctrina. Queda declarado en `code_only` con razón.

Decisiones de diseño (fijadas acá):
- **Familia `matches`**: `{"field": F, "pattern": P}` — viola si el valor es string y
  `re.search(P, valor)` NO matchea (los autores anclan con `^...$` cuando quieren match
  total). Valor ausente/None se salta (es trabajo de `required`); valor no-string se salta
  (es trabajo de `type`) — coherente con cómo `bounds` saltea no-números. Disponible
  top-level Y dentro de `each.rules` (se agrega al subset v1). Mensaje ASCII
  "pattern mismatch". `validate_rules` la reconoce (`_VALID_KEYS` y el subset de `each`).
- **Registro como record plano** (forma auditoría, precedente routing-audit): el record es
  `{servers: [{name, transport, command?, url?}], env_entries: [{server, key, value}]}` —
  aplanar `env` evita colecciones anidadas (que `each` no soporta y NO se agregan sin
  evidencia).
- **Unicidad de nombres de servidor**: cerrada POR CONSTRUCCIÓN en el formato real
  (`mcpServers` es un objeto JSON keyed por nombre) — se documenta en el nodo, no es
  frontera abierta.
- Golden sellado con `--hash`; REPRO del gate re-corre el motor sobre cada caso.

## T1 — Familia `matches` en el motor (dev efímero)

OBJETIVO: extender `scripts/rule_engine.py` (top-level + dentro de `each`) y
`scripts/validate_rules.py` (familia conocida) contra los oráculos congelados
`tests/test_rule_engine.py` y `tests/test_validate_rules.py`, REFORZADOS y RE-SELLADOS por
el PM antes de delegar (TestMatches: match/no-match, anclaje, skip de None y de no-string,
formato del mensaje, `matches` dentro de `each` con prefijo de colección, orden
determinista intacto; gate: `matches` no es clave desconocida). Task contract:
`knowledge/contracts/validate-rules.md` + `knowledge/contracts/rules-gate.md` (re-sellados;
el perímetro del dev son los DOS scripts y nada más). `re` es stdlib: permitido.

## T2 — Dominio mcp-registry (autoría del orquestador)

`knowledge/data_models/mcp_registry.md` (formato del record, política, fronteras: servidor
vivo = code_only con razón; unicidad = cerrada por construcción);
`examples/rules/mcp-registry.rules.json` (required servers; each servers: required
name+transport, enums transport [stdio, streamable-http, sse], matches name kebab; each
servers where stdio: required command; each servers where streamable-http: required url +
matches url `^https://`; each env_entries: matches value `^\$\{[A-Z_][A-Z0-9_]*\}$`;
code_only documentado; golden sellado); `examples/rules/mcp-golden.json` (caso válido +
violaciones: transporte inválido, stdio sin command, url http, secreto literal en env,
name no-kebab); artefactos al MANIFEST de `init_project`; index/nodo enlazados; CHANGELOG.

## Criterios de aceptación

- [ ] `python -m unittest tests/test_rule_engine.py tests/test_validate_rules.py` verde
  SIN que el dev modifique los oráculos (sellos nuevos del PM en ambos contratos).
- [ ] `python scripts/validate_rules.py examples/rules` exit 0 con 5 rule-sets (el nuevo
  incluido) y REPRO verde sobre `mcp-golden.json`.
- [ ] Mutación PM (sobre copia): secreto literal en un env del golden → REPRO exit 1;
  clave `matchess` (typo) en un rule-set → FAMILIA exit 1.
- [ ] Los goldens previos (payment, border, workflow, routing) byte-INTACTOS (canarios).
- [ ] Los 6 gates exit 0; suite completa 2× verde; post-init neutral
  (`test_init_project` con los 3 artefactos nuevos en MANIFEST).
- [ ] Final: CI verde en ambas patas.

## Restricciones

- Tocar SOLO — T1 (dev): `scripts/rule_engine.py`, `scripts/validate_rules.py` (+ su
  REPORT local). T2 (orquestador): los 2 oráculos (SOLO reforzar, antes de delegar) + los
  2 contratos re-sellados, `knowledge/data_models/mcp_registry.md` (nuevo),
  `knowledge/index.md` (enlace), `examples/rules/mcp-registry.rules.json` +
  `examples/rules/mcp-golden.json` (nuevos), `scripts/init_project.py` (SOLO MANIFEST),
  `knowledge/rule-contract-spec.md` (fila de la familia), `CHANGELOG.md`, el spec y el
  reporte.
- Los goldens y rule-sets previos NO se tocan (canarios de regresión).
- Los specs `CONTRACT-01..24` y sus reportes son históricos: read-only.
- PROHIBIDO commitear la config MCP real del usuario o cualquier secreto; el ejemplo es
  sintético.
- Python stdlib puro; sin red; sin LLM; mensajes ASCII; determinista.
- NO commitear hasta verificar. Si algo no se puede sin romper otro criterio, PARAR y
  reportar.
- ABORTAR SI: `matches` no pudiera entrar en `each.rules` sin romper un test previo del
  motor (eso es un hallazgo del diseño de `each`, no un parche); o el REPRO del golden
  nuevo exigiera debilitar la semántica de una familia existente. PARAR, documentar y
  marcar BLOQUEADO.

## Checklist antes de delegar

- [x] RECON corrido (2026-07-08, config real): 5 servidores, 3 con secretos literales en
  env — el dominio y la regla central salen de datos reales; el ejemplo se comitea
  sanitizado con la misma forma.
- [x] Evidencia de la familia: segunda aparición de la clase "propiedad de texto"
  (editorial C23 → registro MCP C25), como exige la doctrina evidencia-primero.
- [x] Todo criterio tiene comando + resultado esperado.
- [x] Red-team hecho: skip de None/no-string definido (no duplica required/type); anclaje
  explícito en los patterns del ejemplo; env aplanado para no inventar `each` anidado;
  goldens previos como canarios; secretos jamás al repo.
- [x] Perímetro declarado; una tarea de código (T1); datos del orquestador (T2).
- [x] Condiciones de aborto explícitas.
