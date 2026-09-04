# Los dos cambios de `.github/**` que salen de la mina v2 (para la mano del propietario)

ADR-002: la automatización no toca `.github/**`. Estos dos cambios son tuyos.
Cada uno con el fichero, la línea y el texto exacto. Diez minutos entre los dos.

## 1. El corrector debe demostrar la mutación y firmar con su run

Fichero: `.github/workflows/repair-sirius-work.yml`.

(a) En el paso `build_prompt` (línea ~588), añadir al prompt del corrector
esta frase, junto a donde ya se le exige demostrar la corrección con una
prueba:

> En el comentario CORRECCION_APLICADA incluye, por cada hallazgo, la
> MUTACIÓN concreta que aplicaste para ver fallar la prueba nueva (qué línea
> cambiaste y a qué) y la primera línea del fallo de pytest. Una corrección
> sin su mutación vista fallar no está demostrada (ADR-001).

(b) En el mismo workflow, donde se publica el comentario `CORRECCION_APLICADA`
con el marcador `<!-- sirius-verdict:corrector:FIXED:<head> -->`, añadir el
run al marcador:

```
<!-- sirius-verdict:corrector:FIXED:<head>:${GITHUB_RUN_ID:-manual}-${GITHUB_RUN_ATTEMPT:-1} -->
```

(los marcadores de `precheck` de ese mismo fichero, líneas 253-425, ya llevan
`${GITHUB_RUN_ID}`: es copiar el mismo sufijo). Con esto desaparece el hueco 2
del informe de la mina (atribuir runs por correlación temporal) y, si el
corrector muere, el run queda citado para leer sus tiempos.

Por qué: «prueba que no puede fallar» es la familia más extendida de la ola
(7 hallazgos en 4 encargos, §4 del informe) y las 3 muertes del corrector no
dejaron diagnóstico (§5).

## 2. La carrera de Quality (4 veces en esta ola)

El verde de Quality que llega mientras la incidencia está en
`sirius:repairing` o `sirius:reviewing` no se consume, y hay que relanzar el
run a mano (#508, #514, #520 ×2).

Opción barata (una línea): `.github/workflows/reconcile-sirius-states.yml`,
línea 35, cambiar

```
    - cron: '17 */6 * * *'
```

por

```
    - cron: '17 * * * *'
```

(de cada 6 horas a cada hora: la carrera se cura sola en ≤1 h en vez de ≤6).

Opción completa (más delicada, para cuando quieras): en
`.github/workflows/advance-sirius-after-quality.yml` (selección de candidatas,
líneas ~104-114), aceptar también incidencias en `sirius:repairing` cuyo
último veredicto del corrector sea FIXED con el MISMO head que el run verde
de Quality — es exactamente el caso de la carrera, y el head evita registrar
un verde de un head viejo. Si eliges esta, conviene encargarle al motor las
pruebas del cambio y que tú pegues solo el YAML.

## Nota: el guardián de goteo (ADR-123) está mudo y ya se sabe por qué

No es tuyo, es un encargo del motor pendiente de tu OK: el guardián solo
entiende `ruta:número` limpio al final del campo `archivo`
(`_LOCATION_LINE_RE` en `src/sirius_engine/drip_guard.py:67`), y los
revisores escriben ese campo con adornos («…py:1436-1449 (_set_controls_enabled)»,
«…py:1490 en 6899ecf», «(… ~líneas 766-805)»). Probado el 04-09-2026 con los
seis campos reales de la ola: solo uno de seis se entiende; por eso hubo 5
goteos reales y 0 marcas. El arreglo natural es endurecer
`parse_archivo_location` para extraer ruta y primera línea aunque haya
adornos, con los seis casos reales como pruebas.
