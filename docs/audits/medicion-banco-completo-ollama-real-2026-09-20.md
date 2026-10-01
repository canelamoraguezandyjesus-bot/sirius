# El banco entero con Ollama real, 20-09-2026: dos de los tres suelos de D1, alcanzados

`uv run python scripts/medir_banco_con_ollama_real.py --diagnostico` en la
máquina del propietario, sobre `main` en `66f11424`, modelo
`qwen3:4b-instruct`, espera 30 s. **47 llamadas, 0 rendiciones, 0,7 min** —
medición válida por el criterio del propio guion.

Es el motor por etapas abierto **más el adaptador real del filtro de
relevancia**: la máquina entera, no la etapa de búsqueda sola. Todas las cifras
del banco medidas hoy antes de ésta decían `SIN FILTRO` y no son comparables
con ella.

## El resultado

```
  Aciertos exactos ...... 8/47      suelo D1: 29/47 -> por debajo
  Omisiones criticas .... 0         suelo D1: 1 o menos -> ALCANZA
  Cobertura ............. 70/81     suelo D1: 63 -> ALCANZA
  Elementos de mas ...... 218       (ruido tolerable)
  Llamadas 47 · Rendiciones 0 · 0.7 min
```

**Dos de los tres suelos de D1, alcanzados.** El que falta es el de precisión.

## El diagnóstico, que es lo que hay que leer

```
  caso       critica   laboratorio (fila 4)   produccion (hoy)
  B04-CA-33  DEC-003   NO_ENTRO               OK
  B04-CA-34  DEC-003   NO_ENTRO               OK
  B04-CA-34  MEM-014   NO_ENTRO               OK
  B04-CA-34  MEM-016   NO_ENTRO               OK

  Laboratorio, fila 4:  4 criticas perdidas
  Produccion, hoy:      0 criticas perdidas
```

**Producción pierde menos elementos críticos que el laboratorio del que salió
el diseño.** El laboratorio pierde 4; el Sirius de hoy, 0.

## Reproduce exactamente la medición del 05-09

`evidencia-experimento-filtro-fiel-al-laboratorio.md:265-270`, sobre `main` en
`a07c5d5`: `8/47 exactos, 218 de mas, 0 criticas perdidas, 70/81`. **Las cuatro
cifras idénticas**, y la misma tabla de diagnóstico caso por caso.

Quince días, dos árboles distintos, mismo resultado. **Esta medición es
reproducible**, al contrario que la de D7 punto 6, que tiene ±2 de jitter.

## Predicción, publicada antes de correrla

| criterio | predicho | medido | |
|---|---|---|---|
| críticas perdidas | 0 a 3 | **0** | cumplida |
| cobertura | >= 63/81 | **70/81** | cumplida |
| aciertos exactos | >= 22/47 | **8/47** | **FALLADA** |
| elementos de más | 40 a 90 | **218** | **FALLADA** |

**Por qué fallaron las dos, y es un error mío concreto**: anclé la predicción
en el `22/47; 39 de más` del **02-09**, que está **superado**. Es anterior a
M19b (ADR-128) y M20 (ADR-129). El documento de evidencia contenía la medición
del 05-09 —la vigente— y cité la vieja. Peor: aquel `22/47` venía con **10
críticas perdidas**, así que tampoco alcanzaba el suelo, y fallaba justo en la
métrica declarada intolerable. Decirle al propietario «estabas a siete casos»
fue engañoso, y queda dicho aquí.

## Y el 8/47 no es un defecto: es un precio firmado antes de pagarlo

Del 02-09 al 05-09, misma máquina y mismo modelo: críticas perdidas **10 → 0**,
cobertura **59 → 70/81**, aciertos exactos 22 → 8, elementos de más 39 → 218.

La causa está escrita y es deliberada: la siembra (M20, ADR-129) pone lo
crítico delante del filtro y el rescate por criticidad (M19b, ADR-128) impide
que el modelo lo tire. **ADR-129 aceptó el precio por escrito ANTES de
medirlo**: la siembra mete en cada consulta todo lo no ordinario del ámbito, el
filtro solo lo poda hasta 218, y los aciertos exactos bajan porque *la
respuesta trae de más, no de menos*.

Esa distinción es lo que queda de todo esto: **el problema pendiente no es que
Sirius olvide. Es que trae demasiado.** Lo que falta para el tercer suelo es
podar 218 sin volver a perder lo crítico.

## Nota operativa

El `.venv` vive dentro de una carpeta sincronizada por OneDrive, y `uv sync`
volvió a fallar con «Acceso denegado» al borrar el `dist-info`, igual que el
05-09 (ya anotado entonces como riesgo de la máquina, no del código). Se
recuperó y midió entero, pero sigue siendo una bomba de relojería.
