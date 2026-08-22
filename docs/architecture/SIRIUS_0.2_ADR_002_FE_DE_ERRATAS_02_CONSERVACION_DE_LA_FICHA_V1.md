# Fe de erratas 02 — qué significa «conservar intacta» la ficha `ADR002-A` v1

**Estado:** PROPUESTO · **Rama:** `evidence/adr001-spikes` · **Fecha:** 2026-07-31

**Documento afectado:** `SIRIUS_0.2_ADR_002_PAQUETE_CORRECCION_01_ADR002A_v0.1.md`, §4,
punto 1.

**Naturaleza:** contradicción interna entre dos puntos del mismo párrafo. No
afecta a ninguna cifra, muestra, método, veredicto ni identidad de commit.

---

## 1. Qué dice el documento afectado

El §4 del paquete de corrección 01 afirma dos cosas que no pueden ser ciertas a
la vez:

> 1. **La ficha `ficha_ADR002-A_v1.json` se conserva intacta**, con su blob y su
>    huella. […]
>
> 4. Por tanto se emitirá **`ficha_ADR002-A_v2.json`**, con motivo de
>    sustitución, y **v1 pasará a `SUSTITUIDA`** por el mecanismo de versionado
>    que el contrato ya implementa.

El punto 4 obliga a escribir `SUSTITUIDA` en el campo `estado` de la v1. El
campo `estado` forma parte de la **forma canónica** sobre la que se computa la
huella —así lo define `card_protocol.huella_canonica`, que excluye únicamente el
propio campo de huella—. Marcar la v1 como sustituida, por tanto, **recomputa su
huella y cambia su blob**. El punto 1, leído al pie de la letra, lo prohíbe.

## 2. Cuál de los dos manda, y por qué

Manda el punto 4, porque es el mecanismo que el contrato implementa y el que la
regla 5 de `ADR002-TOL-210` hace obligatorio:

```
verify_cards.fallos_de_unicidad:
  "{candidato}: {n} fichas CONGELADA a la vez (versiones {versiones});
   una version sucesora obliga a marcar SUSTITUIDA la anterior"
```

Dejar la v1 en `CONGELADA` junto a una v2 también `CONGELADA` **bloquea el
verificador de fichas**. No hay lectura del punto 1 que permita cumplir a la vez
el contrato y la literalidad de «su blob y su huella».

## 3. Qué se conserva realmente, y qué cambia

Lo que el punto 1 protege —y sigue protegido— es que **la v1 no se reescriba
para simular que nunca existió ni que nunca fue defectuosa**:

| Elemento de la v1 | Estado |
|---|---|
| Todos los límites por etapa | **sin tocar** |
| Todas las declaraciones (`no_invoca_el_barrido_de_t0`, `senal_tardia`, `ciclo_de_indice`, …) | **sin tocar** |
| `commit_de_referencia` `c01f23fc2652ddb038cdccc59fca3cd19c9a5b28` | **sin tocar** |
| Presencia del fichero en el repositorio | **se conserva**, no se borra ni se retira |
| `estado` | `CONGELADA` → `SUSTITUIDA` |
| `congelacion.huella` | recomputada como consecuencia del cambio de estado |

El diff completo de la v1 en el commit de la ficha v2 son **exactamente dos
líneas**: el estado y su huella derivada.

## 4. Dónde sigue estando el contenido original, íntegro

El contenido de la v1 tal como se congeló no desaparece: queda inmutable en el
historial de Git.

| Dato | Valor |
|---|---|
| Commit que congeló la v1 | `b96e6ea76d60bc51f1dc0cb8e9f3d12cb3900d25` |
| Blob de `ficha_ADR002-A_v1.json` en ese commit | `1a96f535250bce643e8ccf2edb0362b3ec9320fe` |
| Huella canónica declarada entonces | `00571890294bcd18748e2ee600eb43bad1b92f80` |

Se recupera con `git show b96e6ea:artifacts/adr002_cards/ficha_ADR002-A_v1.json`,
y su blob es verificable con `git hash-object`. Ambas huellas —la de
`CONGELADA` y la de `SUSTITUIDA`— quedan inventariadas en
`custody_errata.HASHES_NO_ALMACENADOS` con el motivo por el que no resuelven a
ningún objeto Git.

## 5. Lo que esta fe de erratas NO hace

- **No corrige el documento afectado en su sitio.** El §4 del paquete de
  corrección 01 se queda como está: es historial, y su contradicción es parte de
  lo que ocurrió.
- No cambia ningún defecto diagnosticado, ningún criterio de corrección del §5
  ni ninguna de las prohibiciones del §6.
- No aprueba a `ADR002-A` como preparado para benchmark.
- No autoriza ninguna medición.

---

**Regla que queda escrita para las siguientes sucesiones:** «conservar intacta»
una ficha sustituida significa conservar **su contenido normativo y su blob
original en el historial**, no congelar el campo que el contrato obliga a
mover. Una ficha sustituida se **marca**; no se borra ni se reescribe.
