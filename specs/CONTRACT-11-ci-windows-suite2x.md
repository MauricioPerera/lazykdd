# Contrato 11 — CI: matriz Windows y suite 2×

Prerrequisitos: contratos 01-09 cerrados (independiente de C10: perímetros disjuntos).
Dos gaps del CI respecto de la práctica real del repo: (a) corre solo en `ubuntu-latest`,
pero el desarrollo es en Windows y el único bug post-release del repo fue Windows-only
(cross-drive, C08) — su caso se testea en Linux solo vía `ntpath` con paths literales, y
el test del CLI real (`test_cli_cross_drive_exit1_io_not_contract_invalid`) se saltea
fuera de Windows; (b) la metodología exige suite 2× al cierre (dos corridas idénticas ≈
sin flaky) pero el CI la corre una sola vez — la regla anti-flaky es disciplina del PM,
no gate.

> Capa: este es un **contrato de ejecución** (nivel proyecto). La tarea no delega código
> de producción (solo CI), por lo que no lleva task contract CCDD propio.

## CI-WIN-2X (T1) — matriz de OS + segunda corrida de la suite

FIX/OBJETIVO: `.github/workflows/validate.yml` con `strategy.matrix.os:
[ubuntu-latest, windows-latest]` y `runs-on` parametrizado; los 5 pasos actuales quedan
idénticos en comando y orden (ya son cross-platform: Python stdlib, rutas relativas
POSIX), y se agrega un segundo paso de suite ("Run unit tests (2/2)") idéntico al
existente. Invariantes: ningún paso existente se elimina ni cambia de comando; el test
win-only del cross-drive pasa a ejecutarse en la pata Windows (en Linux se sigue
salteando limpio); Python 3.11 en ambas patas.

## Criterios de aceptación

- [ ] `python -c "import yaml; yaml.safe_load(open('.github/workflows/validate.yml'))"`
  sin excepción (el YAML parsea).
- [ ] `grep -n "windows-latest" .github/workflows/validate.yml` con hit, y
  `grep -c "unittest discover" .github/workflows/validate.yml` devuelve 2.
- [ ] En este host Windows: `python -m unittest discover -s tests -p "test_*.py"` verde
  2× (dos corridas idénticas).
- [ ] CI verde en AMBAS patas de la matriz sobre el push de cierre, verificado con
  `gh run view` del run: ambos jobs en success.

## Restricciones

- Tocar SOLO: `.github/workflows/validate.yml`.
- Sin dependencias nuevas; sin cambios en `scripts/`, `tests/` ni `knowledge/`.
- NO commitear (el PM commitea por tarea verificada). Si algo no se puede sin romper otro
  criterio, PARAR y reportar.
- ABORTAR SI: la pata Windows del CI falla por una causa cuya corrección exigiría tocar
  archivos fuera del perímetro (eso es un hallazgo que alimenta un contrato nuevo, no se
  parchea en silencio); o el runner windows-latest no ofrece Python 3.11. En ese caso
  PARAR, documentar la evidencia del run en el reporte y marcar BLOQUEADO.

## Checklist antes de delegar

- [x] RECON corrido (2026-07-07): suite 136 verde 2× en host Windows real; el YAML actual
  parsea con `yaml.safe_load`; el chequeo cross-drive del export se dispara ANTES de
  cualquier escritura (robusto a unidades inexistentes del runner, diseño ya fijado en
  `test_export_gate_contract.py`); los 5 pasos del CI usan solo Python + rutas relativas.
- [x] Todo criterio tiene comando + resultado esperado (el veredicto final es el run de
  CI, por máquina).
- [x] Red-team hecho: los greps de presencia no bastan solos — el criterio final exige
  ambos jobs en success, no solo que el YAML declare la matriz.
- [x] Perímetro de un solo archivo; disjunto de C10 (pueden correr en paralelo).
- [x] Condiciones de aborto explícitas.
