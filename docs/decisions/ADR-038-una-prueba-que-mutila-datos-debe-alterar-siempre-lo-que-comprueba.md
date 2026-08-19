# ADR-038 — Una prueba que mutila datos debe alterar siempre lo que comprueba

- Estado: APROBADO
- Fecha: 2026-08-19
- Aprobación: fusión de la PR por el propietario
- Contexto: incidencia #164
- Relacionadas: ADR-001 (disciplina de evidencia)

## Contexto y problema

`test_restore_backup_rejects_a_tampered_backup_without_modifying_data` custodia
el camino que protege las copias del propietario: que una copia manipulada se
rechaza sin tocar los datos actuales. Fallaba de forma intermitente con
`DID NOT RAISE`, el mismo commit y el mismo código, en CI sí y en el re-run no.

La prueba mutilaba así:

```python
envelope["ciphertext"] = f"{ciphertext[:-1]}A"
```

`DID NOT RAISE` significa que `restore_backup` **retornó con normalidad**. La
incidencia lo leyó como que `_read_and_validate` había aceptado un envoltorio
manipulado, y apuntó a la validación. Había una lectura más simple: que **no
hubiera envoltorio manipulado que detectar**.

## Criterio de parada (escrito ANTES de decidir)

Publicado en la incidencia #164 antes de tocar nada
([comentario 5336046312](https://github.com/canelamoraguezandyjesus-bot/sirius/issues/164#issuecomment-5336046312)),
adoptando el que la propia incidencia ya tenía escrito y añadiéndole la cota que
le faltaba:

> Si la causa no aparece tras reproducirla ejecutando la suite completa en
> bucle, **no se parchea la prueba para que deje de fallar**: se convierte en
> determinista mutilando el ciphertext de forma que no dependa de su último
> carácter. Cota: **12 vueltas completas**. Y no toco `restore_backup` sin
> traceback.

Se cumplió al pie: 12 vueltas verdes, no se tocó `restore_backup`, y la causa
apareció por medición y no por el bucle.

## Opciones consideradas

1. Mirar `_read_and_validate`, que es donde la incidencia apuntaba.
2. Sustituir el último carácter por otro **comprobado distinto del actual**, que
   es lo que la incidencia proponía como plan B.
3. Mutilar un carácter cuyos bits sean **todos significativos**.

## Decisión

Se mutila el **primer** carácter, con un sustituto elegido comprobando que
difiere del actual:

```python
sustituto = "A" if ciphertext[0] != "A" else "B"
return f"{sustituto}{ciphertext[1:]}"
```

Sus seis bits son los seis primeros del primer byte: todos significativos,
siempre, con relleno y sin él.

## Comprobación que la sostiene

**La causa, medida sobre 300 copias reales** generadas con el servicio de verdad
y bases de datos de tamaño variable:

| Medida | Resultado |
| --- | --- |
| Copias **sin relleno** (el último carácter es un dato, no `=`) | **297 de 300** |
| Copias cuyo último carácter es `A` | **8 de 300 (2,7 %)** |

En esas 8, `ciphertext[:-1] + "A"` devuelve **el mismo texto**: la copia queda
intacta, `restore_backup` la acepta correctamente y la prueba falla con
`DID NOT RAISE`. Un 2,7 % por ejecución encaja con lo observado —falló en CI y
no en 12 vueltas locales seguidas (probabilidad de no caer en 12: ~72 %)—.

**Esto refuta la refutación.** La incidencia daba por descartada esta hipótesis:

> *«El último carácter es **siempre `=`**: 60 de 60 copias reales.»*

Sobre 300 copias, **297 no llevan relleno**. Aquella muestra de 60 no era
representativa, y la hipótesis correcta se archivó como refutada.

**Y el plan B de la incidencia tampoco habría bastado.** Sustituir el último
carácter de datos por otro distinto es inocuo cuando hay relleno: los últimos
bits de ese carácter no se decodifican, así que dos caracteres distintos pueden
dar los mismos bytes. Medido: **inocuo en 1.032 de 10.000 muestras**.

**Prueba por mutación (ADR-001 §3).** Sobre un ciphertext real sin relleno
acabado en `A` —el caso exacto del fallo—:

| Mutilación | ¿Cambia los bytes? |
| --- | --- |
| La anterior (`[:-1] + "A"`) | **No** — la copia queda intacta |
| La que proponía la incidencia, con relleno | **No** |
| La nueva (primer carácter) | **Sí** |

Y sobre 10.000 muestras aleatorias, la nueva es inocua en **0** casos.

## Consecuencias

- La prueba deja de ser intermitente por construcción, no por reintento.
- Sigue comprobando lo mismo: que una copia alterada se rechaza sin tocar los
  datos. No se ha debilitado nada para conseguir verde.
- `restore_backup` **no se tocó**: nunca hubo defecto ahí. El defecto estaba en
  la prueba, que unas veces no manipulaba nada.

## Alternativas descartadas y por qué

**Mirar `_read_and_validate`.** Era donde apuntaba la incidencia y habría sido
tiempo perdido: no había nada que arreglar. Lo que evitó ir por ahí fue la
condición de no tocar ese código sin traceback — el traceback nunca llegó, y
justamente por eso hubo que medir en vez de suponer.

**El plan B de la incidencia.** Descartado con medición, no por criterio: es
inocuo un 10 % de las veces. Es el motivo por el que este ADR existe en vez de
un commit de una línea — el arreglo evidente también estaba mal.

**Marcar la prueba como `flaky` o reintentarla.** Es el camino que la incidencia
vetó desde el principio, y con razón: habría dejado sin vigilancia el camino que
protege los datos del propietario, que es exactamente donde no se puede.
