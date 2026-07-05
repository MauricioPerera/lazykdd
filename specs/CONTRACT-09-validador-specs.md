# Contrato 09 — Validador de contratos de ejecución (checklist ejecutable)

Prerrequisitos: contratos 01-08 completados. El checklist pre-delegación de
`specs/TEMPLATE-CONTRACT.md` es hoy disciplina del redactor; este contrato lo convierte
en check determinista para que lo exija el validador, no la memoria del PM.

> Capa: este es un **contrato de ejecución** (nivel proyecto). Las tareas que impliquen código
> delegado a un agente efímero llevan además su **task contract** CCDD en
> `knowledge/contracts/<task>.md` (validado por `scripts/validate_contracts.py`).

## VALIDATE-SPECS (T1) — validador determinista de specs/CONTRACT-*.md

Hoy nada verifica que un contrato de ejecución nuevo tenga criterios por máquina,
perímetro y condiciones de aborto: el checklist es manual.

FIX/OBJETIVO: existe `scripts/validate_specs.py` (stdlib, sin red, sin subprocess en el
script) que valida los `specs/CONTRACT-*.md` con estas reglas deterministas. Un contrato
está CERRADO si existe `docs/reports/CONTRACT-NN-REPORT.md` con su mismo prefijo
`CONTRACT-NN`; si no, está ABIERTO. `TEMPLATE-*.md` se ignora. Invariantes: los contratos
01-08 (cerrados, históricos) pasan sin editarse; el formato de salida y códigos de salida
siguen el patrón de `scripts/validate_okf.py`.

Reglas para TODO contrato:
- Sección `## Criterios de aceptación` presente, con al menos una línea checkbox
  (`- [ ]` o `- [x]`) que contenga un comando entre backticks.
- Sección `## Restricciones` presente.

Reglas adicionales SOLO para contratos ABIERTOS:
- `Tocar SOLO` presente en Restricciones.
- Bullet `ABORTAR SI` presente y rellenado: su texto no contiene placeholders con los
  caracteres de ángulo del template.

## Criterios de aceptación

- [ ] `python scripts/validate_specs.py specs` exit 0 sobre el repo actual, con resumen
  de archivos revisados.
- [ ] `python -m unittest discover -s tests -p "test_*.py"` verde, incluyendo
  `tests/test_validate_specs.py` con los casos: repo real en verde; abierto completo en
  verde; abierto sin ABORTAR SI falla; abierto con placeholder en ABORTAR SI falla;
  abierto sin comando entre backticks en criterios falla; cerrado sin ABORTAR SI ni
  Tocar SOLO pasa; TEMPLATE ignorado.
- [ ] `.github/workflows/validate.yml` corre el validador nuevo como paso propio y el
  YAML parsea con `python -c "import yaml; yaml.safe_load(open('.github/workflows/validate.yml'))"`.
- [ ] `python scripts/validate_contracts.py knowledge/contracts` exit 0 (incluye el task
  contract nuevo de esta tarea) y `python scripts/validate_okf.py knowledge` exit 0.
- [ ] Final: suite completa 2× verde (dos corridas idénticas); CI verde.

## Restricciones

- Tocar SOLO: `scripts/validate_specs.py`, `tests/test_validate_specs.py`,
  `.github/workflows/validate.yml`, `README.md`, `knowledge/contracts/validate-specs.md`
  y, solo si el validador OKF lo exige, `knowledge/index.md`.
- Los contratos `specs/CONTRACT-01` a `CONTRACT-08` y sus reportes son históricos:
  read-only. El validador se adapta a ellos vía la regla cerrado/abierto, no al revés.
- Sin dependencias nuevas (stdlib); sin red ni subprocess en el script (en tests sí está
  permitido subprocess, como en `tests/test_validate_okf.py`).
- NO commitear (el PM commitea por tarea verificada). Si algo no se puede sin romper otro
  criterio, PARAR y reportar.
- ABORTAR SI: una regla del contrato resulta imposible de cumplir manteniendo verdes los
  contratos históricos; o el paso nuevo de CI no puede añadirse sin tocar pasos existentes.
  En ese caso PARAR, documentar el porqué con evidencia en el reporte y marcar BLOQUEADO.

## Checklist antes de delegar

- [x] RECON corrido: los 8 contratos legacy tienen criterios con backticks; 01 y 04 no
  tienen Tocar SOLO; ninguno tiene ABORTAR SI; los 8 tienen reporte (cerrados). CI real:
  4 pasos en `validate.yml`. Suite real: `python -m unittest discover -s tests -p "test_*.py"`.
- [x] Todo criterio de aceptación tiene comando + resultado esperado.
- [x] Red-team hecho: los casos de test están enumerados y congelados en este contrato
  (un validador que siempre devuelve 0 no los pasa); el PM verifica además con un
  contrato inválido propio tras la entrega.
- [x] Perímetro de archivos declarado; sin tareas concurrentes.
- [x] Condiciones de aborto explícitas.
