# ADR-199 — El detector de familia repetida detiene el ciclo, y esa parada vuelve al corrector, no al revisor que la emitió

- Estado: APROBADO
- Fecha: 2026-09-14
- Aprobación: el propietario, el 14-09-2026, con la cifra de ADR-197 delante
  (14 aciertos y 2 falsos sobre 16). Este ADR ejecuta esa decisión.
- Incidencia: #642
- Nota de arranque: `docs/audits/arranque-el-detector-de-familia-detiene-el-ciclo.md`

## Contexto y problema

El detector de familia repetida (ADR-078, incidencia #277) se cableó al ciclo
real en la incidencia #495 **a propósito sin autoridad**: publicaba
`## AVISO_FAMILIA_REPETIDA` y a continuación el ciclo aplicaba
`sirius:repair-requested` exactamente igual que si no hubiera avisado. La razón
estaba escrita y era buena: el criterio de la incidencia #267 pedía medir su
tasa real antes de darle autoridad.

**La medida se completó y el ciclo siguió igual.**

| | aciertos | falsos | sobre |
|---|---|---|---|
| ADR-078 (agrupamiento viejo) | 4 | 0 | 14 |
| ADR-197 (agrupamiento nuevo) | **14** | **2** | **16** |

Mientras tanto se pagaron las vueltas que el detector ya señalaba: 7 rondas en
la incidencia #501 —rondas 1-3 la misma clave reservada en tres capas, rondas
5-6 el mismo anclaje del diff dos veces, **las siete P2**— contra una media de
2,93; y 15 vueltas en la incidencia #545.

## Criterio de parada (escrito ANTES de tocar nada)

Está en la nota de arranque de esta rama, publicada antes del primer commit de
código, con sus cuatro preguntas. Las dos condiciones de abandono que fijaba
—parar si hubiera que mentir sobre el rol en el marcador, y parar si hubiera
que tocar `.github/**`— **no se dieron**: el diseño de abajo no necesita
ninguna de las dos.

## Decisión

**1. Con familia repetida detectada, la puerta del veredicto detiene el ciclo.**
En vez de `sirius:repair-requested`, publica `sirius:blocked-decision`. El
comentario conserva todo lo que ya publicaba —las observaciones estructuradas y
el `## RONDA_HALLAZGOS` de la ronda— y añade cómo se sale.

**2. Esa parada vuelve al CORRECTOR, no al revisor que la emitió.** Es la única
de las tres paradas cuyo destino no es la fase que la produjo, y el motivo es
que `continua` significa «ya lo he mirado, sigue y corrígelo»: lo que queda por
hacer es una corrección. Para que el guion de reanudación pueda saberlo, el
marcador declara la razón, con la misma forma que ya usan las paradas
`precheck:<razón>:`:

```
<!-- sirius-verdict:reviewer:blocked:familia-repetida:<head>:<run> -->
```

El rol sigue siendo el verdadero —`reviewer`, que es quien ve el patrón entre
rondas—: no se falsea el historial, se enruta por la razón.

**3. La parada no perdona rondas.** El reset del listón de convergencia se
reserva a los bloqueos que emite la propia política. Aquí el ciclo ya ha
demostrado que da vueltas: debilitar el guarda del bucle justo ahí sería lo
contrario de lo que esta parada busca.

## Comprobación que la sostiene

La nota de arranque **predijo el defecto del diseño ingenuo antes de escribir
una línea**: cambiar solo la puerta del veredicto produciría un rebote, porque
reanudar lee el rol del marcador y esta parada la emite el revisor. La prueba
lo confirmó al pie de la letra antes del arreglo:

```
assert 'sirius:repair-requested' in ['sirius:review-requested']
```

Es la forma del defecto **H-33** (incidencias #453 y #471), que este
repositorio ya pagó una vez.

Cuatro mutaciones, todas vistas fallar:

| | mutación | qué suspende |
|---|---|---|
| M1 | la puerta sigue aplicando `repair-requested` | el aviso vuelve a ser decorativo |
| M2 | la reanudación no distingue esta parada | el rebote: vuelve a revisión |
| M3 | el desvío se aplica a **todo** `:blocked:` del revisor | reabre H-33 para el bloqueo de rol legítimo |
| M4 | la puerta se inventa otra razón y no la declara | la parada nueva nace sin vuelta |

## Lo que este ADR NO hace

- **No diagnostica la raíz ni propone la salida.** Eso sigue siendo la
  incidencia #251. Esta parada se la pone delante a una persona; no adivina.
- **No elimina los falsos positivos**: 2 de cada 16, y cada uno cuesta un
  `continua`. El precio está aceptado con la cifra delante.
- **No toca el umbral del detector** (3 rondas consecutivas sobre el mismo
  archivo) ni el agrupamiento que fijó ADR-197.
- **No toca la política de convergencia** ni ninguno de sus umbrales.
- **No resuelve la incidencia #503**, que pide algo distinto: que el criterio de
  parada mire la **severidad**. Esto mira la **repetición**.
- **No garantiza que un solo `continua` baste siempre.** Si la familia se
  detecta en una ronda en la que la política de convergencia ya iba a bloquear,
  el corrector arrancará y se parará acto seguido en su propia puerta
  (`precheck:convergencia-<razón>`), que sí perdona rondas al reanudarse. Serían
  dos órdenes en vez de una. No es un rebote —cada parada avanza a una distinta y
  la segunda se levanta sola—, pero es un coste real y se dice en vez de
  descubrirse.

## Lo que ya existía y no hubo que tocar

Las dos piezas que hacen útil esta parada estaban puestas, y comprobarlo antes
evitó ampliar nada:

- `sirius:blocked-decision` ya avisa al propietario:
  `.github/workflows/notify-sirius-state.yml` dispara con esa etiqueta.
- `sirius:blocked-decision` ya estaba en `SIRIUS_PARADAS_REANUDABLES`, así que
  `continua` ya la levantaba.

Por eso este cambio **no toca `.github/**` en absoluto**: era una de las dos
condiciones de abandono de la nota de arranque, y no llegó a hacer falta.

## El hueco que sí cierra, y por qué importaba más que el caso

H-33 se descubrió **en producción**, sobre dos incidencias reales, porque cada
emisor nuevo de `sirius:blocked-decision` se venía enrutando a mano y nadie
comprobaba que lo estuviera. Cuando el enrutado se olvida, la parada no falla:
reanuda la fase equivocada, que es peor, porque tiene aspecto de haber
funcionado.

`test_toda_parada_de_bloqueo_con_razon_propia_declara_su_vuelta` cierra la
clase: lee del guion del veredicto los marcadores `:blocked:` que llevan razón
propia y exige que el guion de reanudación nombre cada una. Una parada que
mañana se invente su razón y no la declare suspende ahí sola.

No interpreta shell —leerlo desde el texto de un guion exigiría un intérprete
entero, que es justo por lo que ADR-001 retiró la puerta de `git push`—: lee
literales de marcador, que es exactamente lo que el guion de reanudación
también lee del historial.

## La lección

- familia: `guarda-medida-que-se-queda-sin-autoridad-porque-nadie-relee-la-medida`
- sin esto se repetiría: una guarda se fusiona a propósito sin autoridad para
  medirla primero, la medida se completa y el disparador —«cuando haya datos
  suficientes»— no dice quién comprueba si ya los hay; el detector acertó 14 de
  16 mientras el ciclo pagaba 7 rondas en la incidencia #501 y 15 en la #545.
- lo hace cumplir: `tests/automation/test_reanudar_una_parada.py`
