# Cierre del ciclo: qué hay de verdad a 24 de septiembre de 2026

- Fecha: 2026-09-24
- Quién lo lee: el propietario, antes de decidir qué hace con Sirius; y la
  sesión que reabra el repositorio después de la pausa. Se llega desde
  `MEMORIA.md` y desde ADR-216.
- Caduca con: la primera decisión suya sobre el rumbo. Hasta entonces, vale.

Este documento existe porque el propietario dijo el 24-09-2026 que en cuatro
meses no ve nada que la aplicación haga, y que lo que se le ha contado —
fusiones, revisiones, correcciones — no es lo que él mide. Tiene razón en el
criterio: **una fusión no es una capacidad**. Así que aquí no hay fusiones.
Hay lo que existe, lo que funciona demostrado, lo que no, y con qué número.

## 1. Lo que la aplicación hace hoy, y está demostrado

Sirius 0.1 es una aplicación de escritorio real, empaquetada para Windows y
**aceptada por él mismo el 17-08-2026** ejecutándola en su máquina (B13 y B14,
PR #122). No es una maqueta. Al abrirla hay cuatro pestañas:

| Pestaña | Qué puede hacer el usuario |
|---|---|
| Conversación | hablar con el modelo, con la respuesta llegando por partes, historial que persiste al cerrar y abrir |
| Memoria y decisiones | ver lo guardado, confirmar o rechazar lo que Sirius propone recordar, corregirlo, archivarlo, marcar criticidad y categoría |
| Configuración | clave de API validada contra el proveedor, ubicación de los datos, copia de seguridad y restauración |
| Proyectos históricos | los proyectos anteriores y la continuidad entre sesiones |

Y una página aparte, **Model Studio**, con la superficie de grabación
(interfaz construida; voz y cámaras, no).

Lo que sostiene eso: **7 433 pruebas automáticas en verde**, medidas hoy sobre
el árbol de esta rama, más las dos validaciones manuales en su Windows del
10-08 y el 17-08. Arranca sin hablar con nadie cuando no hay proveedor: eso se
midió (B14), no se supone.

## 2. Lo que NO hace, con su número

Sirius 0.2 —la parte que debía hacerlo **recordar lo que importa**, que es el
problema que él nombró al principio— no está. Y no es una opinión:

| Qué se quería | Suelo exigido | Medido |
|---|---|---|
| aciertos exactos sobre el banco de 47 casos | 29/47 | **7/47** (ADR-202, 14-09-2026) |
| latencia P95, tres escenarios | ≤ 300 ms | **682 / 671 / 669 ms** |

El límite de 300 ms está suspendido mientras se mide (ADR-125), así que la
segunda fila no es un rojo: es un dato. La primera sí es la distancia real.
**Esa es la brecha entre lo que los documentos prometen y lo que la aplicación
hace.** Estaba medida y escrita desde el 14-09; no se le puso delante con esta
claridad.

## 3. Dónde se fue el trabajo

Cuando la auditoría de septiembre contó los ADR que había —196 entonces, **209**
hoy—, el reparto salió así: **44 tratan de la aplicación y 152 del motor, del
método o de la automatización** (ficha PROC-006, estimación declarada como tal).
Es decir: la mayor parte del esfuerzo de estos meses fue en la máquina que
construye, no en lo que él abre. La auditoría lo dejó escrito el 19-09; este
documento lo repite porque es la respuesta honesta a su pregunta.

## 4. Qué queda parado y cómo se reenciende

- **El motor**: 91 trabajos en su diario, 59 entregados y 31 cancelados.
  Ninguno espera ya decisión, salvo lo que dice el punto siguiente.
- **Cinco workflows con horario** siguen despertando solos
  (`motor-sirius`, `reconcile-sirius-states`, `reflejar-desenlace`,
  `contador-siete-dias`, `mina-mensual`). Con el diario sin trabajo vivo, un
  turno mira, no encuentra nada y sale: no rompen nada, pero consumen minutos
  de Actions. Se apagan desde la pestaña **Actions** de GitHub, cada uno con
  «···» → «Disable workflow», y se vuelven a encender igual. **No se han
  tocado los ficheros a propósito**: su horario está derivado y vigilado por
  guardas cruzadas (`tests/automation/test_contador_de_siete_dias.py`), y
  desactivarlos desde la interfaz no toca ese diseño ni exige cambiar ninguna
  prueba.
- **El repositorio entero es la copia de seguridad**: todo lo decidido está en
  `docs/decisions/`, el método en `.claude/skills/`, el estado del motor en la
  rama `estado-del-motor`. Un `git clone` se lo lleva todo.

## 5. Lo que este cierre NO pudo hacer

- **Los cuatro trabajos que esperaban decisión siguen esperando en la rama
  `estado-del-motor`.** Se comprobó que `sirius-decidir … --terminar` los cierra
  limpiamente —se ejecutó sobre una copia y los cuatro quedaron `cancelled`,
  terminal—, pero esta sesión **no puede escribir en esa rama**: es estado
  compartido que solo escribe el workflow (idea aparcada I-009). Los cuatro
  comandos que lo cierran desde su ordenador están en ADR-216, para el lote.
- **`WI-20260828-122242` no se puede cerrar con nada.** Está `active` desde el
  28-08 y es de clase `investigacion`, un carril **retirado** el 08-09
  (ADR-161/163). Ningún comando admite esa transición: `sirius-decidir` solo
  resuelve paradas sin incidencia y se niega, con razón, a inventar un cambio
  de estado que el dominio no admite. Queda registrado como H-216. En la
  práctica no hace nada: el despachador rechaza su clase y ningún workflow lo
  toca.

## 6. Si mañana se retoma solo el robot

Lo que vale para eso y ya está construido: el motor de trabajo con su diario,
el ciclo de revisión, la disciplina de evidencia y las diecinueve skills de
`.claude/skills/`. Lo que no: la aplicación de escritorio y la memoria de 0.2,
que son otro producto. Separarlos es una decisión suya, no de esta sesión.
