---
name: hablar-con-el-propietario
description: >-
  Cómo se le escribe al propietario de Sirius para que pueda responder: los dos
  modos en que dirige (pegado desde el ordenador, dictado desde el móvil), los
  cinco disparadores medidos que rompen la conversación, la forma de un informe
  que se puede contestar y qué hacer cuando dice «haz lo que tú creas» o cuando
  se enfada. Cárgala antes de escribirle cualquier mensaje, antes de darle una
  cifra, antes de pedirle algo y antes de decidir si una pregunta merece
  molestarle. Las diez reglas de su método están en `AGENTS.md` (ADR-208); esto
  es lo que hay que hacer con ellas.
---

# Hablar con el propietario

**Regla única: el mensaje tiene que poder contestarse con un sí, un no o un
dato. Si no, no está terminado.**

Las diez reglas de cómo conversa están en `AGENTS.md`, sección «Cómo conversa el
propietario, y qué espera», y qué se le pregunta y qué no, en la de ADR-204. No
se repiten aquí. Esto es la parte operativa: lo que hay que hacer al escribir.

## Los dos modos, y cómo se reconocen

| Señal | Modo | Lo que espera |
|---|---|---|
| Texto pegado, lista numerada, prohibiciones explícitas («no hagas commit todavía»), formato del informe pedido | **dirige la ejecución** desde el ordenador | un paso por mensaje, el comando exacto, y **solo** lo que pidió |
| Texto dictado, corto, con faltas, a nivel de meta («vamos a acabar con el empaquetado») | **dirige el rumbo** desde el móvil | que construyas tú el mapa y le preguntes sí/no |

Confundirlos es la fuente número uno de fricción: devolverle un plan cuando
dirige la ejecución, o un comando cuando dirige el rumbo. Él lo fijó el
10-08-2026: «¿tú eres el que me tiene que guiar? Y yo, el que responde y
decide, porque me pones mucho texto y yo no puedo responderte a todo… me
preguntas, y yo te digo sí, no».

## Los cinco disparadores que rompen la conversación

Los cinco están medidos en `docs/audits/AUDITORIA_FORMA_DE_TRABAJO_2026-09.md`,
hallazgo E-04. No son teoría: cada uno tiene fecha y hora.

1. **Una instrucción sin dónde ejecutarla.** Se arregla a la primera con el
   formato **dónde se pega / qué hace / qué va a salir**. Él no programa, y lo
   ha dicho: «no sé ni dónde ponerla».
2. **Prometer que le avisas.** Entre turnos no puedes hablar. Cuatro veces se
   prometió en una sola sesión y ninguna se cumplió. Se dice lo contrario:
   «esto tarda N minutos; cuando me escribas te lo cuento».
3. **Pedirle evidencia de algo que él ya hizo.** Cuando dice que algo está
   probado, está probado; búscalo tú antes de pedirlo.
4. **Una cifra sin su comparación al lado.** El 19-09 leyó una línea base
   recién medida como una regresión, y tenía todo el derecho: la cifra iba
   sola. Toda cifra va con la de antes, o con la palabra «línea base».
5. **Creer que trabajas cuando estás esperando turno.** Si vas a tardar, dilo
   antes de empezar, no después.

Y uno más, de la misma familia: **el menú de opciones**. Lo rechazó siete
veces, cinco en una sola noche.

## La forma de un informe que se puede contestar

- **Primero la respuesta**, después el porqué. Nunca al revés.
- **Cifras con su unidad y su comparación.** «7 179 pruebas en verde, 11 min
  30 s» vale; «todo bien» no.
- **Una pregunta por mensaje**, como mucho. Dos preguntas devuelven media
  respuesta.
- **Sin jerga y sin nombres internos** salvo que él los haya usado antes.
- **Corto.** Si el mensaje no cabe en una pantalla de móvil, sobra algo.

## Datos de su máquina, para que el comando funcione a la primera

Entran aquí los que ya han hecho fallar un comando. Hoy hay dos:

- **Su escritorio está redirigido a OneDrive.** `C:\Users\ASUS\Desktop` **no
  existe**; el real es `C:\Users\ASUS\OneDrive\Desktop`. Así que `$HOME\Desktop`
  falla, y hay que escribir `[Environment]::GetFolderPath('Desktop')`, que lo
  resuelve solo. El 20-09-2026 esto tumbó dos comandos seguidos —el de descarga
  y el de ejecución— y las dos veces el error fue del comando, no suyo.
- **El repositorio está en `C:\Users\ASUS\OneDrive\Desktop\laboratorio sirius\sirius`**,
  con un espacio en el nombre de la carpeta: la ruta va entre comillas. Él no
  la sabe de memoria y lo dijo el 11-09-2026 («¿yo qué sé dónde está la
  carpeta? Tú lo sabes perfectamente»): si el comando la necesita, va escrita.

## Tres reglas más, de septiembre (ADR-213)

Son las reglas 11, 12 y 13 de `AGENTS.md`; aquí va lo operativo.

- **Contesta primero.** Si llega un mensaje suyo mientras esperas a CI o a la
  batería, el siguiente paso es contestarle en dos líneas, antes de lanzar
  nada más. El 14-09 y el 20-09-2026 creyó que la sesión estaba parada o le
  ignoraba, y las dos veces la sesión encadenaba esperas sin responder.
- **El parte de la mañana.** Tres bloques cortos y en este orden: *hice* (con
  enlace); *no hice, y por qué* (una línea por cosa: decidido por ti, bloqueado
  por qué, o dejado para él); *te toca a ti* (comandos con dónde / qué / qué
  sale). Nada más. Lo pidió con esas palabras el 14-09-2026, tres veces en un
  día.
- **Lo del ordenador, en lote.** Mientras dirige desde el móvil, cada cosa que
  exija su ordenador se apunta y se le da junta cuando él diga que ya está
  delante (11-09-2026). Y no se le pide pegar nada que la sesión pueda poner
  ella misma: «¿qué pegar de qué? Ponlo tú, como ya hacemos en otras sesiones»
  (12-09-2026).

## Cuando dice «haz lo que tú creas»

Es una decisión, no un permiso para volver a preguntar. Significa: decide,
ejecuta y déjalo escrito en un ADR que diga que lo decidiste tú (ADR-204). El
20-09 lo dijo siete veces en un solo mensaje, y la respuesta correcta a las
siete era la misma: resolverlo.

## Cuando se enfada

Se enfada por texto largo, por preguntas que podrías resolver tú y por
esperas sin explicación. La reparación **no** es explicar por qué el texto era
largo: es escribir menos, preguntar menos y seguir trabajando. Una disculpa de
una línea y a trabajar.

## Qué NO hace esta skill

- **No decide por él lo que es suyo.** Dinero, salud y cambio de producto se
  preguntan siempre (ADR-204).
- **No es un guion de frases.** No copies los ejemplos: son evidencia de qué
  falla, no plantillas.
- **No cubre el laboratorio físico ni la cabeza robótica**, que él lleva
  aparte y quedaron fuera de alcance el 19-09-2026.
- **No sustituye al ADR.** Lo hablado se pierde; lo decidido se escribe.
