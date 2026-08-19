# ADR-042 — Un paso de preparación sin plazo propio puede costar el trabajo entero

- Estado: APROBADO
- Fecha: 2026-08-19
- Aprobación: fusión de la PR por el propietario
- Contexto: incidencias #202 (A4) y #206 (A5)
- Relacionadas: ADR-002 (la automatización no edita `.github/**`; lo hace una sesión interactiva)

## Contexto y problema

El paso que instala las bibliotecas de Qt era esto, sin plazo propio:

```yaml
run: |
  sudo apt-get update
  sudo apt-get install -y --no-install-recommends libegl1 libgl1 libxkbcommon0
```

`apt-get` espera indefinidamente a un espejo que no responde. Sin plazo, esa espera consume el presupuesto del trabajo completo hasta que GitHub lo cancela a los 20 minutos.

Y una ejecución **`cancelled` es peor que una fallida**: `advance-sirius-after-quality` se niega —con razón— a interpretarla como aprobada o suspensa, publica `CI_STOPPED_SAFELY` y deja la incidencia en `sirius:failed-safely`, que exige intervención manual. El bloque se para en seco por una avería que no tiene nada que ver con el trabajo.

Ocurrió **dos veces el mismo día**, en el mismo paso, sin llegar a ejecutar una sola prueba:

| Incidencia | Ventana | Duración del paso | Pasos posteriores |
| --- | --- | --- | --- |
| #202 (A4) | 04:34:12 → 04:54:21 | 20 min 09 s | `Ruff format`, `Ruff lint`, `Mypy`, `Pytest`: los cuatro `skipped` |
| #206 (A5) | 15:35:27 → 15:55:37 | 20 min 10 s | los cuatro `skipped` |

Cuarenta minutos de runner gastados en no hacer nada, dos bloques detenidos y dos intervenciones manuales.

## Criterio de parada (escrito ANTES de decidir)

Publicado al propietario tras la primera ocurrencia, antes de saber si habría una segunda:

> Si vuelve a colgarse en el mismo sitio, ya no será mala suerte y te traigo el arreglo — es el mismo paso que señalé como el más caro y prescindible del ciclo. **Dos cancelaciones en el mismo paso dejan de ser mala suerte. En ese caso el arreglo no es reintentar.**

Se cumplió la condición y se dejó de reintentar.

## Opciones consideradas

1. Reintentar a mano cada vez que ocurra.
2. Cachear los paquetes `.deb` con `actions/cache`.
3. No instalar lo que ya está, acotar cada intento con su plazo y reintentar una vez.

## Decisión

La tercera, en los **tres** workflows que traían el paso duplicado —`quality.yml`, `implement-sirius-work.yml` y `repair-sirius-work.yml`— y por este orden de importancia:

1. **No instalar lo que ya está.** Se comprueba con `dpkg -s` cuáles faltan. Si no falta ninguna, `apt` no llega a ejecutarse. (En `ubuntu-latest` hoy **sí** faltan, así que esta guarda no es la que resuelve el problema; ver la comprobación.)
2. **Instalar sin refrescar primero.** La imagen del runner ya trae listas de paquetes. Esto evita por completo el paso lento en el caso normal.
3. **Refrescar solo si lo anterior no basta**, con plazos holgados: 240 s para `update`, 180 s para `install`.
4. **`timeout-minutes: 10` en el paso**, como red de último recurso. Peor caso: 150 + 240 + 180 = 570 s.

Y un cambio de desenlace que importa tanto como el ahorro: si de verdad no puede instalar, el paso **falla ruidosamente** en lugar de dejar morir el trabajo por tiempo. Un `failure` es diagnosticable y el ciclo sabe tratarlo; un `cancelled` no dice nada y detiene el bloque.

## Comprobación que la sostiene

Las dos piezas del arreglo, ejecutadas de verdad y no razonadas:

**La guarda.** Ejecutando el bucle de detección en un contenedor Linux con las tres bibliotecas presentes:

```
RESULTADO: ya instaladas -> apt no se ejecuta
```

**Esa comprobación no dice nada del runner, y la primera versión de este ADR la presentó como si lo dijera.** El primer intento del arreglo falló en CI justo por ahí: en `ubuntu-latest` las tres bibliotecas **no** están, la guarda no salta y `apt` se ejecuta igual. La medición era correcta; la extrapolación, no. La guarda se conserva porque no cuesta nada y cubre el caso en que sí estén, pero **no es la pieza que resuelve el problema**.

**El plazo.**

```
timeout 3 sobre un sleep 60 -> salió en 3s con código 124 (124 = cortado por plazo)
```

**Y una segunda corrección, del propio arreglo.** La primera versión puso 60 s a `apt-get update` y falló en CI ([run 32273953875](https://github.com/canelamoraguezandyjesus-bot/sirius/actions/runs/32273953875)). El registro muestra por qué:

```
16:07:08  Get:10 .../ubuntu/24.04/prod noble/main amd64 Packages [357 kB]
16:07:08  Get:13 .../chrome-stable/deb stable/main amd64 Packages [1414 B]
16:08:08  ##[warning]Intento 2 agotado o fallido; reintento.
```

Estaba descargando **con normalidad** cuando el plazo lo cortó a los 60 s exactos. El fallo del 19-08 **no fue un espejo caído: fue uno lento**, y eran dos averías distintas tratadas como una. Un plazo demasiado corto convierte lentitud en fallo, que es otra forma de romper el ciclo.

De ahí la forma definitiva, que además ataca la causa en vez del síntoma: **se intenta instalar SIN `update`** —la imagen del runner ya trae listas de paquetes y suelen bastar—, y solo si eso falla se refresca, con plazos holgados (240 s y 180 s). `apt-get update` refresca **todos** los orígenes configurados —Microsoft, Google, Docker— y ninguno sirve para estas tres bibliotecas: era trabajo lento e inútil en el camino crítico.

**Los tres ficheros** siguen siendo YAML válido tras el cambio (`yaml.safe_load`).

**Y una prueba estructural que ya existía cazó un efecto secundario.** Subir el plazo del paso de 5 a 10 min en `repair-sirius-work.yml` rompió
`test_job_timeout_covers_every_bounded_step_plus_margin`: exige que el plazo del job cubra la suma de los plazos de sus pasos **más cinco minutos de margen**, y la suma pasaba a 74 sobre un job de 75.

```
AssertionError: suma 74 sin margen bajo el job 75
```

No es un detalle contable: sin margen, el job puede caducar **durante** el paso del corrector, y una caducidad ahí es una cancelación —justo el desenlace mudo que este ADR viene a eliminar—. Se sube el plazo del job de 75 a 80, y la prueba vuelve a verde con 6 minutos de margen.

## Consecuencias

- El caso normal deja de refrescar listas de paquetes que no hacen falta: se instala directamente, y solo se refresca si eso no basta.
- Si las bibliotecas ya estuvieran presentes, no se toca `apt` en absoluto.
- El peor caso pasa de 20 min y `cancelled` a ~9,5 min y `failure`, que el ciclo sí sabe encauzar.
- Y queda una lección con nombre: **medir en el contenedor de la sesión no es medir en el runner.** El primer intento de este mismo arreglo se apoyó en esa confusión y falló en CI por ella.
- Se elimina la causa de las dos únicas intervenciones manuales del día que no fueron decisiones.

## Alternativas descartadas y por qué

**Reintentar a mano.** Es lo que se hizo la primera vez, y por eso hubo una segunda. Reintentar no es un arreglo: es pagar el coste otra vez y confiar en que la próxima no toque.

**Cachear los `.deb` con `actions/cache`.** Ataca el síntoma equivocado: lo que se colgaba era `apt-get update` contactando con el espejo, que se ejecutaría igual. Añade una dependencia y complejidad de invalidación para no cubrir el caso observado.

**Quitar el paso del todo**, apostando a que el runner ya trae las bibliotecas. **La primera versión de este ADR estuvo a punto de recomendarlo** apoyándose en una medición hecha en el contenedor de la sesión. CI demostró que en `ubuntu-latest` no están: quitar el paso habría roto todas las pruebas de GUI. Queda escrito como recordatorio de lo cerca que estuvo una extrapolación cómoda de convertirse en decisión.

**Plazos cortos y agresivos** (la primera versión: 60 s). Descartada con la evidencia de su propio fallo: convierte un espejo lento en un fallo, y el espejo lento es el caso frecuente. Cortar pronto solo vale cuando lo que se corta está muerto, no cuando va despacio.
