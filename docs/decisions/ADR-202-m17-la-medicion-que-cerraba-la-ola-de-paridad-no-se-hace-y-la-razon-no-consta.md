# ADR-202 — M17, la medición que cerraba la ola de paridad, no se hace; y la razón no consta

- Estado: APROBADO
- Fecha: 2026-09-14
- Aprobación: el propietario, el 14-09-2026, en conversación: «M17 se decidió que
  no se iba a hacer... si se hace, se hace en otro momento».
- Incidencia: #647

- Nota de arranque de esta rama: **este ADR**, publicado con su criterio de
  parada antes del primer cambio del registro (precedente: ADR-063).

## Criterio de parada (escrito ANTES de mirar nada)

Este trabajo no cambia código. Termina cuando:

1. Queda escrito **qué** se decidió sobre M17 y, explícitamente, que **la razón
   no consta**.
2. Las cifras que M17 iba a evaluar se citan de una corrida real, no de memoria.
3. La incidencia #503 queda desbloqueada por escrito, no de palabra.
4. La cadena entera en verde.

**Me detengo, sin terminar, si** para justificar la decisión tuviera que
reconstruir una razón que nadie tomó. En ese caso se escribe el hueco.

## Contexto y problema

La Arquitectura Técnica 0.2 §11.5 fija una ola de cinco encargos —M13 a M17—
para llevar a producción la paridad que el laboratorio ya tenía. **M17 es su
punto de control**: sobre el pipeline con M13-M16 integrados, ejecutar las dos
pruebas `xfail(strict=True)` de M11, añadir dos aserciones duras propias y
publicar la cifra real, salga la que salga.

`docs/evolution/STATUS.md` lo dice con estas palabras: la ola *«se cierra cuando
las pruebas lo confirmen, no antes»*.

**M16 se cerró el 01-09-2026** (incidencia #504, ADR-124). **M17 no se encargó
nunca**: no existe ninguna incidencia para él. El trabajo siguió a M18, M19 y M20
(ADR-126 a ADR-129) y la ola se quedó sin su medición de cierre.

Y esa ausencia tuvo un coste concreto y localizable: la incidencia #503 declara
como precondición «M16 y M17 cerrados. Antes no», y lleva desde el 01-09
bloqueada contra un hito que ya estaba decidido que no iba a ocurrir. **Trece
días esperando a algo que nadie iba a hacer.**

## Decisión

**1. M17 no se hace.** Es una decisión del propietario, tomada antes de hoy. Si
algún día se hace, es una decisión nueva: nada de lo escrito aquí la prepara.

**2. La razón no consta, y no se inventa.** Preguntado hoy, el propietario dijo
textualmente: «no me acuerdo por qué, pero se decidió que no se iba a hacer».
Este ADR registra **lo decidido**, no una reconstrucción plausible de por qué.
Escribir una razón verosímil que nadie tomó sería peor que dejar el hueco: se
leería después como si constara.

**3. La ola de paridad queda ABIERTA, no cerrada.** Sin su medición de cierre no
se puede afirmar que alcanzó su objetivo, y `STATUS.md` ya dejó escrito que no se
cierra por declaración. Queda como ola sin cerrar, con esta nota.

**4. La precondición de la incidencia #503 queda vacía.** Una precondición que no
puede cumplirse nunca no bloquea: engaña. La #503 pasa a poder trabajarse.

## Lo que sí se sabe, aunque M17 no se hiciera

La medición que M17 iba a hacer **no está del todo a oscuras**: las dos pruebas
`xfail(strict=True)` de M11 siguen en la suite y publican su estado en cada
ejecución. Medido hoy, 14-09-2026, en la corrida completa de esta rama:

| Criterio | Suelo exigido | Medido hoy |
|---|---|---|
| `aciertos_exactos` sobre el banco de 47 | **29/47** | **7/47** (era 4/47 antes de M13-M16) |
| RNF-003 P95, tres escenarios | **≤ 300 ms** | **682,1 / 671,0 / 669,1 ms** |

Así que no hacer M17 **no esconde un buen resultado**: deja sin registrar
formalmente uno que ya se conoce y que está lejos. Las dos pruebas son
`strict=True` a propósito: el día que el motor por etapas alcance esas cifras,
pasarán inesperadamente y obligarán a retirar la marca. **El hito solo se aprueba
cuando eso sea verdad**, y ese mecanismo sigue vivo aunque M17 no se haga.

## La lección

- familia: `decision-que-solo-vive-en-una-conversacion`
- sin esto se repetiría: una decisión de NO hacer algo no deja rastro —no hay
  incidencia que cerrar ni ADR que escribir, porque el trabajo no existió—, y
  meses después una precondición escrita antes de ella sigue bloqueando trabajo
  real contra un hito que nadie iba a hacer; la #503 estuvo trece días así, y el
  propietario ya no recordaba por qué.
- lo hace cumplir: ninguna prueba: una decisión tomada de viva voz fuera del
  árbol no la puede ver ninguna guarda de este repositorio; lo que la hace
  cumplir es escribirla, que es lo que hace este ADR.
