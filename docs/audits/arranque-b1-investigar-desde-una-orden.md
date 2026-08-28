# Nota de arranque — B1: que una orden de investigación produzca un informe

Fecha: 2026-08-28. Publicada ANTES del primer cambio de código (ADR-001).

## El estado, medido

- `interpretar_intencion_v0` YA clasifica «investiga…» como clase
  `INVESTIGACION` (líneas 53–54 de `intent_interpreter.py`).
- El despachador la RECHAZA: no hay fila en `TABLA_ACTIVACION`
  (`ClaseNoDespachableError`), ni perfil en `TABLA_PERFILES`.
- El ejecutor existe y está MEDIDO: la configuración de ADR-098 dio 7/7 con
  fuentes reales (S2, run 33141864710). Lo que falta es la costura: que una
  incidencia de clase investigacion la atienda ese ejecutor y devuelva el
  informe por el ciclo normal.

## Lo que se construye (el precedente es C3/ADR-088, misma costura)

1. Fila `INVESTIGACION` en `TABLA_ACTIVACION` (mismas etiquetas que
   programacion/documentacion) y perfil `investigador@1` en `TABLA_PERFILES`.
   La tabla dice que añadir una fila es enmienda de contrato: ADR-099 la
   autoriza, igual que ADR-088 autorizó la de DOCUMENTACION.
2. Ejecutor `investigar-orden.yml`: se dispara con la misma etiqueta de
   activación, PERO gobernado por `Perfil: investigador@` — y el workflow del
   implementador EXCLUYE ese perfil en su puerta, ANTES de consumir el evento,
   para que nunca corran los dos.
3. El ejecutor no es un agente de Claude: es el investigador MEDIDO (mismo
   entorno del banco: python 3.12, gpt-researcher 0.15.1, NVIDIA + Tavily,
   `research_report`, que es el tipo con número). Corre la pregunta del
   `## Objetivo`, escribe `docs/investigaciones/<fecha>-<slug>.md` CON su
   cabecera de caducidad, abre la PR, comenta `PR abierta: <URL>` y aplica su
   veredicto con `sirius_apply_verdict.sh` — el MISMO protocolo del
   implementador, sin inventar marcador nuevo.
4. El revisor de ese perfil es `revisor-documental`: el entregable es un
   documento.

## Las cuatro preguntas

1. ¿La prueba del despachador se ve FALLAR antes (ClaseNoDespachableError,
   como en C3) y pasar después con las MISMAS etiquetas que documentacion?
2. ¿La puerta del implementador excluye `investigador` ANTES de consumir el
   evento? Si excluyera después, el evento se perdería consumido y nadie lo
   atendería.
3. ¿El informe generado cumple el guardián de caducidad de
   `docs/investigaciones/` (titulo, fecha, pregunta, caduca_con, estado)? Ese
   guardián corre en Quality sobre la PR del propio informe: un informe sin
   cabecera moriría en su propia revisión.
4. ¿El veredicto PROVISIONAL (`FAILED_SAFELY`) se escribe ANTES de investigar,
   como exige el protocolo? Si el proceso muere a mitad, el ciclo tiene que
   encontrar un veredicto, no un silencio.

## Criterio de parada

- (a) Si la costura exigiera un marcador o protocolo NUEVO en el ciclo, se
  para: el ciclo entiende el protocolo del implementador y B1 tiene que hablar
  ese idioma, no enseñarle otro.
- (b) El tope del trabajo nuevo no puede pasar de 85 minutos (ventana del
  contador, §11.2). Se fija en 30.
- (c) Si el ejecutar la orden exigiera claves de OpenAI o Anthropic, se para.
  NVIDIA + Tavily, las que ya están.
- (d) Regla de las dos rondas (ADR-001).

## Lo que NO se toca

Ni el banco de medición, ni el contrato §8 (fusionar sigue siendo del
propietario), ni la clase MIXTA ni el descomponedor (ADR-089, aplazado). El
examen «lado a lado contra ChatGPT» NO es esta rama: necesita esta costura
viva primero.
