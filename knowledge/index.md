# Knowledge Bundle (OKF)

Bienvenido a la base de conocimiento del proyecto. El formato de los nodos está especificado en [OKF-SPEC](./OKF-SPEC.md).

## Referencia
- [Especificación OKF](./OKF-SPEC.md) — spec normativa de nodos OKF.
- [Metodología de ejecución por contratos](./metodologia-ejecucion.md) — proceso operativo de nivel proyecto (specs/, docs/reports/, delegación y verificación).
- [Validación de contratos](./validacion.md) — nodo canónico: niveles 1 y 2, gate multi-lenguaje, export, precedencia del budget y ciclo de vida.
- [Casos reales de la metodología](./casos-reales.md) — incidentes verificados que motivaron las reglas; evidencia separada del proceso normativo.
- [Upgrade de la plantilla](./plantilla-upgrade.md) — qué es infraestructura sobreescribible desde upstream vs. propiedad del proyecto; procedimiento manual de upgrade.
- [Rule contract](./rule-contract-spec.md) — vertiente que valida reglas de negocio como datos declarativos (no solo código); familias, golden set y frontera dato/lógica.

## Estructura
- [Contratos de Desarrollo](./contracts/)
- [Modelos de Datos](./data_models/)
  - [Tabla users](./data_models/users_table.md)
  - [Limites de pago por pais](./data_models/payment_limits.md)
  - [Reglas de control de fronteras](./data_models/border_rules.md)
  - [Politica de workflows](./data_models/workflow_policy.md)
  - [Politica de ruteo de mensajes](./data_models/message_routing.md)
  - [Estilo editorial de articulos](./data_models/editorial_style.md)
  - [Registro de servidores MCP](./data_models/mcp_registry.md)
  - [Cableado de agentes](./data_models/agent_wiring.md)
  - [Convención UX/accesibilidad](./data_models/ux_page_contract.md)
  - [Convención de mensaje de commit](./data_models/commit_message_contract.md)
- [Arquitectura](./architecture/)
  - [Arquitectura general](./architecture/overview.md)