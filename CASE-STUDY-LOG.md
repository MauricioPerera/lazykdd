# Registro del caso de estudio KDD

Este archivo NO es parte de la metodología KDD (no lo lee ningún gate, no
sigue el formato OKF). Es un diario aparte: el registro externo de que este
proyecto se construyó con KDD de punta a punta, para servir de evidencia
real cuando se documente como caso de estudio (gap identificado: KDD nunca
se probó fuera de sí mismo).

Cada entrada: fecha, qué se hizo, por qué, evidencia (comando + resultado
si aplica). Sin relleno — si no hay nada verificable que registrar, no se
agrega entrada.

---

## 2026-07-14 — Setup

- Clonado desde `MauricioPerera/KDD` en el tag `v1.6.0` (commit `8bb82f4`).
- Repo desenganchado del remoto de KDD (`git remote remove origin`); este
  proyecto no trackea upstream por git — los upgrades futuros de plantilla
  siguen el procedimiento manual de `knowledge/plantilla-upgrade.md`
  (clonar el nuevo release aparte y diffear la infraestructura a mano).
- Plantilla dejada SIN instanciar (`init_project.py` no corrido todavía):
  los artefactos de ejemplo (`sample_task.md`, dominios de ejemplo, etc.)
  siguen presentes como referencia hasta que se defina el alcance real del
  proyecto — instanciar pide un `--name` que todavía no existe.
- Verificado sano antes de arrancar: `validate_contracts.py` 0 errores (29
  contratos), suite completa 573/573 verde.

## Próximo paso (pendiente, no ejecutado)

Cuando se defina de qué trata el proyecto:
1. `python scripts/init_project.py --apply --name "<Nombre Real>"`.
2. Seguir `knowledge/quickstart.md` para el primer task contract propio.
3. Agregar una entrada acá por cada milestone real (primer contrato verde,
   primera delegación a un agente efímero, primer incidente, etc.) — la
   evidencia de que el método se siguió, no una narración post-hoc.
