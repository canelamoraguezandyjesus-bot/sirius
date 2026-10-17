# ADR-249 — Que migrar la base no apague el diario de Sirius

- Estado: APROBADO
- Fecha: 2026-10-16
- Aprobación: la fusión de la PR que lo introduce, con una ronda limpia de Codex sobre el
  head de contenido y Quality en verde (ADR-205). Es un defecto: el diario ya tenía que
  apuntar todo esto.

Este ADR es además la **nota de arranque** de este arreglo, en la misma rama que ADR-247
(`claude/la-cuenta-de-las-50-marcas`): las cuatro preguntas y el criterio de parada están
escritos antes del primer cambio de código y antes de cualquier revisión.

## Nota de arranque

1. **Dónde vive el fallo y dónde va el arreglo.** El 16-10-2026, en su ordenador, el diario
   de Sirius, `application.log`, medía 8 321 bytes y lo último que tenía era «Sirius
   iniciando», sin «Sirius iniciado» y sin nada de la prueba a ciegas que acababa de hacer.
   La causa, reproducida aquí: `migrations/env.py:16` configura el registro con
   `fileConfig(config.config_file_name)`, y su `disable_existing_loggers`, que vale `True`
   si no se dice otra cosa, apaga el registrador `sirius` y cada `sirius.*` que ya existía.
   `_start_with_resolved_path`, en `src/sirius/main.py`, escribe «Sirius iniciando» y
   después migra con `initialize_persistence`: desde ahí, la ventana, `sirius-oye` y todo lo
   que se importó antes no apuntan nada. El arreglo va en el producto, en la configuración
   de Alembic: que migrar deje encendidos los registradores que ya había.

   **Las pruebas lo sabían y lo taparon.** El conductor de la 0.3 los vuelve a encender
   después de migrar (`_enciende_los_registradores_de_sirius`, en
   `tests/acceptance/conductor_robot_0_3.py:1435`), y varias pruebas del oído, de la voz y
   del puente de la ventana encienden el suyo antes de mirar el diario, también la del
   altavoz de la pieza F. Con el arreglo sobran, y se quitan.

   **¿Puede el sitio del arreglo observar el fallo?** Sí: es la configuración que los
   apaga. Y una prueba con la ventana de verdad, que migra al arrancar, puede mirar que el
   diario sigue apuntando después.
2. **Qué NO garantiza.**
   - Recuperar lo que no se apuntó: lo de antes del arreglo no está en su diario.
   - Que el diario apunte lo que no se le manda: solo deja de estar apagado.
   - Que `fileConfig` deje de tocar el registro de fuera de Sirius: sigue poniendo el suyo
     en la consola, como hasta ahora.
3. **Criterio de parada**, fijado antes de escribir código:
   - **Terminado** cuando una prueba con la ventana de verdad, que migra al arrancar, mira
     que el diario dice «Sirius iniciado» después de migrar y se ha visto fallar con el
     código de hoy; los parches de las pruebas que encendían los registradores se han
     quitado y la batería entera sigue en verde sin ellos; cae la mutación que vuelve a
     apagarlos; y la revisión propia no encuentra nada.
   - **Si quitar un parche rompe una prueba**, se busca por qué antes de volver a ponerlo:
     sería otro sitio que apaga el diario.
4. **Qué lo haría imposible.** Que ninguna migración, la llame quien la llame, pueda apagar
   un registrador que ya existía. Con la configuración de Alembic diciéndolo, ningún camino
   que migre lo hace: ni la ventana, ni `sirius-oye`, ni las órdenes de consola, ni la línea
   de órdenes de Alembic, ni las pruebas.

## Contexto y problema

El de la nota: el diario de Sirius dejaba de apuntar en cuanto se migraba la base, es
decir, en cada arranque.

## Criterio de parada (escrito ANTES de decidir)

El de la nota de arranque, punto 3.

## Opciones consideradas

1. **`disable_existing_loggers=False`** en el `fileConfig` de `migrations/env.py`.
2. **No configurar el registro de Alembic cuando migra Sirius**, solo desde su línea de
   órdenes, con un atributo de la configuración que pone `upgrade_to_head`.

## Decisión

La opción 1: `disable_existing_loggers=False` en el `fileConfig` de Alembic.

Es una línea, y vale para todo lo que migra, también para las pruebas y la línea de
órdenes, que llaman a Alembic sin pasar por `upgrade_to_head`. Al escribir el código se
decidió además:

- **Se quitan los doce parches de las pruebas** que encendían un registrador antes de
  mirar el diario: dos del puente de la ventana, ocho del oído, uno del bucle que lo atiende
  y uno del altavoz de la pieza F; y el del conductor de la 0.3, con la función que los
  encendía todos y el `reabre` que solo existía para llamarla.
- **El conductor de la 0.3 configura el diario antes de montar Sirius**, como
  `sirius.main`. Lo configuraba después, así que lo que Sirius apuntaba al montarse iba por
  el registrador de la prueba anterior, a su carpeta. No se veía porque migrar lo apagaba;
  con el diario encendido, el vigilante de escrituras lo vio en dos pruebas de la voz.

## Comprobación que la sostiene

- **El fallo, visto con la ventana de verdad antes de arreglarlo**:
  `test_after_migrating_at_startup_the_diary_keeps_writing`, en
  `tests/gui/test_app_bootstrap.py`, arranca la ventana con `_build_first_window` sobre una
  instalación de antes. Con el código de `main`, el diario decía solo «Sirius iniciando»,
  como el suyo. Con el arreglo dice también «Sirius iniciado».
- **Mutación**: con el `fileConfig` de antes y sin los parches, caen 10 pruebas: la de la
  ventana y nueve de las que llevaban parche.
- **Sin los parches**, la aceptación entera, el oído, su bucle, el altavoz, el puente de la
  ventana, el arranque y el diario: 346 en verde, 2 omitidas y 1 `xfail`.
- **ruff** limpio; **mypy** sin errores en 733 ficheros.
- **La batería entera**: se escribe la última, sobre el árbol final.

## Consecuencias

- **Su diario apunta desde que arranca la ventana o `sirius-oye`**, también después de
  migrar: lo que hace la prueba a ciegas, la charla y la voz.
- **Migrar sigue configurando el registro de fuera de Sirius**: `fileConfig` pone el suyo
  en la consola y cierra los manejadores que había. El del diario de Sirius se vuelve a
  abrir solo con la línea siguiente, que es lo que mira la prueba de la ventana.
- **Una prueba que lea el diario ya no tiene que encenderlo**; si alguna vuelve a
  necesitarlo, algo lo está apagando otra vez.

## Alternativas descartadas y por qué

- **No configurar el registro de Alembic cuando migra Sirius** (opción 2): solo vale para
  lo que migra por `upgrade_to_head`. Lo que llama a Alembic de otra forma, como las pruebas
  de las migraciones, seguiría apagando el diario de todo lo que corre después en el mismo
  proceso, y los parches de las pruebas seguirían haciendo falta.

## Revisión propia

Antes de empujar se releyó el diff entero contra el código y la nota. Encontró una cosa,
arreglada: el conductor de la 0.3 configuraba el diario después de montar Sirius, y al
quitar su parche dos pruebas de la voz vieron escrituras en la carpeta de la prueba
anterior. Se configura antes, como en `sirius.main`.

## La lección

- familia: `prueba-que-tapa-un-defecto-del-producto`
- sin esto se repetiría: arreglar en la prueba lo que falla en el producto. El conductor de
  la 0.3 y doce pruebas volvían a encender los registradores que la migración apagaba, y
  todas pasaban mientras el diario de su ordenador dejaba de apuntar al arrancar (H-249).
- lo hace cumplir: `tests/gui/test_app_bootstrap.py`

## Revisión externa

Va en la misma PR que ADR-247, y su alcance se suma al de allí: que migrar no apague el
diario, la llame quien la llame, y que ninguna prueba necesite encenderlo a mano.
