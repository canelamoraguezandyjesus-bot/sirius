# ADR-198 — Partir un objetivo grande lo hace la sesión interactiva; el descomponedor automático queda descartado

- Estado: APROBADO
- Fecha: 2026-09-14
- Aprobación: el propietario. **La decisión es suya y ya la tomó** el 14-09-2026;
  este ADR la escribe y cierra la incidencia #341, que llevaba desde el
  25-08-2026 esperando exactamente esta respuesta.

## La pregunta que estaba abierta

`sirius-despachar` convierte **una frase en un encargo**. Si se le pide algo del
tamaño de una versión entera, produce un encargo de alcance imposible. La
incidencia #341 puso tres salidas sobre la mesa y se negó a elegir por su cuenta,
con esta frase: «hasta que se conteste, **este bloque no se despacha**: elegir
entre las tres no es trabajo de implementación».

| | Opción | Qué es |
|---|---|---|
| A | Incidencias padre e hijas | GitHub ya lo soporta; da **dónde colgarlo**, no **quién lo piensa** |
| B | La clase `MIXTA`, hoy inalcanzable, decide el reparto | una máquina descompone la orden |
| C | La sesión interactiva parte y despacha | lo que ya se hace |

## La decisión

**C: el reparto lo sigue haciendo la sesión interactiva.**

**B queda DESCARTADA, no aplazada.** No se construye. Si algún día se quiere, no
empieza por una tarea de implementación: empieza por una decisión explícita sobre
la premisa de ADR-082.

**A queda disponible sin construir nada**, para el día que haya varios objetivos
vivos a la vez.

### Por qué «descartada» y no «aplazada», que es lo que importa de este ADR

Un «aplazado» vuelve a aparecer en cada repaso y obliga a volver a pensarlo
entero. Un «descartado, con la razón escrita» se lee una vez. La incidencia #341
llevaba **veinte días** abierta reclamando una respuesta que ya existía en la
cabeza del propietario; ese es exactamente el coste que este ADR quita.

### Por qué B es más cara de lo que parece

Decidir un reparto **exige un modelo**, y el motor no ejecuta ninguno. Eso no es
una carencia: es la premisa sobre la que descansa ADR-082, que la declara con
todas las letras —«**no ejecuta ningún modelo**: no importa ningún SDK»— y la
convierte en tabla de riesgos («ejecutar un modelo con permiso de escritura: **no
ocurre**»).

Y no es solo prosa: `tests/automation/test_el_motor_no_ejecuta_modelos.py` la
hace cumplir, con pruebas que revisan las importaciones de cada módulo del motor
y los binarios que lanza —«el motor solo lanza `gh` y `git`»—.

Activar `MIXTA` obliga a **releer esa decisión de seguridad**, no a añadir una
tabla. Es una decisión de otro orden, y el sitio donde tomarla no es una
incidencia de implementación.

## Lo que ha cambiado desde el 25-08 y sostiene la elección

La noche del 13 al 14-09-2026 la sesión interactiva repartió trabajo de verdad:
**cuatro encargos despachados uno a uno**, cada uno con su incidencia y su ciclo.
El único que falló no falló por el reparto —lo paró la quinta causa de la puerta
de sensibilidad (ADR-188), que hizo bien su trabajo— y se rescató reescribiendo
la orden, que es el gesto que la propia parada propone.

Y el guardián que la #341 ya había observado sigue ahí: un reparto mal hecho lo
para la máquina. Aquella tarde el implementador recibió un bloque de dos mitades,
vio que una no le correspondía y **se negó a entregar la otra sola** porque
habría sido «una vuelta completa falsa».

## Lo que este ADR NO hace

- **No prohíbe A.** El día que haya tres o cuatro objetivos vivos a la vez,
  colgarlos de una incidencia padre no necesita ningún ADR nuevo: no cambia nada
  del ciclo, que sigue viendo incidencias sueltas.
- **No mecaniza el reparto de ninguna forma.** Ni una heurística, ni una tabla, ni
  un umbral. El reparto sigue siendo un juicio.
- **No cierra la premisa de ADR-082 para siempre.** La deja donde estaba: si
  alguien quiere un motor que ejecute modelos, esa conversación es suya y empieza
  por ahí.

## Consecuencias

- La #341 se cierra citando este ADR. Deja de ser una pregunta abierta.
- La clase `MIXTA` sigue en el enum y sigue siendo inalcanzable por construcción
  (ADR-079). No se retira: **aquí no se borra nada** (ADR-195), y su existencia
  es parte del registro de que se consideró.

## La lección

- familia: `pregunta-al-propietario-que-nadie-vuelve-a-poner-delante`
- sin esto se repetiría: una incidencia formula una pregunta que **solo** el
  propietario puede contestar, se declara a sí misma bloqueada hasta que se
  conteste —«hasta que se conteste, este bloque no se despacha»— y luego nadie
  se la vuelve a poner delante; la #341 estuvo así **veinte días**, y la
  respuesta ya existía. Una incidencia abierta no es un recordatorio: nadie la
  lee si no la lee alguien.
- lo hace cumplir: ninguna prueba: nada en este repositorio distingue una
  incidencia que espera trabajo de una que espera una respuesta del propietario,
  así que ninguna guarda puede sacarla a flote; lo único que hoy mira una
  incidencia parada es `scripts/automation/sirius_reconcile.sh`, y solo las que
  llevan una etiqueta `sirius:*` del ciclo, que la #341 no tiene.
