# Skills versionadas

Copias versionadas de las skills operativas que implementan la metodología KDD.

- `pm-glm-ccdd/SKILL.md` — Claude como PM/orquestador con devs GLM efímeros y gate CCDD.

## Relación con la copia operativa

La copia **operativa** (la que Claude carga en cada sesión) vive en
`~/.claude/skills/<skill>/SKILL.md`, fuera de git. Este directorio existe para
darle historial y respaldo, no para editarla acá.

Regla de sincronía (la misma doctrina que la skill declara): ante una mejora de
proceso, se actualiza PRIMERO la metodología en `knowledge/`, DESPUÉS se refleja
en la copia operativa local, y por último se copia acá **byte-idéntica**
(`cp` + `diff` vacío). Si esta copia y la local divergen, la local manda y esta
se re-copia.
