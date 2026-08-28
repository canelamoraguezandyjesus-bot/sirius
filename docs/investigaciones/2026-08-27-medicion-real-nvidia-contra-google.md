---
titulo: La medición real de NVIDIA contra Google, con las claves puestas
fecha: 2026-08-27
autor: el banco de medición del repositorio (medir-investigador.yml), pasadas 2 y 3
pregunta: >-
  Cuál de las dos configuraciones del investigador —NVIDIA o Google AI— puede
  hacer el trabajo de verdad, medido con las claves reales y no sobre catálogo.

# DE QUÉ DEPENDE PARA CADUCAR. Lo que aquí se midió es el comportamiento de dos
# capas gratuitas UN día concreto, desde los runners de GitHub.
caduca_con:
  - las cuotas y límites de la capa gratuita de Google AI (si suben, Google
    merece la revancha; la condición está en el ADR-098)
  - las cuotas de build.nvidia.com
  - el comportamiento de DuckDuckGo con las IP de los runners de GitHub
  - los nombres de modelo (gemini-3.5-flash, nemotron-3-nano-30b-a3b)

estado: PARCIALMENTE CADUCADA
---

> **AVISO (28-08-2026, un día después): la mitad del diagnóstico CADUCÓ ya.**
> Lo que ACERTÓ: el descarte de Google (confirmado con un 429 de cuota agotada
> al día siguiente) y que el cuello era la búsqueda, no el modelo. Lo que
> CADUCÓ: el «28,6 %» y el «DuckDuckGo casi no devuelve fuentes» describen el
> instrumento de aquel día. Con Tavily funcionando y el conteo mirando los DOS
> registros de la herramienta (PR #382), la misma configuración dio **7/7
> (100 %) con 23 fuentes de media** (run 33141864710). El número vigente vive
> en el registro de bloques (S2, cerrado).

# La medición real: NVIDIA contra Google, 27-08-2026

Dos pasadas del banco con las claves reales. No es una opinión ni un catálogo:
es lo que cada configuración HIZO.

## Pasada 2 (run 33079519839) — antes del plazo por pregunta

| configuración | qué pasó |
|---|---|
| nvidia | código 3 en 5 min 21 s: contestó las 7 preguntas, la medición salió no fiable |
| google | **agotó los 1500 s enteros sin dejar ni una respuesta legible** |

## Pasada 3 (run 33088012637) — con plazo por pregunta (192 s) y desglose

| configuración | resultado |
|---|---|
| nvidia | **MEDIDA**: 2/7 (28,6 %), 311,7 s, servidor `https://integrate.api.nvidia.com/v1` |
| google | **0 de 7**: las siete preguntas cortadas exactamente a 192 s cada una |

Desglose de NVIDIA, pregunta a pregunta:

```
[NO] P1 fuentes=0 segundos=30.2    (capital de Australia)
[NO] P2 fuentes=0 segundos=49.0    (llegada a la Luna)
[ok] P3 fuentes=1 segundos=38.8    (licencia de GPT Researcher)
[ok] P4 fuentes=1 segundos=28.1    (lenguaje de uv)
[NO] P5 fuentes=0 segundos=38.3    (Pyre)
[NO] P6 fuentes=0 segundos=56.9    (última versión de uv)
[NO] P7 fuentes=0 segundos=70.4    (estrellas de GPT Researcher)
```

## Lo que estos números dicen, separado de lo que no dicen

**1. Google, en capa gratuita, no puede hacer este trabajo.** El preflight del
mismo día atestiguó que sus dos modelos responden en segundos a una llamada
suelta. Bajo carga real —una pregunta del investigador son decenas de llamadas:
sub-consultas, resumen de cada página, redacción— no completó NI UNA pregunta en
192 s, y las siete fallaron idéntico. Es el patrón de una cuota estrangulada,
aunque el mecanismo exacto no se pudo confirmar desde fuera. No es arreglable
con más plazo: siete preguntas a más de 192 s no caben en ningún tope que la
ventana del contador de los siete días permita (85 min de trabajo, techo duro).

**2. En NVIDIA el cuello ya no es el modelo: es el buscador.** Contestó todo a
~45 s por pregunta. Sus cinco fallos son TODOS `fuentes=0`: DuckDuckGo, desde
las IP de los runners de GitHub, casi nunca devuelve resultados (solo 2 de 7
búsquedas trajeron algo). Con la regla `fuentes > 0` —que existe para que un
modelo no apruebe recitando de memoria— cada búsqueda vacía es un fallo aunque
la respuesta fuera correcta.

**3. El 28,6 % NO es la calidad del modelo.** Es la calidad del conjunto
modelo+buscador con el buscador medio muerto. El «por lo menos un 80 %» que pide
S2 sigue sin poder medirse honestamente hasta que la búsqueda funcione.

## La decisión que esto informa

ADR-098: el investigador se queda con **NVIDIA**. Google queda descartado
mientras su capa gratuita no complete el banco; la condición de revancha está
escrita en el ADR. El siguiente paso para el número de calidad no es cambiar de
modelo: es darle al investigador un buscador que devuelva fuentes.
