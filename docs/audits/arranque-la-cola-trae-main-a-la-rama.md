# Nota de arranque — la cola deja de ser una condición y pasa a ser un mecanismo

- Fecha: 2026-09-14
- Rama: `mejora/la-cola-trae-main-a-la-rama`
- ADR previsto: ADR-200
- Incidencia: #608
- Decisión que la autoriza: el propietario, el 14-09-2026, eligiendo la
  **opción A** de las tres que se le pusieron delante en la incidencia #608.

Publicada ANTES del primer commit de código, según ADR-001.

## 1. ¿Dónde vive el fallo y dónde va el arreglo?

ADR-191 construyó `scripts/automation/sirius_cola.py` —la condición: una rama
entra a revisión solo si la punta de `main` es ancestro de su head— y dejó
escrito, **a propósito**, que no la cableaba: cablear la condición sin que nadie
ponga al día la rama que espera crearía un atasco nuevo, y peor que el de hoy.

Así que el fallo vive en dos sitios a la vez, y por eso el arreglo son dos
mitades que **tienen que entrar juntas**:

- **A1 — la condición no tiene llamante.** Está en
  `.github/workflows/advance-sirius-after-quality.yml`, rama `success)`: hoy
  repone `sirius:review-requested` sin mirar si `main` está dentro.
- **A2 — nadie pone al día la rama.** Hoy lo hace una persona. Si entrara solo
  A1, toda rama que se quedara atrás esperaría para siempre.

¿Puede el sitio del arreglo OBSERVAR el fallo que arregla? Sí, y es lo que lo
hace barato: ese paso ya lee `repos/{repo}/compare/{base}...{sha}` unas líneas
más arriba, para decidir si una aprobación sigue cubriendo el head (ADR-187).
Es el mismo dato que `sirius_cola.py` necesita.

## 2. ¿Qué NO va a garantizar esto?

- **No resuelve un conflicto real.** Si `main` y la rama tocaron lo mismo, traer
  `main` no puede decidir por nadie: se aborta la fusión y se dice en la
  incidencia. Eso sigue siendo de una persona.
- **No abre ninguna clase de permiso nueva**, y esto conviene decirlo porque a
  la incidencia #608 se le puso delante como si la abriera. El push va con
  `SIRIUS_BOT_TOKEN`, que es la misma credencial con la que
  `repair-sirius-work.yml` ya empuja commits a la rama de una PR
  (`token:` en su checkout). No hace falta subir `contents:` a `write`: el
  bloque `permissions:` gobierna el `GITHUB_TOKEN`, no el PAT.
- **No puede ir con `GITHUB_TOKEN`.** Un push hecho con él no dispara workflows,
  así que Quality no volvería a correr y la rama quedaría esperando otra vez: el
  mismo atasco con otra cara. Es la razón por la que las etiquetas ya van con el
  PAT.
- **No garantiza que una rama entre a la primera.** Si `main` se mueve mientras
  la rama se pone al día, le tocará otra vuelta. Eso es la cola funcionando, no
  un fallo.
- **No serializa el motor.** Se pueden seguir mandando varios trabajos: lo que
  se ordena es la ENTRADA a revisión, no el trabajo.
- **No prueba el `git merge` de verdad en este árbol.** Ver el criterio de
  parada.

## 3. Criterio de parada — decidido ahora, antes de ver ningún resultado

Terminado cuando:

1. Con la rama al día, la revisión se repone exactamente como hoy.
2. Sin la punta de `main` dentro, **no** se repone la revisión, se deja escrito
   en la incidencia que espera y por qué (el módulo ya devuelve el motivo), y se
   pone en marcha la puesta al día.
3. Un conflicto al traer `main` aborta la fusión, no deja la rama a medias, y se
   dice en la incidencia.
4. Una prueba fija que el workflow **llama** a `sirius_cola.py` —la mitad que
   faltó las ocho veces que este repositorio construyó una pieza sin llamante—,
   y se ha visto fallar.
5. La cadena entera en verde.

**Límite que se declara por delante, no después:** `git merge` está denegado en
esta sesión (`.claude/settings.json`), así que **la fusión real no se ejecuta
aquí**. Lo que se puede probar en este árbol es la decisión (ya cubierta por
`tests/automation/test_cola.py`) y el cableado del YAML. Que el paso funcione de
verdad solo lo demuestra ejecutarlo, y eso es lo que dice
`tests/automation/test_expresiones_de_workflow.py` de sí misma: hay una clase de
fallo que solo caza lanzar el workflow. **Primera puesta al día real: se vigila
a mano.**

**Me detengo, sin terminar, si:**

- hiciera falta ampliar `permissions:` o el alcance del PAT —ADR-002 decidió en
  contra y esta incidencia no lo reabre—;
- o si la puesta al día tuviera que reescribir historia (`--force`, rebase,
  amend) sobre una rama que no es mía.

## 4. ¿Qué haría el fallo IMPOSIBLE en vez de improbable?

El fallo de fondo no es «esta pieza no tiene llamante»: es que **una pieza puede
nacer sin llamante y nadie se entera**. `tests/automation/test_piezas_con_llamante.py`
ya cierra esa clase, pero solo para los módulos de `src/sirius_engine`: deriva su
inventario de ese árbol con `ast`. `scripts/automation/` queda fuera, y ahí es
donde vivía esta pieza.

Extender esa guarda a `scripts/automation/` sería el arreglo de clase. **No lo
hago en este trabajo, y la razón es una medida, no pereza:** ADR-190 midió hace
unas horas exactamente esa tentación —ampliar una guarda a un árbol vecino— y
encontró 0 defectos reales y 23 falsos positivos. Ampliar una guarda sin medir
antes su precisión en el árbol nuevo es el error que ADR-190 acaba de documentar.
Queda anotado como candidato con su medición pendiente, no como olvido.
