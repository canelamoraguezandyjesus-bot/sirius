# ADR-250 — Que la voz de personaje cargue con su marca de agua

- Estado: APROBADO
- Fecha: 2026-10-17
- Aprobación: la fusión de la PR que lo introduce, con una ronda limpia de Codex sobre el
  head de contenido y Quality en verde (ADR-205). Es un defecto de la pieza F (ADR-246).

Este ADR es además la **nota de arranque** de este arreglo, en la misma rama que ADR-247
(`claude/la-cuenta-de-las-50-marcas`): las cuatro preguntas y el criterio de parada están
escritos antes del primer cambio de código y antes de cualquier revisión.

## Nota de arranque

1. **Dónde vive el fallo y dónde va el arreglo.** En su ordenador,
   `uv run --extra voz --extra personaje sirius-instala-la-voz` instaló 54 paquetes y bajó
   la voz, y al comprobarla dijo «[FALLA] La voz de personaje (Chatterbox) no carga: la voz
   de personaje no carga ('NoneType' object is not callable)». La causa, comprobada en un
   entorno con `chatterbox-tts` 0.1.7 y `resemble-perth` 1.0.1: Chatterbox crea la marca
   de agua de Perth al cargar (`perth.PerthImplicitWatermarker()`); Perth la deja en `None`
   si al importarla falla algo; y lo que falla es `from pkg_resources import
   resource_filename`, porque `uv.lock` fija `setuptools` 84.0.0, que ya no trae
   `pkg_resources`. Lo traen la 80.9.0 y la 81.0.0; la 82.0.0 y la 83.0.0, no. El arreglo
   va en las dependencias: con el extra `personaje`, `setuptools` por debajo de la 82, y
   `uv.lock` rehecho. La marca de agua no se quita: dice que el audio es generado, y se
   queda.

   **¿Puede el sitio del arreglo observar el fallo?** El lock, sí: dice qué `setuptools`
   se instala. Que Perth cargue de verdad, solo importándolo con ese `setuptools`, que es
   lo que ninguna prueba hacía: todas usaban un Chatterbox de mentira.
2. **Qué NO garantiza.**
   - Que Chatterbox hable en su ordenador: eso lo dice la orden de instalar al comprobarla,
     y él en E-R03-06. Aquí no hay sus pesos ni su gráfica.
   - Que una versión nueva de Perth deje de necesitar `pkg_resources`: la guarda lo pide
     mientras el lock lleve una que lo importa.
3. **Criterio de parada**, fijado antes de escribir código:
   - **Terminado** cuando `uv.lock` deja `setuptools` por debajo de la 82 con el extra
     `personaje`, y se ha mirado qué más se mueve; una guarda falla si el lock vuelve a
     dejar un `setuptools` sin `pkg_resources` con un Perth que lo importa, y se ha visto
     fallar con el lock de hoy; si se puede, Perth importado de verdad con el lock, con su
     marca de agua cargada; ADR-246 corregido en lo que daba por hecho; la cadena entera en
     verde; y la revisión propia sin nada.
   - **Nunca** una marca de agua de mentira ni nada que la quite.
4. **Qué lo haría imposible.** Que el lock no pueda dejar un `setuptools` sin
   `pkg_resources` mientras lleve un Perth que lo importa: la guarda lo mira en cada
   batería.

## Contexto y problema

La pieza F (ADR-246) puso la voz de personaje con Chatterbox en un extra aparte, y sus
pruebas la cargan con un módulo de mentira, porque Quality no instala ese extra. Nadie había
importado la biblioteca de verdad.

## Criterio de parada (escrito ANTES de decidir)

El de la nota de arranque, punto 3.

## Opciones consideradas

1. **`setuptools<82` en el extra `personaje`.**
2. **`setuptools<82` en `constraint-dependencies`** de uv, para todo el proyecto.
3. **Una marca de agua de mentira** (`DummyWatermarker`).

## Decisión

La opción 1: `setuptools<82` en el extra `personaje`.

Es una dependencia de verdad de ese extra: Perth importa `pkg_resources`, y quien lo trae es
`setuptools`. Al escribir el código se decidió además:

- **`uv.lock` rehecho**: solo se mueve `setuptools`, de 84.0.0 a 81.0.0. Ningún otro
  paquete cambia. Entró en el lock con la pieza F, porque lo pide `torch`, que solo está en
  ese extra: sin el extra no se instala.
- **La guarda** (`tests/automation/test_marca_de_agua.py`) mira el lock, porque Quality no
  instala el extra: mientras lleve un Perth del que no se sepa que ya no importa
  `pkg_resources`, todo `setuptools` del lock tiene que ser anterior a la 82. Falla
  cerrada: un Perth nuevo solo sale de ella si alguien lee su código y lo apunta en su
  lista.
- **La marca de agua no se toca.**

## Comprobación que la sostiene

- **La guarda, vista fallar con el lock de `main`**: «el lock lleva resemble-perth
  ['1.0.1'], que importa pkg_resources, y setuptools ['84.0.0'], que ya no lo trae». Con el
  arreglo pasa.
- **`uv lock`**: 205 paquetes en 3,6 s; solo cambia `setuptools`.
- **Las pruebas que leen los extras, el lock o `pyproject.toml`**, 18 ficheros: 1 342 en
  verde.
- **ruff** limpio; **mypy** sin errores en 735 ficheros.
- **La batería entera**, sobre `401ea5a1`, el árbol final de la PR: 8 847 en verde,
  14 omitidas y 2 `xfail`, ningún fallo, en 23 min 41 s.
- **Perth de verdad**, en un entorno aparte con los 157 paquetes que el lock instala con el
  extra `personaje`, `torch` 2.14.1 incluido, sin la gráfica ni los pesos de Chatterbox:
  - con `setuptools` 81.0.0, `import chatterbox.mtl_tts, perth` deja
    `perth.PerthImplicitWatermarker` como clase, se crea («loaded PerthNet (Implicit) at
    step 250,000») y marca dos segundos de audio sin fallar;
  - con `setuptools` 84.0.0 en el mismo entorno, es `None`, y crearla da «'NoneType' object
    is not callable», el error de su ordenador.

  Que la marca se detecte no se comprobó: con un tono de prueba, su detector da 1,0 con
  ella y sin ella.

## Consecuencias

- **Con el extra `personaje` se instala `setuptools` 81.0.0** en vez de 84.0.0. Sin el extra,
  como en Quality, no se instala.
- **En su ordenador hay que volver a pasar la orden de instalar con el extra**, después de
  traer la rama: es la que comprueba que la voz carga.
- **Si un Perth nuevo deja de importar `pkg_resources`**, la guarda lo seguirá pidiendo
  hasta que se lea su código y se apunte.

## Alternativas descartadas y por qué

- **`constraint-dependencies`** (opción 2): limita a todo el proyecto por algo que solo
  pide un extra, y no dice de dónde viene la necesidad.
- **Una marca de agua de mentira** (opción 3): quitaría la marca de que el audio es
  generado. No.

## Revisión propia

Antes de empujar se releyó el diff entero contra el código y la nota. En el código no
encontró nada; en este ADR, una frase que no decía bien de dónde venía `setuptools`,
reescrita.

## La lección

- familia: `doble-mas-permisivo-que-la-herramienta-que-dobla`
- sin esto se repetiría: probar con dobles una biblioteca que nadie cargó.
  Ninguna prueba de la pieza F cargó nunca Chatterbox de verdad, solo uno de mentira, y
  con el `setuptools` del lock su marca de agua no cargaba (H-250). La guarda vigila este
  caso, el del lock; que la voz cargue lo dice la orden de instalar en su ordenador.
- lo hace cumplir: `tests/automation/test_marca_de_agua.py`

## Revisión externa

Va en la misma PR que ADR-247, y su alcance se suma al de allí: que con el extra
`personaje` cargue la marca de agua de Perth, sin quitarla nunca.
