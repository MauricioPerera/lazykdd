# KDD Template (Knowledge-Driven Development)

Este es un repositorio plantilla para proyectos que implementan la metodología **Knowledge-Driven Development (KDD)**, la cual unifica:
- **OKF (Open Knowledge Format):** Un formato minimalista para estructurar el conocimiento, diseño y arquitectura como archivos markdown con frontmatter YAML.
- **CCDD (Contract-Driven Development):** Una metodología para gobernar el desarrollo con agentes de IA efímeros mediante contratos estrictos y umbrales deterministas (complejidad, tests congelados).

## Estructura del Repositorio

- `knowledge/`: Aquí vive tu base de conocimiento OKF. Todo archivo aquí es un nodo indexable.
- `knowledge/contracts/`: Donde se definen las tareas para los desarrolladores (humanos o IA) usando el formato híbrido OKF+CCDD.
- `src/` y `tests/`: Código de implementación y pruebas automatizadas.
- `.agents/`: Reglas locales para agentes de IA que clonen este repositorio.

## Cómo usar esta plantilla

1. Usa este repositorio como "Template" en GitHub o clónalo localmente.
2. Explora `knowledge/index.md` para ver cómo se estructuran los conceptos.
3. Al delegar trabajo a un agente (ej. Claude, Antigravity, etc.), el agente leerá `.agents/AGENTS.md` y entenderá inmediatamente que debe respetar los contratos CCDD de este repositorio.

## Integración de Herramientas
Para validar los contratos, se asume que cuentas con herramientas de parseo como `ccdd-gate` instaladas en tu entorno.
