---
type: 'Concept'
title: 'Metodología de ejecución por contratos'
description: 'Proceso operativo de nivel proyecto: contratos de ejecución en specs/, delegación a agentes efímeros, verificación por artefacto y reportes en docs/reports/.'
tags: ['metodologia', 'ccdd', 'proceso', 'ejecucion']
---

# Metodología de ejecución por contratos

Capa de nivel **proyecto** que complementa los task contracts de
[Contratos de Desarrollo](./contracts/): agrupa tareas en **contratos de ejecución**
numerados, cada uno con criterios de aceptación verificables por máquina. Probada en
producción (28 contratos consecutivos en el proyecto origen).

## Capas

| Capa | Dónde | Alcance | Evidencia |
|---|---|---|---|
| Contrato de ejecución | `specs/CONTRACT-NN-<slug>.md` | un objetivo del proyecto (1-N tareas) | `docs/reports/CONTRACT-NN-REPORT.md` (en-repo) |
| Task contract (CCDD) | `knowledge/contracts/<task>.md` | una tarea de código delegada | `.agents/logs/<task>-REPORT.md` (local, gitignorado) |

Plantillas: `specs/TEMPLATE-CONTRACT.md` y `docs/reports/TEMPLATE-REPORT.md`.

## Proceso

1. **PLAN** — convertir el pedido en contrato de ejecución con tareas atómicas; mostrarlo
   antes de disparar trabajo pesado.
   **RECON NEEDED:** toda suposición del plan que no esté verificada (comando real de la
   suite, workflows del CI — incluidos los condicionales por diff que quizá nunca
   corrieron —, dependencias instaladas, lenguajes soportados por el gate) se lista con
   el check exacto que la resuelve, y esos checks se corren ANTES de redactar specs.
   Una suposición sin check es una re-delegación futura.
2. **SPEC por tarea** — autocontenida y por OBJETIVO (estado final + definición de hecho
   con comando y resultado esperado), no por pasos. El agente efímero no tiene memoria:
   todo el contexto va en la spec (o se ensambla con el ensamblador de contexto).
   **Red-team de la definición de hecho antes de delegar:** preguntar «¿cómo podría
   cumplirse este comando sin cumplir la intención?» y parchear la definición con lo que
   aparezca. Casos reales que este paso previene: búsqueda degradada a escaneo completo
   con tests verdes; conteo de parámetros que evade el budget del gate.
3. **DELEGAR** — un agente efímero por tarea. Tareas que compartan archivos → secuenciales.
4. **VERIFICAR por artefacto** — la palabra del agente no cuenta: solo salidas reales de
   comandos (validador, tests). El orquestador re-corre los comandos antes de integrar.
   Todo trade-off declarado por el agente se inspecciona puntualmente.
5. **COMMIT por tarea verificada** — baseline limpio para la siguiente tarea.
6. **CIERRE** — suite completa 2× (dos corridas idénticas ≈ sin flaky; un flaky detectado
   es una tarea futura, no se ignora), reporte del contrato en `docs/reports/`, estado en
   el README.

## Política de reintentos (tope de gasto)

Máx **2 re-delegaciones** por tarea, cada una con el error exacto como feedback. A la 3ª:
**subdividir** la tarea. Si la versión subdividida también falla: **bloqueado, escalar** al
humano con diagnóstico. Nunca bucle infinito.

## Reglas duras

- El veredicto es del **gate determinista** (validador + tests + CI), nunca del modelo.
- Un contrato de ejecución no se cierra con criterios sin salida de máquina.
- Los agentes nunca commitean ni tocan archivos fuera del perímetro declarado en su spec.
- Toda spec lleva **condiciones de aborto** explícitas (ver `specs/TEMPLATE-CONTRACT.md`):
  ante un criterio inalcanzable por razón legítima, el agente PARA y documenta con
  evidencia en vez de improvisar o forzar.
- El ensamblador de contexto (si está instalado: `scripts/assemble_context.py` +
  `ccdd/context.json`) provee contexto presupuestado y auditable para cada delegación.
