# Nota de arranque — que el banco diga por qué no midió

Fecha: 2026-08-27. Publicada ANTES del primer cambio de código (ADR-001).

## Lo medido, en la primera pasada real de la comparación

`medir-investigador.yml`, ejecución 33079519839. El atestado pasó —los cuatro
modelos respondieron HOY— y la comparación corrió 30 minutos. Resultado:

```
13:57:21  → nvidia: preparando subproceso propio
14:02:42    nvidia: fallo — el subproceso terminó con código 3.
            Final de su salida: … 📚 Getting relevant content based on query:
            "Current star count for GPT Researcher GitHub repository…"
14:02:42  → google: preparando subproceso propio
14:27:42    google: agotado_el_tiempo — pasó de 1500 s y se cortó.
```

**Veredicto: NO CONCLUYENTE.** Ninguna de las dos se midió. El guardián hizo lo
que debe —no publicar un número que no existe— y aun así el instrumento no sirve,
porque **no dice qué pasó**.

## Hallazgo 1: hay una rama que no se puede alcanzar

`comparar_investigadores.medir_configuracion` tiene esto, en este orden:

```python
if proceso.returncode != 0 or not salida_json.is_file():
    base.estado = ESTADO_FALLO
    base.detalle = f"el subproceso terminó con código {proceso.returncode}…"
    return base                       # <-- sale aquí

crudo = sin_secretos(salida_json.read_text(…), [clave])
resultado = json.loads(crudo)
if not resultado.get("medicion_fiable", True):
    # «El hijo ya sabe que lo suyo no vale y lo dice»
    base.detalle = str(resultado.get("motivo_no_fiable", …))
```

Y `medir_investigador.main` termina así:

```python
if not resultado.medicion_fiable:
    sys.stderr.write(f"MEDICION NO FIABLE: {resultado.motivo_no_fiable}\n")
    return 3
```

El hijo devuelve **3 exactamente cuando** la medición no es fiable. La primera
guarda del padre atrapa todo código distinto de cero. Por tanto **la rama que
lee `motivo_no_fiable` no se ejecuta nunca**: es código muerto con un comentario
que explica por qué es importante.

Eso es lo que impide hoy contestar «¿por qué NVIDIA no fue fiable?». El motivo se
escribió, viajó en el JSON y el padre lo tiró para poner en su lugar la cola de
unos registros `INFO` del buscador.

Octavo caso de la enfermedad de esta casa, y el más difícil de ver: no es una
función sin llamante ni un dato sin lector, es **una rama inalcanzable por
construcción**, protegida por la guarda que la precede.

## Hallazgo 2: el plazo no cabe en el banco

El banco tiene **siete** preguntas desde que se le añadieron las dos perecederas.
NVIDIA hizo las siete en 5 min 21 s (~46 s por pregunta). Google no terminó en
1500 s, o sea **más de 214 s de media disponibles y aun así no llegó**: o es tres
veces más lento, o **se colgó en una pregunta**.

El plazo es por CONFIGURACIÓN, así que una sola pregunta colgada se lleva por
delante las otras seis, que ya estaban contestadas. Se tira una medición entera
por un cuelgue puntual, y el informe solo puede decir «agotado_el_tiempo».

## Las cuatro preguntas

1. ¿Se ve **FALLAR antes** una prueba que ejecute el camino real —hijo que sale
   con 3 y escribe su JSON— y compruebe que el padre publica el motivo?
2. ¿Sigue siendo `fallo` un código distinto de 0 y de 3, y sigue siéndolo un 3
   **sin** JSON escrito? Distinguir 3 no puede convertirse en «confiar en el 3».
3. Con plazo por pregunta, ¿una pregunta colgada deja las demás medidas, y el
   informe dice cuáles se cortaron? Una medición parcial que se presente como
   completa sería peor que no medir.
4. ¿El plazo por pregunta **por siete** sigue cabiendo dentro del plazo por
   configuración y del tope del paso? Un plazo interior mayor que el exterior no
   protege nada: lo corta GitHub y nos quedamos sin informe.

## Criterio de parada

- **(a)** Si al distinguir el código 3 un porcentaje no fiable acabara publicado
  como medida, se para: sería exactamente la raíz que la refutación del 26-08
  tumbó.
- **(b)** Si el plazo por pregunta hiciera que una configuración con TODAS las
  preguntas cortadas se presentara como medida, se para.
- **(c)** Si hiciera falta subir el tope del trabajo por encima de 85 minutos, se
  para: rompe la ventana de tolerancia del contador de los siete días.
- **(d)** Regla de las dos rondas (ADR-001).

## Lo que NO se toca

No se cambian los modelos, ni el banco de preguntas, ni el atestado. El problema
de hoy no es qué se mide: es que el instrumento no sabe contar lo que le pasó.
