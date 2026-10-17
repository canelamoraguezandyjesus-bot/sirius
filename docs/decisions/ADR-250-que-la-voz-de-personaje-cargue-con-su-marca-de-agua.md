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
`setuptools`. Lo que quede por decidir al escribir el código se anota aquí con su porqué.

## Comprobación que la sostiene

Se escribe al acabar.

## Consecuencias

Se escriben al acabar.

## Alternativas descartadas y por qué

- **`constraint-dependencies`** (opción 2): limita a todo el proyecto por algo que solo
  pide un extra, y no dice de dónde viene la necesidad.
- **Una marca de agua de mentira** (opción 3): quitaría la marca de que el audio es
  generado. No.

## La lección

- ninguna: esta es la nota de arranque; si deja una lección, se escribe al acabar.

## Revisión externa

Va en la misma PR que ADR-247, y su alcance se suma al de allí: que con el extra
`personaje` cargue la marca de agua de Perth, sin quitarla nunca.
