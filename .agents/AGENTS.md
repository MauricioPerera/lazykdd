# Reglas para Agentes de IA

Si eres un agente de IA interactuando con este repositorio, debes acatar las siguientes reglas:

1. **Metodología KDD Obligatoria**: Este repositorio utiliza Knowledge-Driven Development. Antes de escribir código, debes leer los contratos en `knowledge/contracts/`.
2. **Carga la Skill Local**: Tienes disponible la skill `kdd-okf-ccdd-hybrid` en el directorio `.agents/skills/`. Debes adoptarla en tu contexto para entender cómo generar y validar los contratos híbridos OKF-CCDD.
3. **No dupliques contexto**: Utiliza enlaces de markdown relativos a `knowledge/` cuando necesites explicar el porqué de una implementación.
4. **Validación Determinista**: Ningún contrato o implementación se considera terminada hasta que pases una herramienta de validación (como `ccdd-gate`) localmente y te asegures de que los umbrales de complejidad se cumplen.
