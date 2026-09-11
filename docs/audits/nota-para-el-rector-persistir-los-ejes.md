<!-- Nota preparatoria para el proceso del Rector. NO es un encargo ni un ADR: no autoriza implementar nada. -->

# Persistir los ejes de la memoria — nota preparatoria para el Rector

**Fecha:** 11-09-2026. **Origen:** decisión del propietario, tomada ese día:
«sí en principio: guardar los ejes; formalizar por el Rector».

## Por qué esto NO se lanza como encargo

Es un **cambio de esquema** de la memoria canónica de Sirius. El Documento
Rector (§17, «regla de activación», que la enmienda §19 deja **sin tocar**)
exige, para cualquier etapa posterior a 0.1, Definición de Producto aprobada,
pruebas de aceptación reproducibles y arquitectura técnica aprobada. Un encargo
del ciclo no puede sustituir eso, y esta nota tampoco: solo reúne lo que ese
proceso va a necesitar, medido y no recordado.

## Qué son «los ejes», con el árbol delante

`EjesDeclarados` (`src/sirius/domain/staged_engine_contracts.py:204-226`):
`confirmacion`, `validez`, `disponibilidad`, `valid_from`, `valid_to`,
`sensibilidad`, `autoridad`, `ambito`, `no_usar_como_memoria`,
`no_consolidable`, `procedencia` y `miembros_de_ambito`. Su propio docstring
los define como «los ejes que el esquema canónico de Sirius 0.1 no persiste
hoy». El puerto real entrega **todo** ítem con `ejes=SIN_EJES`
(`src/sirius/adapters/persistence/staged_engine_port.py:29`), y las puertas que
los necesitan «degradan» al estado colapsado.

## Lo medido que sostiene la decisión

- **La palanca 2 (08-09) midió que derivarlos de las columnas de hoy no paga**:
  con el arnés fechado a fondo, `16/47; 164; 73/81; 0` frente a `17/47; 162;
  74/81; 0` de `main`; y con los ejes del corpus inyectados, su rama y `main`
  dan **exactamente lo mismo** (`21/47; 144`). Conclusión de entonces: *el
  andamiaje que consume ejes ya existe; lo que falta son los ejes.*
- **Distancia entre lo derivado y lo declarado**: 5 exactas y 20 de más.
- **Dos huecos de la línea son este mismo problema en pequeño**:
  - **H3 (`MEM-020`)**: «candidata de fuente externa» son los ejes
    `confirmacion` y `autoridad`. Sirius 0.1 no puede expresarlo: `MemoryStatus`
    es `CURRENT`/`ARCHIVED`/`DELETED`, y el arnés la aproxima **archivándola**
    (`ArchiveMemoryUseCase`), que no significa eso. Las sugerencias canónicas
    (§3.2/§3.3, `src/sirius/domain/memory_suggestion.py`) nunca entran en
    recuperación, así que tampoco sirven de vehículo. **Sin `confirmacion`
    persistida, la decisión del propietario para H3 —«sale, marcada como no
    confirmada»— no es implementable en 0.1.** H3 va aquí.
  - **H5 (`DEC-001`)**: el encargo del 11-09 porta la pertenencia a la fixture
    y arregla `G4`, pero **en producción no entra** hasta que
    `miembros_de_ambito` se persista, porque el puerto entrega `SIN_EJES`.

## Lo que el proceso del Rector tendrá que decidir, y esta nota no decide

1. **Qué ejes se persisten** de los doce, y con qué dominio de valores cada uno
   (el corpus los declara con literales: `CONFIRMADA`/`CANDIDATA`,
   `VIGENTE`/…, `FUENTE_EXTERNA`/`DOCUMENTO_CANONICO`/`ACTO_EXPLICITO_USUARIO`…).
2. **De dónde salen en producción**: el corpus los trae adjudicados; un usuario
   real no. Quién los fija, cuándo, y qué valor por defecto tiene cada uno
   cuando nadie lo fija —que es exactamente la degradación que hoy hacen las
   puertas—.
3. **Cómo se presenta lo no confirmado** (H3): marcado, y con qué texto; y si
   una sugerencia canónica y una memoria `CANDIDATA` son la misma cosa o dos.
4. **Qué pasa con el banco**: hoy es la única fuente de ejes, inyectados por el
   arnés; con ejes persistidos, el arnés deja de necesitar `ejes_por_identidad`
   y las cuatro mediciones que hoy son distintas (bitácora, entrada 83) se
   acercan.

## Lo que esta nota NO garantiza

Que persistir los ejes lleve la memoria al criterio del propietario. La única
medición que lo diría es la de Ollama real en su máquina, caducada desde el
02-09, y esa medición **perdía 10 críticas** con el filtro encendido. Los ejes
tocan las columnas de exactas y hallados; las críticas perdidas son otra
pregunta.
