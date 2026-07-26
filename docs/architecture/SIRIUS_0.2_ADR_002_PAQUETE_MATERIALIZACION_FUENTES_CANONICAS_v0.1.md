# SIRIUS 0.2 — ADR-002 · Paquete de materialización de fuentes canónicas

**Versión:** 0.1  
**Estado:** AUTORIZADO PARA BÚSQUEDA LOCAL Y MATERIALIZACIÓN DOCUMENTAL  
**Rama:** `evidence/adr001-spikes`  
**Aprobación previa:** Registro de Tolerancias v0.4 y artefactos asociados aprobados el 26 de julio de 2026  
**No autoriza:** benchmark, T0/T1–T4, prototipos, cambios productivos ni merge.

## 1. Objetivo

Satisfacer `SRC-ADR002-01` materializando en el repositorio las tres fuentes canónicas completas:

1. `SIRIUS_0.2_BLOQUE_04_BUSQUEDA_Y_RECUPERACION_v1.0_APROBADO.docx`
2. `SIRIUS_0.2_PLAN_DE_PRUEBAS_Y_REGISTRO_EXTERNO_DE_DELEGACIONES_v1.0_APROBADO.docx`
3. `SIRIUS_0.2_ARQ_00_MARCO_RECTOR_ARQUITECTURA_Y_MAPA_DECISIONES_v1.0_APROBADO.docx`

## 2. Regla de búsqueda

Antes de pedir archivos al usuario, buscar los nombres exactos en:

- el repositorio y sus carpetas padre;
- el directorio personal;
- `Downloads` / `Descargas`;
- `Documents` / `Documentos`;
- `Desktop` / `Escritorio`;
- carpetas locales de Claude y del proyecto Sirius accesibles a la sesión.

No usar coincidencias de nombre aproximadas como fuente canónica. No sustituir un APROBADO por una versión PROPUESTO.

## 3. Verificación mínima

Para cada archivo encontrado:

- nombre exacto;
- tamaño en bytes;
- SHA-256;
- documento legible como DOCX;
- portada o propiedades internas compatibles con la versión y el estado APROBADO;
- no contiene macros ni archivos ejecutables incrustados;
- no es un enlace, acceso directo ni archivo vacío.

Referencias ya verificadas para contraste cuando coincidan con los archivos locales disponibles:

- Plan de Pruebas + RED/PDP: SHA-256 `39058c0f5fe50bb4b703411bd5296e1bb8b1ede513ccf2d9eacabb35da3f59fd`, tamaño 93.708 bytes.
- ARQ-00: SHA-256 `730a5fd13dce18bfcdb8dd4afee23dfe22c067c7cb3b953a9bd115cf73224f49`, tamaño 85.951 bytes.

Si un archivo con el mismo nombre tiene otra huella, no descartarlo automáticamente: inspeccionar su portada y contenido, informar la discrepancia y detener la publicación de ese archivo hasta resolverla.

## 4. Destino propuesto nuevo

Crear únicamente si las fuentes se verifican:

`docs/architecture/canonical_sources/`

Copiar allí los tres DOCX con sus nombres exactos y crear:

`docs/architecture/canonical_sources/MANIFEST.md`

El manifiesto debe registrar por archivo:

- nombre;
- versión y estado;
- tamaño;
- SHA-256;
- origen local encontrado;
- fecha de materialización;
- autoridad de aprobación;
- relación con `SRC-ADR002-01`.

No registrar en el manifiesto rutas personales completas; usar una descripción minimizada del origen, por ejemplo `Descargas del usuario`.

## 5. Resultado permitido si falta una fuente

Si falta cualquiera de las tres:

- no inventar ni reconstruir el documento desde resúmenes;
- no copiar versiones propuestas;
- no declarar satisfecha `SRC-ADR002-01`;
- copiar y publicar únicamente las fuentes verificadas si hacerlo no genera ambigüedad;
- entregar la lista exacta de ausencias y las ubicaciones buscadas.

## 6. Validación

Antes del commit:

- confirmar que solo se añaden `docs/architecture/canonical_sources/` y, si procede, el manifiesto;
- volver a calcular SHA-256 desde las copias dentro del repositorio;
- comprobar que las huellas antes/después coinciden;
- confirmar que los tres documentos son legibles;
- `git status --short` limpio salvo las rutas autorizadas;
- no modificar `src/`, `tests/`, `migrations/`, `experiments/`, `artifacts/` ni documentos anteriores.

## 7. Publicación

Cuando las tres fuentes estén verificadas:

`docs(adr002): materialize canonical benchmark sources`

Push a `evidence/adr001-spikes`. No abrir PR nuevo y no fusionar el PR #117.

Si falta alguna fuente, no hacer el commit final de cierre de `SRC-ADR002-01`; publicar solo un commit parcial si las fuentes presentes están inequívocamente verificadas y el manifiesto marca la puerta como `NO SATISFECHA`.
