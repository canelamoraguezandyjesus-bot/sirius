# ADR-097 — Un tres no es un fallo sino un veredicto con motivo, y el plazo se reparte por pregunta

- Estado: PROPUESTO
- Fecha: 2026-08-27
- Aprobación: la fusión de la PR por el propietario
- Contexto: S2, incidencia #258. Primera pasada REAL del banco (ejecución 33079519839)
- Relacionadas: ADR-001, ADR-095 (la escalera de cuatro preguntas y el atestado),
  ADR-096 (una contradicción no es una divergencia)

## Contexto y problema

El banco se ejecutó de verdad por primera vez. El atestado pasó —los cuatro
modelos respondieron ese día— y la comparación corrió treinta minutos:

```
13:57:21  → nvidia: preparando subproceso propio
14:02:42    nvidia: fallo — el subproceso terminó con código 3.
            Final de su salida: … 📚 Getting relevant content based on query…
14:02:42  → google: preparando subproceso propio
14:27:42    google: agotado_el_tiempo — pasó de 1500 s y se cortó.
```

**NO CONCLUYENTE.** El guardián hizo lo correcto: no publicar un número que no
existe. Pero al ir a leer *por qué*, resultó que **no se podía**.

### El código 3 no era un fallo, y se trataba como tal

`medir_investigador.main` termina así:

```python
if not resultado.medicion_fiable:
    sys.stderr.write(f"MEDICION NO FIABLE: {resultado.motivo_no_fiable}\n")
    return 3
```

Devuelve `3` **si y solo si** la medición no es fiable, y lo hace **después** de
escribir el JSON entero con el motivo dentro. El padre tenía, en este orden:

```python
if proceso.returncode != 0 or not salida_json.is_file():
    base.detalle = f"…código {proceso.returncode}. Final de su salida:\n{cola}"
    return base                       # <-- sale aquí, siempre

…
if not resultado.get("medicion_fiable", True):
    # «El hijo ya sabe que lo suyo no vale y lo dice»
    base.detalle = str(resultado.get("motivo_no_fiable", …))
```

El segundo bloque **no se ejecutaba nunca**. Código muerto con un comentario
explicando por qué era importante, y con una prueba en verde vigilándolo —una
que leía el texto fuente, y que por eso mismo no podía notar la diferencia entre
«está escrito» y «se ejecuta»—.

Octavo caso de la enfermedad de esta casa, y una forma nueva:

| # | forma | cómo se encuentra |
|---|---|---|
| 1–6 | función sin llamante | `grep` del nombre |
| 7 | dato sin lector (ADR-096) | buscar quién consulta el campo |
| **8** | **rama inalcanzable** | **hay que leer la guarda que la precede** |

### El plazo era por configuración, y el banco creció

El banco pasó de cinco a siete preguntas cuando se añadieron las perecederas
(ADR-095). El plazo siguió siendo uno solo, por configuración, en el proceso
padre. Medido: NVIDIA hizo las siete en 5 min 21 s (~46 s cada una); Google no
terminó en 1500 s **y no dejó ni una respuesta legible**, porque el padre lo mató
con todo dentro.

Una sola pregunta colgada se llevaba por delante las otras seis ya contestadas.

## Decisión

**Un `3` con JSON escrito es un veredicto con motivo, no una avería.** Se
comprueba antes que la guarda genérica; se lee el JSON; se publica
`motivo_no_fiable`. Un `3` **sin** JSON sigue siendo un fallo —el hijo murió
antes de escribirlo— y cualquier otro código también.

**Sigue sin contar como medida.** Lo único que cambia es que ahora se puede
saber por qué. El porcentaje no se copia: un 100 % sobre cero fuentes publicado
como resultado es exactamente la raíz que la refutación del 26-08 tumbó, y hay
una prueba que lo fija con un hijo cuyo JSON trae `porcentaje: 100.0`.

**El plazo se reparte por pregunta**, derivado y no escrito a mano:

```
por_pregunta = max(60, int(presupuesto × 0,9 ÷ nº de preguntas))
```

El 10 % se reserva para arrancar, cargar la herramienta y escribir el JSON. El
suelo de 60 s existe para que un presupuesto ridículo no acabe midiendo el reloj
en vez del investigador. Con 1500 s y siete preguntas: 192 s cada una, y
`192 × 7 = 1344 ≤ 1500`, así que **el hijo termina y escribe su informe antes de
que el padre lo mate**. El plazo del padre pasa a ser la red de seguridad, no el
mecanismo.

Y el padre **le dice al hijo de cuánto dispone** (`--presupuesto`). Sin esa
mitad, el hijo reparte un valor por defecto ajeno al plazo real.

## Alternativas descartadas

**Subir el plazo por configuración.** No cabe: dos configuraciones a 35 min son
70, más instalación, y el tope del trabajo no puede pasar de 85 minutos sin
romper la ventana de tolerancia del contador de los siete días. Además no
resuelve nada: una pregunta colgada seguiría llevándose las demás.

**Quitar preguntas del banco.** Las dos perecederas son las únicas que un modelo
no puede recitar de memoria (ADR-095). Recortar el banco para que quepa en el
plazo es cambiar la medición para que salga, no para que valga.

**Fiarse del 3 y publicar su porcentaje.** Descartada por el criterio de parada
(a) de la nota de arranque, y con prueba.

## Cómo se comprueba

Cinco mutaciones, cinco rojos, en
`docs/audits/evidencia-el-banco-dice-por-que.md`. Dos merecen mención aquí:

- **M3** —el padre deja de pasar `--presupuesto`— dejó las 40 pruebas en verde la
  primera vez que se corrió. La pieza estaba y el cable no se vigilaba, en código
  escrito ese mismo día. Se añadió el guardián que retrata el `argv` real del
  hijo.
- **M5** nació de un fallo propio: si se cortan todas las preguntas,
  `fuentes_totales` también vale cero, así que el motivo culpaba al buscador y
  mandaba a instalar `ddgs` con el buscador sano. Otro rojo que miente, dentro
  del trabajo que venía a corregir un rojo que miente. Lo cazó una prueba propia
  antes de salir de la rama.

## Lo que este ADR no decide

**Sigue sin haber número.** No dice si Google o NVIDIA sirven, ni cuál es mejor:
arregla el instrumento para que la próxima pasada, si vuelve a no medir, lo diga.
La comparación real es la pasada siguiente.
