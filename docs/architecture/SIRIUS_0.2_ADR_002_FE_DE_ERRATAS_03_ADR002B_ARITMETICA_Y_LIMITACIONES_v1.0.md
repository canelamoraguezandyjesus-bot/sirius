# Fe de erratas 03 — aritmética declarada y limitaciones conocidas de ADR002-B v1

**Estado:** PROPUESTO · **Rama:** `evidence/adr001-spikes` · **Fecha:** 1 de agosto de 2026

**Documentos afectados:**
`SIRIUS_0.2_ADR_002_PAQUETE_TRABAJO_12_ADR002B_SENAL_VECTORIAL_TARDIA_v0.1.md` (§6)
y `artifacts/adr002_cards/ficha_ADR002-B_v1.json` (fundamento de la operación
`construccion` del ciclo de índice), huella `c1ca17a7f5345b4cec2a0ea63dac6c8b1bb6e5fd`.

**Origen:** revisión adversarial independiente de la entrega de `ADR002-B`
(commits `d2cebcb8591293bacaa94e0b56b6e667b5e86f00` →
`765dc9f` sobre la ficha congelada en `ac2fa93`), ejecutada antes del push.

**Naturaleza:** dos erratas de transcripción aritmética en texto ya congelado
y el registro de las limitaciones conocidas halladas por la revisión.
**Ninguna afecta a un límite vigente, a una muestra, a un veredicto ni a la
huella de ninguna ficha.** Nada se corrige en sitio: la evidencia publicada no
se reescribe; se declara.

---

## 1. Errata A — la suma de filas insertadas contradice sus propios sumandos

El §6 del paquete 12 y el fundamento de `construccion` de la ficha declaran:

> «dominado por ≤149.442 filas insertadas (4.096 + 4.096 + 550 + 140.800) × 20.000 ns»

La suma correcta de esos mismos sumandos es **149.542** (no 149.442; error de
transcripción de 100). Además el constructor inserta 6 filas de `metadatos` no
contadas: el total exacto es **149.548**.

**El techo declarado sobrevive con el margen declarado:**
149.548 × 20.000 ns = 2,991·10⁹ ns < 5·10⁹ ns → margen 1,67× ≥ el «≥1,6×»
declarado. El límite de 5·10⁹ ns de la ficha **no cambia**; cambia solo la
cifra intermedia del fundamento, y por eso esta errata se declara en vez de
reescribir un texto cuya huella está congelada.

## 2. Errata B — el alcance de la justificación de `ESCALA_FIJA`

El §6 justifica la escala 10⁶ así:

> «PPMI ≤ ln(550) ≈ 6,31 → valores ≤ 6,31·10⁶; cuadrados ≤ 4·10¹³; sumas de
> ≤256 dimensiones ≤ 1,1·10¹⁶ < 2⁶³»

Esa aritmética acota los **pesos de término persistidos** y el producto
escalar de la consulta. No acota el peor caso teórico de la
`norma_cuadrada` de un **vector de elemento**, cuyos valores por dimensión son
sumas de hasta 64 aportes de término: el extremo adversarial es
≈ 256 × (64 × 6,31·10⁶)² ≈ 4,2·10¹⁹ > 2⁶³ ≈ 9,22·10¹⁸.

**Alcance real:** exigiría que decenas de términos de un mismo elemento
aportaran su peso máximo a la misma dimensión, un canon adversarial sin
relación con la escala de referencia (en el fixture, la norma máxima
observada queda en el orden de 10¹²). Y si alguna vez ocurriera, el fallo es
**ruidoso y cerrado**: `sqlite3` rechaza el entero fuera de rango en la
construcción; no hay corrupción silenciosa. Queda registrado que la cota
citada cubre lo persistido por término, no la norma del elemento.

## 3. Limitaciones conocidas registradas (sin corrección en sitio)

Halladas por la revisión adversarial; **ninguna es alcanzable con el fixture
técnico** y por eso ninguna prueba las dispara. Se registran para que el acto
que decida la preparación de `ADR002-B` las tenga delante, y para que ninguna
corrección posterior pueda presentarse como si el defecto no hubiera existido.

1. **Materialización de coincidencias sin clave útil.** Una coincidencia
   vectorial cuyo elemento tenga clave de sujeto vacía, o comparta clave con
   más de 512 elementos, no puede materializarse por el puerto y se descarta
   sin traza (`candidate.py`, filtro de item ausente). Los elementos sin
   clave son inmaterializables **por diseño** —la clave es parte declarada de
   la representación—, pero el descarte silencioso contradice la letra de
   «ninguna degradación» y una corrección exigirá **ficha v2**.
2. **Ventana de examinados antes de las exclusiones.** El corte de
   `ELEMENTOS_EXAMINADOS_MAXIMOS` (4.096) se aplica en SQL con orden por
   identificador, antes de filtrar lo ya recuperado. Con más de 4.096
   candidatos el corte es determinista pero ciego a la relevancia. Nunca
   vinculante a la escala de referencia (≤550 elementos).
3. **Canon ilegible en la apertura del lector.** Si el fichero del canon no
   es legible al recomputar la huella, el error escapa **sin tipar** (error
   de SQLite, no `IndiceNoUtilizableError`) y la conexión del sidecar queda
   sin cerrar. Nada continúa —sigue siendo un fallo—, pero ni tipado ni sin
   residuos: por debajo de la letra del contrato de fallo cerrado.
4. **Ventana entre lecturas en `construir`.** Los elementos y la huella del
   canon se leen en dos conexiones consecutivas; una mutación concurrente del
   canon entre ambas sellaría un índice desfasado como válido. El protocolo
   ejecuta sesiones de proceso único, donde la ventana no existe; fuera de
   ese supuesto la garantía de desfase no rige.
5. **El techo de almacenamiento no se autoimpone.** `ALMACENAMIENTO_MAXIMO_SIDECAR_B`
   es un límite declarado, como todos los límites de ficha: el código no lo
   hace cumplir en construcción y lo verificará el benchmark bajo TOL-207.
   La prueba técnica lo comprueba solo a la escala del fixture.
6. **Notas menores.** El determinismo prometido es por entorno (`libm` puede
   diferir entre plataformas; todo es LAB-LINUX); `sqlite3.connect` crea un
   fichero vacío si la ruta no existe (afecta a utilidades de ciclo de vida
   invocadas contra rutas erróneas); el candidato no expone cierre explícito
   del lector (irrelevante en Linux); la dependencia `TOP_K ≤
   ARGUMENTOS_MAXIMOS` que hace correcta la materialización queda ahora
   aseverada de forma directa en las pruebas estáticas.

## 4. Lo que esta fe de erratas NO hace

- **No corrige la ficha `ADR002-B` v1 ni el paquete 12 en sitio**: sus blobs
  y la huella `c1ca17a7f5345b4cec2a0ea63dac6c8b1bb6e5fd` quedan intactos.
- No emite ficha v2: ningún límite vigente cambia y ninguna fuente de la
  huella del candidato se toca.
- No aprueba a `ADR002-B` como preparado para benchmark ni lo descarta.
- No autoriza medición alguna.

**Regla que queda escrita:** cualquier corrección futura del código de
`adr002_b/` —incluida la limitación 1— cambia fuentes de la huella del
candidato y exige **ficha v2** con motivo de sustitución, conforme a la regla
3 de custodia del acta de TOL-210 y al §10 del paquete 12.
