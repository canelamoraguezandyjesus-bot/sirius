# SIRIUS 0.2 — ADR-002 · Paquete de trabajo 09 · `ADR002-TOL-210` · ficha de candidato ejecutable

**Versión:** 0.1
**Estado:** **PROPUESTO** · no aprueba ninguna puerta y no autoriza ninguna ejecución
**Fecha:** 31 de julio de 2026
**Rama:** `evidence/adr001-spikes`
**Commit de partida:** `f1cd4ab` — acta de aprobación de `ADR002-TOL-209`
**Puerta que trabaja:** `ADR002-TOL-210`
**Protocolo aplicable:** `SIRIUS_0.2_ADR_002_PROTOCOLO_MEDICION_v0.2_PROPUESTO.md`
**Registro aplicable:** `SIRIUS_0.2_ADR_002_REGISTRO_TOLERANCIAS_v0.5_PROPUESTO.md`
**No autoriza:** ejecutar T0, los pasos 2 y 3 de `ADR002-TOL-208`, implementar o ejecutar candidatos, el benchmark, ni fusionar el PR #117.

---

## 1. Por qué este paquete

`ADR002-TOL-209` quedó satisfecha por su acta. Quedan dos puertas de arranque:
`ADR002-TOL-208` en sus pasos 2 y 3, y `ADR002-TOL-210`.

**TOL-210 es la que puede trabajarse ahora**, y no por comodidad. Sus tres dependencias están cubiertas —el presupuesto de TOL-207, el corpus congelado del paso 1 de TOL-208 y el protocolo de TOL-209— y **no exige ejecutar nada**. Los pasos 2 y 3 de TOL-208 sí: exigen ejecutar T0 sobre el corpus congelado, y ninguna ejecución es admisible sin ficha. **El orden real de dependencias pone TOL-210 antes.** Atacarla no salta ninguna puerta: la precede.

### 1.1 El problema exacto

`ADR002-TOL-210` dice dos cosas con consecuencia:

> Un candidato sin ficha confirmada **no es ejecutable**.
> Una ejecución que no referencie una ficha previa **no es utilizable como evidencia**.

Ambas son comprobables por máquina. **Ninguna se comprobaba.**

La plantilla describía el contenido en prosa y dejaba el cumplimiento a la buena fe de quien la rellenase. La congelación era una fecha escrita en una casilla. Eso es **exactamente el defecto que la propia fila del Registro denuncia** de la v0.3, donde la regla «señalaba a un contenedor que no podía alojarla, y su cumplimiento no era auditable».

Repetirlo un nivel más arriba habría sido el mismo error con mejor letra: una regla que nadie puede violar porque nadie la mira no es una puerta, es una intención.

---

## 2. Qué se hace ejecutable

### 2.1 Anterioridad

La congelación deja de ser una fecha y pasa a ser una **relación en el grafo de Git**:

1. el fichero está **confirmado** en el repositorio con ese contenido exacto;
2. el commit en que **entró** es **ancestro estricto** del commit que ejecuta.

**Y el commit de entrada se observa, no se declara.** Una ficha no puede declarar el SHA del commit que la contiene: ese SHA depende del contenido que la incluye, así que el campo sería imposible de rellenar. Es la misma autorreferencia que obliga a excluir la huella de sí misma, y el primer diseño de este paquete la tenía en los dos sitios. Lo que la ficha declara es su **commit de referencia** —el del acto de gobierno bajo el que se congela—; cuándo entró lo busca el verificador en el historial.

**Estricto** importa. Aparecer en el mismo commit que la ejecución no es haber congelado antes: es haber aparecido a la vez. Una fecha se escribe; un ancestro, no.

### 2.2 La huella, y por qué se excluye a sí misma

La huella es el **blob Git de la forma canónica de la ficha excluido el propio campo de huella**.

No es una comodidad de implementación: una huella que se incluyese a sí misma **no tendría punto fijo**, porque escribirla cambia el contenido que la produce. Se descubrió al escribir las pruebas del propio paquete, con el primer diseño, que sencillamente **no convergía**. Excluir el campo no debilita nada, porque el campo excluido es justo el que se comprueba.

La huella dice **qué** se congeló. **Cuándo** lo dice el §2.1. Las dos comprobaciones son distintas y ninguna sustituye a la otra.

### 2.3 Ausencia de resultados

Una ficha contiene **límites y declaraciones**, jamás mediciones del propio candidato. Se hace cumplir **cerrando** todos los conjuntos de campos: lo que el esquema no prevé, no entra.

Una lista de nombres prohibidos se esquivaría renombrando el campo. Un conjunto cerrado, no.

### 2.4 Coherencia con lo ya aprobado

La ficha **cita** el presupuesto de TOL-207 y el perfil de TOL-209; no propone los suyos. El validador comprueba que cita **los aprobados**:

| Magnitud | Valor citado | Origen |
|---|---:|---|
| Presupuesto absoluto por candidato | `1.610.612.736 B` | acta de TOL-207 |
| `SM` | `17.405 ns` | acta de TOL-209 |
| `U50` | `2.685 ns` | acta de TOL-209 |
| Sesiones | `11`, exactamente | acta de TOL-209 |

Una ficha que declarase otros no estaría congelando una tolerancia: la estaría **cambiando en silencio** para su propio candidato.

### 2.5 El universo de fichas no es T1–T4

La v0.2 de la plantilla ya lo había corregido, y el contrato lo hereda: las fichas son de las **alternativas mínimas** de ARQ-00 §23 —`ADR002-A`, `ADR002-B`, `ADR002-C`, `ADR002-D`— más `T0-control`. La partición T1–T4 de ADR-002 v0.2 §3 **no es la misma**, y la Resolución de la partición de candidatos v1.0 zanjó cuál rige.

**Solo `T0` puede fichar como control de falsación.** Marcar `ADR002-A` o `ADR002-C` como control invalida la ficha: no declarar una señal tardía **no es un déficit**, es la alternativa que se pone a prueba.

### 2.6 Coherencias que el contrato recomputa

- la **señal tardía** declarada debe ser exactamente la de la alternativa declarada;
- el bloque de restricciones de `ADR002-D` aplica **si y solo si** la alternativa es `D`;
- la suma de los **límites locales por etapa** debe explicar el coste local total;
- el **coste externo** se declara en texto, no en enteros, para que no pueda entrar en la aritmética que TOL-202 prohíbe;
- ningún **objetivo** puede superar a su propio límite duro;
- el porcentaje y el «¿cabe?» del almacenamiento se **recomputan**;
- una operación **ejecutable** no declara exención; una **no ejecutable** declara motivo técnico y evidencia alternativa, antes de ejecutar.

---

## 3. Materialización

| Artefacto | Efecto |
| --- | --- |
| `SIRIUS_0.2_ADR_002_FICHA_CANDIDATO_TEMPLATE_v0.3_PROPUESTO.md` | plantilla **nueva**; la v0.1 y la v0.2 se conservan sin modificar |
| `experiments/adr002/cards/card_protocol.py` | reglas vinculantes y propiedades comprobables |
| `experiments/adr002/cards/schema_card_v0_1.py` | contenido mínimo, con todos los conjuntos **cerrados** |
| `experiments/adr002/cards/verify_cards.py` | verificación contra Git; no mide y no ejecuta candidatos |
| `experiments/adr002/cards/test_adr002_cards.py` | pruebas de las reglas y del recorrido |

Las plantillas anteriores conservan sus nombres, sus blobs y sus etiquetas. Su intangibilidad es un **control bloqueante** de este paquete, por la misma razón que la del protocolo v0.1 y el Registro v0.4 en el paquete 08: sus blobs están citados en documentos ya publicados.

---

## 4. Controles internos bloqueantes

Catorce. Fallan **cerrado**: un control ausente o distinto de `True` es fallido.

**Se computan sobre las fichas presentes, y solo si hay alguna.** Con cero fichas el recorrido no publica catorce `True`: publica «sin fichas que controlar». Publicarlos en verde sin haber mirado ninguna ficha sería justo el defecto que este paquete corrige, un nivel más arriba.

El último no se deriva de que ninguna ficha falle —eso sería compatible con un verificador que nunca denuncia nada—: se **sondea**, comprobando que una referencia sin respaldo sale efectivamente `NO_UTILIZABLE`.

| Control | Qué comprueba |
| --- | --- |
| `plantilla_anterior_intacta` | los blobs de la v0.1 y la v0.2 |
| `contenido_minimo_completo` | las secciones y campos de TOL-210, uno a uno |
| `conjuntos_cerrados` | ninguna clave ajena al esquema, en ninguna sección |
| `sin_marcadores_vacios` | ni vacío ni «pendiente» ni «n/a» |
| `presupuesto_de_tol207_citado` | el entero aprobado, no uno propio |
| `perfil_de_tol209_citado` | `SM` y `U50` aprobados |
| `once_sesiones_exigidas` | exactamente 11, no «al menos» |
| `coste_local_coherente` | la suma por etapas explica el total |
| `coste_externo_no_sumado` | el externo se declara aparte, en texto |
| `puertas_previas_declaradas` | las seis, una a una |
| `papel_de_control_reservado_a_t0` | ninguna alternativa mínima ficha como control |
| `senal_tardia_coherente_con_la_alternativa` | la señal es la de su alternativa |
| `anterioridad_comprobada_contra_git` | ancestro estricto, no fecha |
| `ejecucion_sin_ficha_no_utilizable` | **sondeado**: una referencia sin respaldo sale `NO_UTILIZABLE` |

### 4.1 El estado de las puertas también se deriva

`verify_cards` no acepta que le declaren qué puertas están satisfechas: lo **deriva de las actas que existen**. `ADR002-TOL-208` y `ADR002-TOL-210` salen en `False` porque no tienen acta, y por tanto **ningún candidato es ejecutable hoy**. El verificador lo dice ejecutándose:

```text
$ uv run python -m experiments.adr002.cards.verify_cards --check
fichas conformes: 0
puertas de arranque pendientes: ['ADR002-TOL-208', 'ADR002-TOL-210']
controles bloqueantes: sin fichas que controlar
ADR002-TOL-210 no queda satisfecha por esta comprobacion: la satisface su acta.
```

---

## 5. Lo que este paquete NO hace

1. **No emite ninguna ficha.** No hay candidato autorizado que fichar, y este paquete no lo autoriza. El repositorio no contiene ninguna ficha, y una prueba lo comprueba.
2. **No aprueba `ADR002-TOL-210`.** La satisface su acta, no este paquete.
3. **No implementa ningún candidato** ni decide cuál es mejor.
4. **No ejecuta T0** ni los pasos 2 y 3 de `ADR002-TOL-208`.
5. **No mide nada.** No abre cronómetro, no lanza procesos, no toca SQLite.
6. **No modifica** `src/`, `tests/`, `migrations/` ni configuración productiva.
7. **No fusiona el PR #117.**

---

## 6. Limitaciones conocidas

1. **La ficha de referencia de las pruebas es un fixture**, no la ficha de ningún candidato real. Su único propósito es dar un punto de partida conforme a las mutaciones que se le aplican.
2. **El contrato comprueba la forma, no la verdad.** Que un límite esté declarado, sea completo y no contradiga lo aprobado no lo hace correcto: la corrección de un límite es responsabilidad de quien lo congela. Lo que el contrato impide es declararlo **tarde**, **incompleto** o **contradictorio**.
3. **La anterioridad se comprueba contra el grafo de Git.** Un historial reescrito la invalidaría, que es el comportamiento querido, pero también significa que la garantía es tan fuerte como la custodia del repositorio.
4. **`T0-control` no declara alternativa mínima ni señal tardía.** Es el control de falsación: incumple RF-14 y no compite. Su ficha existe y se valida igual, pero esas dos secciones quedan en `null`.
5. **La coherencia entre el §2.12 y el §2.13** —suma por etapas contra extremo a extremo— se comprueba sobre los **límites duros**, no sobre los objetivos: es el par que decide el descarte.
6. **El contrato no verifica que la rederivación de T0 exista.** Solo exige que la ficha declare si existe y, si no, por qué. Mientras `ADR002-TOL-208` no esté satisfecha en sus tres pasos, ninguna ficha puede declarar una rederivación real.

---

## 7. Estado de las puertas al cerrar este paquete

| Puerta | Estado |
|---|---|
| `SRC-ADR002-01` | **SATISFECHA** |
| `ADR002-TOL-207` | **SATISFECHA** |
| `ADR002-TOL-209` | **SATISFECHA** |
| `ADR002-TOL-208` · paso 1 | **COMPLETADO** |
| `ADR002-TOL-208` · global | **NO SATISFECHA** — faltan los pasos 2 y 3 |
| `ADR002-TOL-210` | **NO SATISFECHA** — este paquete la deja **instrumentada y lista para su acta** |

**El benchmark continúa bloqueado.**

---

**Siguiente movimiento único:** que el usuario apruebe o corrija la plantilla v0.3 y el contrato de este paquete. Con esa aprobación, `ADR002-TOL-210` puede quedar satisfecha por acta, y la única puerta de arranque pendiente serían los pasos 2 y 3 de `ADR002-TOL-208`, que **sí exigen ejecutar T0** y requieren por tanto autorización expresa e independiente.
