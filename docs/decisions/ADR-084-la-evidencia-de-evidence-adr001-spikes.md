# ADR-084 — La evidencia de `evidence/adr001-spikes`: qué se afirmó, con qué se comprobó y qué no se hizo

- Estado: PROPUESTO
- Fecha: 2026-08-21
- Aprobación: la fusión de la PR #117 por el propietario
- Rama: `evidence/adr001-spikes` · PR #117, **abierta y sin fusionar**

## Incumplimiento de ADR-001, dicho antes que nada

`ADR-001` pide la nota de arranque **antes del primer commit**. Esta llega después de
más de doscientos, y no se maquilla: se escribe al final, y el empujón de cierre fue
quien la reclamó.

Hay una causa y no es excusa: `ADR-001` y su skill **no existían en la copia que esta
rama leía**. La rama arrancó de un `main` anterior, y el instrumental de disciplina
apareció al fusionar `main`, el 21 de agosto, junto con `ADR-016`. Es el mismo defecto
que `ADR-016` registra —leer el estado desde una rama atrasada—, y esta rama lo cometió
también: se afirmó que Sirius 0.1 estaba sin aceptar leyendo `V8_EXECUTION.md` desde
aquí, cuando en `main` constaba **ACEPTADO y TERMINADO** desde el 10 de agosto. Queda
corregido en el mismo trabajo.

El número **084** se toma sobre el `main` de hoy, que llega al 083. Si `main` lo ocupa
antes de fusionar, este documento se renumera, como hizo `herramienta/skill-adr` al
pasar del 030 al 032.

## Contexto y problema

`ADR-002` se cerró en su acta v1.0 como **no conforme**: los cuatro candidatos
incumplían las mismas dos obligaciones, y una de ellas —`B04-M01`, recall crítico,
umbral 100 % por caso— valía **16 omisiones en seis casos**. La pregunta de esta rama
fue si esa cifra era una propiedad del banco o un defecto reparable.

## Criterio de parada (escrito ANTES de medir, y honrado)

Antes de la primera corrida del modelo local se publicó el listón:

> «si los aciertos exactos suben por encima de 26/47, funciona y lo metemos en Sirius.
> Si no suben, el diseño está mal, te lo digo, y cerramos esta vía.»

Se cumplió: 24 → 30. Y la regla se aplicó también en sentido contrario, tres veces:

- la **fusión híbrida `RRF`** salió inerte y se declaró inerte, refutando la
  justificación que yo mismo había escrito;
- la **señal semántica densa** no superó a la léxica en ningún punto de operación, ni
  con modelo de pago, y la vía se cerró;
- la **ampliación al guardar** se midió dos veces por debajo de la línea base y se
  apagó pese a estar ya construida.

## Lo que se afirma

1. Las omisiones críticas pasan de **11 a 1** sobre el banco de 47 casos, y de los
   **seis casos** que cerraban `ADR-002` quedan **cinco resueltos**.
2. El filtro **no puede** dejar la cobertura crítica peor que la búsqueda. No es una
   instrucción al modelo: es una regla en el código.
3. `ADR-002` **sigue sin poder cerrarse eligiendo una alternativa**, y el acta v2.0 lo
   dice: la primera puerta queda a un caso y la segunda —conformidad de etapa, 14 de 46—
   **intacta**, porque este trabajo arregla `N1-33` y rompe `N1-31`, saldo cero.

## Comprobación que lo sostiene

Comprobable en este árbol, hoy:

- **Siete mediciones** conservadas enteras y ninguna pisada (`resultado_modelo_local*.json`);
  el arnés se niega a sobrescribir un artefacto ya medido y lo comprueba **antes** de
  medir.
- **2064 pruebas** de `experiments/adr002/` y 1493 del proyecto, con Ruff y mypy en verde.
- La regla de las críticas se **predijo antes de escribirla** —30/47 exactos, 20/31
  completas, 53/81 trozos, 10 de más, 11 omisiones— y la máquina dio los cinco números.
- El recomputo del artefacto v0.6 reproduce el recorrido 11 → 5 → 1 sin volver a
  encender el modelo.

## Lo que NO se afirma, y por qué

- **La siembra al ensamblar contexto no es validable con este banco.** Se escribió
  después de ver qué casos fallaban, y los dos únicos casos del banco con ese propósito
  son justo esos dos: el banco la confirmaría por construcción. Se sostiene por diseño, y
  una prueba deja ese hecho asertado para que las cifras no se lean como validación.
- **La corrida v0.7 no sirve para juzgar la latencia.** Su cronómetro rodeaba solo el
  filtro, de modo que la llamada de ampliación —hecha dentro de la búsqueda— quedaba
  fuera de la cifra que decide si se respeta el presupuesto de 5 s. Corregido después,
  con una prueba que impide volver a comparar el presupuesto contra el filtro a solas.
- **No se tocó el banco.** Ni corpus, ni `resultado_esperado`, ni adjudicación. Y no se
  lee `criticidad.razon_segura`: hay un atajo que cerraría el último caso indexándola
  —contiene la palabra exacta de la consulta que falla— y está descartado a propósito,
  escrito en `SIRIUS_0.2_ADR_002_LA_ULTIMA_OMISION_v1.0.md`, con dos pruebas que
  verifican que su texto no llega a ningún índice.
- **Ninguna modificación productiva de Sirius 0.1.** Todo vive en `experiments/`.

## Defectos propios, encontrados y corregidos en esta rama

Se listan porque el recuento honesto es parte de la evidencia:

| defecto | cómo salió |
|---|---|
| Justificación del híbrido que la propia medición refutaba | midiendo |
| Regla de polaridad que mandaba tirar prohibiciones que el banco espera | leyendo el banco tras un empeoramiento |
| La misma exclusión repetida en la regla temporal | detalle por caso |
| Huella del modelo pedida a un extremo que no la trae | salió «desconocida» |
| Nombre de salida fijo que rompía toda corrida a partir de la segunda | al segundo intento del propietario |
| Cronómetro que dejaba fuera la mitad cara | una cifra que bajaba cuando debía subir |
| Cinco ficheros borrados por un `rm` de limpieza | el árbol lo dijo; restaurados |

Los siete se publicaron con su medida al lado, no en un resumen.

## Consecuencias

- Lo construido queda **medido y disponible**, no adoptado: adoptarlo son dos decisiones
  del propietario, y una de ellas exige que Ollama esté arrancado, que `AGENTS.md` obliga
  a consultar antes.
- La segunda puerta de `ADR-002` sigue roja y **merece su propio paquete**. No se
  reinterpreta aquí: hacerlo sabiendo que es lo único que falta sería mover la medida
  sobre el resultado.
