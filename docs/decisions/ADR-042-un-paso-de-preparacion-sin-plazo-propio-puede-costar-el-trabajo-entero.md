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

1. **No instalar lo que ya está.** Se comprueba con `dpkg -s` cuáles faltan. Si no falta ninguna, `apt` no llega a ejecutarse y la avería **no puede ocurrir**.
2. **Plazo por intento**: 60 s para `update`, 120 s para `install`. Un espejo que no responde cuesta un minuto, no veinte.
3. **Un reintento**, porque el fallo observado es transitorio.
4. **`timeout-minutes: 6` en el paso**, como red de último recurso.

Y un cambio de desenlace que importa tanto como el ahorro: si de verdad no puede instalar, el paso **falla ruidosamente** en lugar de dejar morir el trabajo por tiempo. Un `failure` es diagnosticable y el ciclo sabe tratarlo; un `cancelled` no dice nada y detiene el bloque.

## Comprobación que la sostiene

Las dos piezas del arreglo, ejecutadas de verdad y no razonadas:

**La guarda.** Ejecutando el bucle de detección en un contenedor Linux con las tres bibliotecas presentes:

```
RESULTADO: ya instaladas -> apt no se ejecuta
```

Esto es más que una comprobación de sintaxis: sugiere que en un runner con estas bibliotecas ya presentes **el `apt-get` era innecesario en todas y cada una de las ejecuciones**, y por tanto que el riesgo se asumía a cambio de nada.

**El plazo.**

```
timeout 3 sobre un sleep 60 -> salió en 3s con código 124 (124 = cortado por plazo)
```

**Los tres ficheros** siguen siendo YAML válido tras el cambio (`yaml.safe_load`).

## Consecuencias

- El caso normal deja de tocar la red: el paso pasa de ~77 s a milisegundos cuando las bibliotecas ya están.
- El peor caso pasa de 20 min y `cancelled` a ~6 min y `failure`, que el ciclo sí sabe encauzar.
- Se elimina la causa de las dos únicas intervenciones manuales del día que no fueron decisiones.

## Alternativas descartadas y por qué

**Reintentar a mano.** Es lo que se hizo la primera vez, y por eso hubo una segunda. Reintentar no es un arreglo: es pagar el coste otra vez y confiar en que la próxima no toque.

**Cachear los `.deb` con `actions/cache`.** Ataca el síntoma equivocado: lo que se colgaba era `apt-get update` contactando con el espejo, que se ejecutaría igual. Añade una dependencia y complejidad de invalidación para no cubrir el caso observado.

**Quitar el paso del todo**, apostando a que el runner siempre trae las bibliotecas. Tentador —la medición sugiere que suelen estar— pero es una apuesta sobre la imagen del runner, que GitHub cambia sin avisar. La guarda obtiene la misma ventaja sin hacer la apuesta.
