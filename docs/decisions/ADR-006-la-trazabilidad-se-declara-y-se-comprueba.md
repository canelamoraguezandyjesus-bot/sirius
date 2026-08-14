# ADR-006 — Declarar la trazabilidad PA/SP y comprobarla por máquina, en vez de derivarla por búsqueda

- Estado: PROPUESTO
- Fecha: 2026-08-10
- Aprobación: la fusión de la PR por el propietario

## Contexto y problema

B12 exige una matriz que enlace cada prueba del Plan de Pruebas aprobado con lo
que la cubre. Antes de empezar, la situación medida era:

- el plan define **40** identificadores: PA-001 a PA-025, PA-E2E-01, PS-01 a
  PS-07 y SP-01 a SP-07;
- solo **12** aparecían citados en algún archivo de prueba;
- `tests/acceptance/` y `tests/contract/` existen desde V0 y contienen
  únicamente un README que dice «se añadirán cuando la vertical correspondiente
  exista».

El hueco resultó ser de **trazabilidad, no de cobertura**: el comportamiento de
PA-003, PA-004, PA-005 o PA-017 está probado desde hace bloques, pero ninguna
prueba menciona el identificador, así que desde el plan no se ve.

## Criterio de parada (escrito ANTES de decidir)

- Si al verificar una entrada la prueba candidata no demuestra lo que el plan
  pide, se marca `hueco` y se dice. No se apunta una prueba parecida para que
  la fila no quede vacía.
- Si el mecanismo de comprobación pasa igual con la matriz mintiendo, no se
  sube.
- Si cerrar los huecos exige tocar código de producto, se detiene: eso es otro
  subbloque, no este.

## Opciones consideradas

1. **Derivar la matriz buscando los identificadores en `tests/`.** Cero
   mantenimiento aparente.
2. **Declararla a mano en un documento.** Legible, y se pudre en silencio.
3. **Declararla a mano y comprobar por máquina que lo declarado existe.**

## Decisión

Se adopta la opción 3.

La matriz vive en `docs/implementation/TRAZABILIDAD_PA_SP.md` y
`tests/unit/test_pa_sp_traceability.py` verifica que estén los 40
identificadores, que cada prueba nombrada exista en su archivo y con su nombre,
que la cobertura sea `automática`, `parcial` o `manual`, que las dos últimas
declaren un motivo de un vocabulario cerrado (`proveedor-real`,
`windows-real`, `evaluación-humana`) y que todo hueco esté además listado como
tal.

## Comprobación que la sostiene

**La opción 1 quedó descartada por una medición, no por preferencia.** Buscar
`PA-010` y `PA-016` en `tests/` devuelve `tests/automation/test_sirius_issue.py`
y `tests/automation/test_validate_issue_body.py`. Al abrirlos, la cadena que
coincide es:

```python
"## Requisitos y pruebas de aceptación\nPA-010 a PA-016.\n\n"
```

Es el cuerpo de una incidencia de ejemplo usada como fixture de la
automatización. No cubre nada. Una matriz derivada por búsqueda habría
registrado ahí cobertura de PA-010 y PA-016 —dos identificadores de doce— y esa
cobertura falsa es peor que una fila vacía, porque nadie vuelve a mirar una
casilla que ya está marcada.

**Siete mutaciones, todas con el resultado predicho antes de ejecutarlas:**

| Mutación | Resultado |
|---|---|
| Identificador omitido de la matriz | 1 falla |
| Prueba renombrada en la matriz | 1 falla |
| Archivo inexistente en una referencia | 1 falla |
| Cobertura fuera del vocabulario | 1 falla |
| `parcial` sin motivo | 1 falla |
| Hueco borrado de la tabla de huecos | 1 falla |
| **Prueba real renombrada en el código** | 1 falla |
| Restaurado | 122 pasan |

La séptima es la que decide: renombrar `test_store_is_always_false` en
`tests/unit/test_openai_responses_provider.py` hace fallar la comprobación de
SP-04. Sin ella las otras seis solo demostrarían que el analizador lee su
propio texto.

Una comprobación del propio analizador se encontró durante esto: la primera
versión leía también la tabla de huecos, cuyas filas empiezan igual por un
identificador, y producía entradas fantasma. Lo cazó la propia prueba al
ejecutarse por primera vez.

## Consecuencias

- Renombrar o borrar una prueba citada rompe CI con el identificador exacto
  que se quedó sin cobertura.
- Los huecos son visibles y contados: PA-025 (no se mide rendimiento),
  PA-009 · PA-E2E-01 · PS-01 a PS-07 (evaluación humana) y PA-023 (tráfico en
  Windows real).
- `automática` no significa PA superada, y la matriz lo dice en su cabecera.
  Confundir ambas cosas es el error que V8_EXECUTION ya lleva advirtiendo.

## Lo que esto NO garantiza

- **No mide la calidad de la prueba citada.** Una prueba vacua cuenta igual
  que una buena; contra eso está la mutación de ADR-001, no esta tabla.
- **No demuestra que la cobertura sea suficiente** para la prueba del plan.
  Que `test_store_is_always_false` cubra SP-04 es un juicio humano registrado,
  no algo que la máquina compruebe.
- **No cubre la trazabilidad requisito–PA**, que vive en el plan aprobado.

## Alternativas descartadas y por qué

- **Opción 1** (derivar por búsqueda): descartada por la medición de arriba.
  Habría registrado cobertura falsa el primer día.
- **Opción 2** (declarar sin comprobar): es lo que ya existía en forma de prosa
  dispersa, y produjo 12 identificadores citados de 40 sin que nadie lo notara.
- **Poblar `tests/acceptance/` con una prueba por PA** que replique lo que ya
  prueban las suites de integración y GUI: descartada. Duplicaría la cobertura
  para satisfacer una taxonomía, y la duplicación es exactamente lo que ADR-005
  acaba de quitar de la documentación.
