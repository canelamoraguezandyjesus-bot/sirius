# ADR-174 — La mina en dos pasadas: la lección se declara en el ADR que la produce y las familias se cuentan solas

- Estado: PROPUESTO
- Fecha: 2026-09-12
- Aprobación: la fusión de la PR por el propietario

## Nota de arranque (escrita ANTES de tocar una línea de código)

### Lo medido antes de escribir esta nota

El repositorio tiene DOS sitios donde debería caer una lección, los dos con su
regla escrita y los dos muertos:

| Sitio | Qué guarda | Regla que declara | Último cambio |
|---|---|---|---|
| `.claude/skills/disciplina-evidencia/patrones.md` | 8 patrones de fallo | «un patrón ENTRA cuando ha mordido dos veces; se PODA lo que lleve un trimestre sin invocarse. La revisión es trimestral, de quince minutos, y decide el propietario» | **2026-08-31** (`5cc3f18`) |
| `docs/audits/registro_defectos.yml` | 32 defectos, **los 32 cerrados**, ninguno abierto | «un defecto NUNCA se borra de aquí: pasa a `estado: cerrado` con el commit que lo cerró» | **2026-08-31** (`5cc3f18`) |

Los dos se tocaron por última vez **el mismo día y en el mismo commit**. Desde
entonces han nacido **48 ADR** —ADR-124 a ADR-173—, con sus correcciones, sus
rondas de revisión y sus raíces encontradas. **Cero lecciones capturadas. Cero
defectos registrados.** Los 8 patrones del catálogo salen todos de dos PR de
agosto, la #136 y la #139.

Y la familia más vieja de la casa siguió mordiendo mientras tanto:

- `AGENTS.md:17-20` dice, a mano: *«ha aparecido seis veces una pieza correcta
  a la que no llamaba nadie, y una séptima casi se construye por duplicado el
  25-08»*.
- El informe de la mina del 31-08 la registra como familia **F3** y cuenta
  *«ya mordió 7 veces documentadas»*.
- **Hoy, 12-09-2026, mordió la octava**: `MirroredWorkItem.cerrada`, calculado
  por el espejo en cada pasada desde que se escribió y leído por nadie en todo
  `src/` y `scripts/` (ADR-173). Nadie va a actualizar el «seis veces» de
  `AGENTS.md`, igual que nadie lo actualizó a siete.

Y el detalle que decide el diseño: **esa familia YA se convirtió en prueba** —
`tests/automation/test_piezas_con_llamante.py`— y aun así mordió. Porque esa
prueba es un **diccionario escrito a mano de cuatro módulos**
(`authority_reversion`, `seven_day_streak`, `projection_verifier`,
`supervisor`): cubre las cuatro instancias que alguien se acordó de añadir, no
la familia. Un campo de un `dataclass` como `cerrada` le es invisible por
construcción.

### 1. ¿Dónde vive el fallo y dónde va el arreglo? ¿Puede el sitio del arreglo OBSERVAR el fallo?

**El fallo no es que falte un sitio donde escribir lecciones: hay dos. Es que
capturar depende de que alguien se acuerde**, y en doce días de trabajo denso
nadie se acordó ni una vez. Un catálogo cuya regla de entrada dice «cuando haya
mordido dos veces» exige que alguien lleve la cuenta, y la cuenta la llevaba un
número escrito a mano en `AGENTS.md`.

El arreglo va donde algo **sí ocurre siempre**: el ADR. Nacen 48 en doce días,
los crea un guion desde una plantilla, y hay una batería de pruebas que ya los
mira uno a uno (`tests/automation/test_citas_de_los_adr.py`).

**¿Puede ese sitio observar el fallo que arregla?** Sí para la mitad que
importa: si la lección es un **bloque declarado** del ADR, su ausencia es un
hecho que una prueba ve, y la batería se pone roja sin ella. No puede observar
la otra mitad —si la lección escrita vale algo— y eso se declara abajo en vez
de prometerlo.

### 2. ¿Qué NO va a garantizar esto?

- **No juzga si una lección es buena.** Una máquina ve que está; no ve que sea
  verdad. Contra eso solo hay revisión humana, y este ADR no la inventa.
- **No rellena los 173 ADR anteriores.** La obligación empieza en ADR-174. Los
  anteriores quedan exentos, y la vista nace casi vacía a propósito: prefiero
  una vista que crece de verdad a una rellenada a posteriori de memoria.
- **No normaliza el significado de una familia.** Si un ADR declara
  `familia: otra-cosa` para lo que en realidad es «pieza sin lector», la cuenta
  sale mal. La vista enseña cada familia con sus ADR para que un humano vea el
  solape; ninguna máquina puede hacer más que eso aquí.
- **No arregla `test_piezas_con_llamante.py`.** Que su lista sea a mano y no vea
  un campo es un trabajo propio; esto solo hace que la familia se cuente.
- **No poda.** La regla «se poda lo que lleve un trimestre sin invocarse»
  necesita medir «invocada», y nada mide eso. Queda fuera, dicho.
- **No inventa una pasada periódica que alguien tenga que ejecutar.** Si la
  revisión dependiera de que el propietario se siente quince minutos cada
  trimestre, este ADR estaría repitiendo el fallo que dice arreglar.

### 3. Criterio de parada (decidido ANTES de ver ningún resultado)

- **(a)** Si capturar la lección no se puede hacer sin pedirle al propietario
  que haga algo, **se para**: sería el mismo defecto con otro nombre.
- **(b)** Si la vista no se puede generar del árbol y solo del árbol —sin
  reloj, sin red y sin `git`, como exige ADR-171—, **se para**. Antes nada que
  una vista curada.
- **(c)** Si hacer obligatorio el bloque exigiera tocar ADR ya fusionados,
  **se para** y la obligación se restringe a los nuevos.
- **(d)** Ninguna prueba nueva se da por buena sin haberla visto fallar contra
  una versión rota a propósito (ADR-001 §3).

### 4. ¿Qué haría el fallo IMPOSIBLE en vez de improbable?

Que **no capturar ponga la batería en rojo**. No un recordatorio, no una
costumbre, no una casilla en una plantilla que se borra sin que nadie se
entere: una prueba que mira cada ADR nuevo y falla si no trae su bloque. Eso
convierte «acordarse» en «no poder seguir sin decidirlo», que es la única forma
que ha funcionado en este repositorio.

Y para la segunda pasada, lo equivalente: **que la cuenta de cuántas veces ha
mordido una familia no la lleve nadie**. Se genera del árbol, como `MEMORIA.md`,
y una prueba falla si la vista confirmada no coincide con lo que el generador
produce. Un número escrito a mano caduca en silencio; uno generado no puede.

Lo que esto NO hace imposible, dicho arriba: que la lección escrita sea mala.

## Contexto y problema

(se completa al cerrar el trabajo)

## Decisión

(se completa al cerrar el trabajo)

## Comprobación que la sostiene

(se completa al cerrar el trabajo)

## Consecuencias

(se completa al cerrar el trabajo)
