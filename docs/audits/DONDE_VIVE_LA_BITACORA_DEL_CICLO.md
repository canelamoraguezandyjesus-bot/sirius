# Dónde vive la bitácora del ciclo, y por qué no está aquí todavía

- Fecha: 2026-09-20
- Decisión que lo fija: ADR-210.

## Qué es y dónde está

La **bitácora de fallos y mejoras del ciclo** es el registro vivo de todo lo que
falla en el ciclo del motor, lo que se corrige sobre la marcha y toda manera
mejor de hacer algo que aparece por el camino. La pidió el propietario el
03-09-2026: *«cada vez que algo falle, o encuentres una mejor manera de hacerlo,
apúntalo en algún lado; después lo mandamos a la mina y mejoramos el trabajo»*.

No está en `main`. Vive en la rama `claude/adr002-tol209-forensic-audit-i0ui8k`,
y solo ahí. En esa rama es `docs/audits/bitacora-de-fallos-y-mejoras-del-ciclo.md`:
**128 entradas, 459 KB**
y, con ella, siete documentos más que cita y que también viven solo en esa rama —la
edición de septiembre de la mina de aprendizaje, las decisiones pendientes de la
línea de memoria, y las mediciones del 20-09 con Ollama real—.

Para verla sin cambiar de rama:

```
git fetch origin claude/adr002-tol209-forensic-audit-i0ui8k
git show FETCH_HEAD:docs/audits/bitacora-de-fallos-y-mejoras-del-ciclo.md | less
```

## Por qué no se ha traído

Su sitio es `main` —un registro que nadie puede leer no es un registro— y traerla
se intentó el 20-09-2026. No se hizo, por dos razones medidas:

1. **No viene sola.** Cita siete documentos hermanos que tampoco están en `main`.
   Traerla suelta deja diez referencias rotas, y el comprobador documental las
   nombra una a una.
2. **Su rama está viva.** Su último commit era de hacía **ocho minutos** cuando
   se comprobó. Copiar a `main` el trabajo en vuelo de otra sesión es
   exactamente la colisión que ADR-206 existe para evitar, y la comprobación que
   ese ADR exige es la que paró esta.

La rama está empujada, así que nada se ha perdido: archivar una rama es dejarla
ahí (ADR-195). Lo que faltaba era que se pudiera encontrar, y para eso existe
esta nota.

## Qué tiene que pasar para que entre

Que la sesión que la escribe la traiga con su familia en una sola PR, cuando
cierre su línea de trabajo. Desde entonces su sitio es `main` y se actualiza
ahí.
