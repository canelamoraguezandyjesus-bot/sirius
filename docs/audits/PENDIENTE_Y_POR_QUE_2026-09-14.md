# Lo que queda, y por qué no está hecho — 14 de septiembre de 2026

Este documento existe porque el propietario preguntó exactamente eso: *«quiero
saber si no está hecho, ¿por qué? Porque al final yo quiero tener todo bien
hecho, pero supongo que también dejé trabajo atrás porque se decidió que no se
iba a meter»*.

Tenía razón en las dos mitades. **Hay cosas sin hacer, y hay cosas que se decidió
no hacer** — y hasta hoy no había ningún sitio donde se distinguieran. Ese era el
defecto: un «no se hace» y un «no se ha hecho todavía» se parecen mucho desde
fuera, y el segundo se pudre.

**Método.** Se listan las incidencias abiertas el 14-09-2026 y se clasifica cada
una. Nada se deduce del título: cada fila dice dónde se comprobó. Lo que no se
comprobó se dice.

**Qué NO es este documento.** No es un plan ni una priorización. No decide nada:
solo separa lo pendiente de lo descartado y pone la razón al lado de cada cosa.

## A · Hechas, y cerradas hoy

Su arreglo estaba en `main` y seguían abiertas porque nadie las había cerrado
—un defecto de aseo, no de trabajo—. Se cerraron el 14-09 con su razón escrita.

| | qué era | su arreglo |
|---|---|---|
| #608 | fusionar una PR costaba una ronda en todas las demás | ADR-200 |
| #609 | el despachador dejaba salir encargos que ADR-002 prohíbe | ADR-188 |
| #613 | las paradas de la puerta de sensibilidad no tenían salida | ADR-189 |
| #625 | la red de seguridad llevaba 35 días ciega | ADR-193 |
| #628 | una PR en conflicto no recibe ningún run de Quality | ADR-194 |
| #630 | «podar» no estaba definido en ninguna parte | ADR-195 |
| #632 | `MEMORIA.md` dejó de caber en una sola lectura | ADR-196 |
| #642 | el detector medido y acertando, y el ciclo seguía parcheando | ADR-199 |

Dos de ellas —#609 y #613— se le habían contado al propietario esa misma mañana
como «trabajo pendiente». **Era falso**: sus arreglos se habían fusionado la
noche anterior. La corrección está aquí porque el error también cuenta.

## B · Decididas hoy y en marcha

| | qué es | estado |
|---|---|---|
| #503 | el ciclo no distingue criticidad: 7 rondas de P2 | **desbloqueada hoy** |
| #646 | la mina solo se escribía si a alguien se le ocurría | ADR-201 |

La #503 llevaba desde el 01-09 con una precondición —«M16 y M17 cerrados»— que
**no podía cumplirse nunca**, porque M17 estaba decidido que no se haría. Trece
días bloqueada contra un hito que nadie iba a hacer. Se trabajará **después** de
que la autoridad del detector (ADR-199) lleve unos ciclos midiéndose, porque las
rondas que la #503 cita son justo las que esa autoridad corta: puede que al
medirlo el problema sea otro, o mucho más pequeño.

## C · Apuntes para debatir, NO encargos

El propietario pidió expresamente registrarlas y **no** implementarlas. No están
hechas porque no había que hacerlas.

- **#506 — el tercer tipo de memoria («dónde nos quedamos»).** La incidencia
  dejaba una comprobación pendiente —leer `project_continuity.py` antes de
  afirmar que era un hueco— y **hoy se ha hecho**.

  **Ya existe y ya llega al modelo.** `ProjectContinuityUseCase` modela
  `state_summary`, `blockers` y `next_step`, uno por proyecto, apilando
  revisiones inmutables; `src/sirius/application/send_message.py` los mete en el
  prompt bajo `# Proyecto activo`, y `src/sirius/application/context.py` los
  cuenta contra el presupuesto de contexto.

  Lo que falta es mucho más pequeño: **nada lo actualiza solo**. Lo rellena una
  persona, así que el dato solo dice la verdad si alguien se acuerda de
  escribirlo — la familia `regla-que-depende-de-que-alguien-se-acuerde` otra vez.
  Y sigue viva la pregunta que el propietario hizo entonces: si se rellenara
  solo, **¿qué lo protege de guardar basura?**

- **#267 — mecanizar el método.** Es una lista de cinco candidatos, no un
  encargo. El candidato 1 —la regla de las dos rondas— **lo cerró ADR-199 hoy**.
  Quedan cuatro, y el propio apunte avisa de que mecanizar «se declaró una
  mutación» no es mecanizar «se pensó bien».

## D · Laboratorio y producto, no motor

Contenedores de largo plazo abiertos desde julio: #8 (panel maestro), #9 (cierre
de 0.1), #10 (roadmap), #11 (cabeza robótica), #12 (mano y brazo), #13
(laboratorio físico), #14 (reglas operativas), #15 (backlog), #25 (patrón
operativo), #127 y #134 (Model Studio).

No son trabajo del motor pendiente: son el sitio donde vive el plan. Cuentan como
abiertas porque nunca se cierran, no porque estén atrasadas.

## E · Decidido que NO se hace, con la razón

Esta es la parte que el propietario sospechaba que existía, y existe.

| qué | razón | dónde consta |
|---|---|---|
| **M17**, la medición que cerraba la ola de paridad | decisión suya; **la razón no consta y él no la recuerda** | hasta hoy, en ninguna parte |
| El descomponedor automático (#341) | descartado, no aplazado: partir un objetivo exige un modelo y el motor no ejecuta ninguno | ADR-198 |
| Model Studio · Módulo Voz (#126) | decisión suya | la incidencia, cerrada con su razón |
| Curator | descartado | ADR-195 |
| Ampliar la guarda de citas a `docs/` | **medido**: 0 defectos reales, 23 falsos positivos | ADR-190 |
| Ampliar el alcance de la credencial del motor | decidido en contra | ADR-002 |
| Serializar el motor a un trabajo a la vez (opción C de #608) | tira lo que el propietario pidió: mandar varios trabajos seguidos | ADR-200 |
| Ampliar `test_piezas_con_llamante.py` a `scripts/automation/` | no se amplía una guarda a un árbol vecino sin medir antes su precisión ahí | ADR-200, citando ADR-190 |

**Lo que este documento cambia:** de las ocho filas de arriba, siete ya tenían su
razón escrita en un ADR. Una no —M17— y es justo la que costó trece días de
bloqueo a otra incidencia. Esa asimetría es el argumento entero.

## Lo que sigue pendiente de verdad, en una línea

1. **#503** — la severidad en el criterio de parada, después de medir ADR-199.
2. **#506** — quién actualiza el estado del trabajo, y qué lo protege de basura.
3. **#267** — cuatro candidatos de mecanización del método.
4. **La primera puesta al día real de ADR-200 y el primer disparo de ADR-201**,
   que solo se demuestran ejecutándose y se vigilan a mano.

Todo lo demás de la lista, o está hecho, o está decidido que no se hace.

## Una cuenta que conviene saber antes de añadir el próximo reloj

`contador-siete-dias.yml` no elige su hora: la **deriva** del mayor hueco libre
entre los `schedule:` del directorio, y una guarda exige que su cron sea
exactamente esa hora (ADR-144). Así que un disparo periódico nuevo no basta con
que caiga fuera de su ventana de silencio: **si parte el mayor hueco, la hora
derivada se mueve y el contador deja de cumplir su propia guarda**. Le pasó a
ADR-201 con las 04:00, que caían fuera de la ventana y aun así partían el hueco.

Y hay un detalle que multiplica la cuenta: **el derivador trata un cron mensual
igual que uno diario**. `mina-mensual.yml` solo dispara doce veces al año, pero
reserva su ranura los 365 días. Es conservador y está bien, pero quien añada el
siguiente reloj tiene que contar con ello.

El criterio que queda: el contador se queda con el mayor hueco; un trabajo
periódico nuevo se va al punto medio del siguiente.
