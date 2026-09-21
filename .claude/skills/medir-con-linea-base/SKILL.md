---
name: medir-con-linea-base
description: >-
  Cómo se mide un cambio del motor de Sirius para que la cifra valga: la línea
  base primero —el camino de producción tal cual está, no el doble que nunca
  descarta—, el criterio y el suelo escritos antes de medir, la cifra anclada al
  árbol que la produjo y siempre con su comparación al lado, y qué guion mide
  qué (búsqueda sin Ollama, banco con Ollama real, intérprete de peticiones).
  Cárgala antes de lanzar cualquier medición del banco de 47 casos o de
  latencia, antes de escribir una cifra en un ADR o en un mensaje al
  propietario, y cuando alguien —él incluido— lea una cifra como regresión o
  como mejora.
---

# Medir con línea base

**Regla única: una cifra sin línea base y sin árbol no mide nada. Primero se
mide lo que hay, después el cambio, y las dos se escriben juntas con su sha.**

## Por qué existe, con fechas

- **19-09-2026, ADR-203**: el banco solo sabía medir con el motor por etapas
  encendido, así que la línea base de producción —el camino de puerta
  cerrada— no existía y nada de lo medido era atribuible. H-203 sigue abierto
  en el registro de defectos.
- **14-09-2026, ADR-202**: M17, la medición que cerraba la ola de paridad, no
  se hizo y la razón no constaba en ningún sitio; las cifras que sí había:
  7/47 aciertos contra un suelo de 29/47, y 682/671/669 ms contra 300.
- **19-09-2026**: una línea base recién medida se leyó como regresión porque
  la cifra iba sola (hallazgo E-04 de la auditoría, disparador 4).
- ADR-154: las cifras se citan **ancladas al árbol** que las produjo. ADR-125:
  el límite de 300 ms de RNF-003 está suspendido mientras se mide su coste
  real; no es un suelo vigente.

## Los pasos

1. **Antes de medir, en la nota de arranque** (skill `disciplina-evidencia`):
   qué cifra manda, el suelo y qué resultado hace parar. En el banco de 47
   casos la cifra que manda es **omisiones críticas** —lo que el propietario
   declaró intolerable—; los elementos de más son ruido tolerable. Los suelos
   que existen están escritos como pruebas `xfail(strict=True)`: pasarán solas
   el día que se alcancen.
2. **La línea base, primero**:
   `uv run --no-sync python scripts/diagnosticar_busqueda_del_banco.py --puerta-cerrada`
   mide el camino que producción ejecuta hoy, con todas las puertas apagadas
   (ADR-203). Rechaza combinarse con `--peticion`, `--ejes` o `--cupo`, y a
   propósito: esas palancas no existen en ese camino y la cifra parecería
   comparable sin serlo. Sin `--puerta-cerrada`, el mismo guion mide el techo
   de la etapa de búsqueda y las palancas del laboratorio (ADR-148), que no
   son producción: se dice al lado de la cifra.
3. **Con modelo de verdad**:
   `uv run --no-sync python scripts/medir_banco_con_ollama_real.py` (necesita
   Ollama arrancado y tarda minutos; `--diagnostico` dice en qué etapa se
   perdió cada crítica). Si el contador de **rendiciones** no es cero, parte de
   las consultas no pasaron por el modelo: la medición está contaminada y no se
   publica. El intérprete de peticiones se mide aparte con
   `scripts/medir_interprete_de_peticion.py` (ADR-164).
4. **La latencia** se mide con `tests/integration/test_local_performance.py`,
   la prueba que la tabla de V8 cita desde B12c; el límite de 300 ms sigue
   suspendido (ADR-125), así que una cifra por encima no es un rojo, es un
   dato.
5. **La cifra se escribe anclada** (ADR-154): «sobre el árbol de `<sha
   corto>`» y, si existe, el run de Quality de ese head. Una actualización de
   la rama no invalida una cifra anclada ni obliga a repetir el guion; una
   cifra sin árbol no se presenta como la del head vigente.
6. **Siempre con la comparación al lado**: «antes X, ahora Y, suelo Z, árbol
   S». Sin comparación no va ni al ADR ni al propietario
   (`hablar-con-el-propietario`, disparador 4). Y si se decide no medir, la
   razón se escribe en el ADR (ADR-202): «no se midió porque…».

## Qué NO hace esta skill

- **No decide el suelo**: lo fijó el propietario (omisiones críticas
  intolerables) y cambiarlo es cambio de producto (ADR-204).
- **No mide dinero ni coste de sesión**: ver `coste-antes-de-tocar-una-fuente`.
- **No corre en CI lo que necesita Ollama**: los guiones con modelo real son
  manuales por diseño; CI mide con dobles deterministas.
- **No sustituye a la mutación de las guardas**: medir el motor y probar una
  guarda son dos cosas (`disciplina-evidencia`).
